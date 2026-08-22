-- ---------------------------------------------------------------------------
-- 02_tablas_raw_y_staging.sql — Ingesta semi-estructurada (Momento 2, punto 3)
-- Equipo 5 · RutaSegura — siniestros del call center (JSON)
--
-- La tabla de aterrizaje VARIANT, la carga inicial, y el aplanado con
-- LATERAL FLATTEN hacia la tabla de staging.
-- ---------------------------------------------------------------------------

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE WH_VEHICLE_COVERGE;
USE DATABASE VEHICLE_COVERAGE;
USE SCHEMA RAW_JSON;

-- ---------------------------------------------------------------------------
-- 1. RAW_SINIESTROS — la tabla de una sola columna de datos
-- ---------------------------------------------------------------------------
--
-- Todo el siniestro entra como UN valor VARIANT, sin declarar su esquema. Esa es
-- la apuesta del schema-on-read: si el call center agrega un campo mañana (y lo
-- hace — los exports de la semana 2 traen `email` y los de la 3 `assigned_workshop`,
-- que la semana 1 no tenía), esta tabla NO cambia. El costo se paga al leer, no al
-- cargar — el opuesto exacto de la ingesta relacional de carga/.
CREATE TABLE IF NOT EXISTS RAW_SINIESTROS (
    raw_data       VARIANT,
    -- Trazabilidad: de qué archivo salió cada fila y cuándo entró. Con esto, un
    -- dato raro en staging se rastrea hasta el export exacto que lo trajo.
    _stg_file_name STRING,
    _stg_loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Aterrizaje de los exports JSON de siniestros, sin interpretar. Una fila = un siniestro.';

-- ---------------------------------------------------------------------------
-- 2. Carga inicial desde el stage
-- ---------------------------------------------------------------------------
--
-- Sin FORCE, a propósito — al revés que en la ingesta relacional. Allá cada corrida
-- regenera archivos con el mismo nombre y contenido nuevo, y el load metadata de
-- Snowflake era una trampa. Acá el proveedor DEPOSITA archivos nuevos con nombres
-- nuevos (siniestros_semana_N.json) y los viejos no cambian: el load metadata es
-- exactamente el comportamiento incremental que se quiere — cargar solo lo que no
-- se ha cargado. Misma feature, dos decisiones opuestas, cada una con su razón.
COPY INTO RAW_SINIESTROS (raw_data, _stg_file_name, _stg_loaded_at)
FROM (
    SELECT $1, METADATA$FILENAME, CURRENT_TIMESTAMP()
    FROM @STAGE_SINIESTROS
)
FILE_FORMAT = (FORMAT_NAME = FF_SINIESTROS_JSON)
ON_ERROR    = ABORT_STATEMENT;

-- ---------------------------------------------------------------------------
-- 3. Exploración con notación de punto y LATERAL FLATTEN (Paso C del taller)
-- ---------------------------------------------------------------------------
--
-- Nivel siniestro: notación de dos puntos + cast explícito. El cast (::STRING,
-- ::FLOAT) importa: sin él todo sale como VARIANT y las comparaciones se vuelven
-- sorpresas.
SELECT
    raw_data:claim_id::STRING             AS claim_id,
    raw_data:policy_number::STRING        AS policy_number,
    raw_data:incident_type::STRING        AS incident_type,
    raw_data:estimated_damage_usd::FLOAT  AS estimated_damage_usd
FROM RAW_SINIESTROS
LIMIT 5;

-- Nivel involucrado: LATERAL FLATTEN convierte cada elemento del array
-- involved_parties en una fila propia — el "JOIN implícito contra tu propio
-- array". Un siniestro con 3 involucrados produce 3 filas.
--
-- Las claves que no existen en los exports viejos (email solo llega desde la
-- semana 2, assigned_workshop desde la 3) devuelven NULL, no error: eso es
-- schema-on-read absorbiendo la evolución del proveedor sin tocar una línea.
SELECT
    raw_data:claim_id::STRING            AS claim_id,
    p.value:name::STRING                 AS party_name,
    p.value:role::STRING                 AS party_role,
    p.value:phone::STRING                AS phone,
    p.value:email::STRING                AS email          -- NULL en semana 1
FROM RAW_SINIESTROS,
     LATERAL FLATTEN(input => raw_data:involved_parties) p
LIMIT 10;

-- ---------------------------------------------------------------------------
-- 4. STG_SINIESTROS_FLATTENED — materializar el aplanado
-- ---------------------------------------------------------------------------
--
-- ¿Por qué una tabla y no una vista? Porque cada consulta a la vista reaplanaría
-- todo RAW_SINIESTROS de nuevo — gratis hoy con 12 siniestros, caro cuando el
-- proveedor lleve un año depositando exports. Y porque la Masking Policy de
-- 04_rbac_masking.sql se aplica sobre columnas de esta tabla: es el punto donde el
-- dato semi-estructurado se vuelve consumible (y por tanto, protegible).
CREATE TABLE IF NOT EXISTS STG_SINIESTROS_FLATTENED (
    claim_id             STRING,
    policy_number        STRING,   -- cruza con RAW.POLICY.POLICY_NUMBER
    vin                  STRING,   -- cruza con RAW.VEHICLE.VIN
    reported_at          TIMESTAMP_NTZ,
    incident_type        STRING,
    estimated_damage_usd FLOAT,
    assigned_workshop    STRING,   -- NULL en exports anteriores a la semana 3
    party_name           STRING,
    party_role           STRING,
    party_phone          STRING,   -- PII -> Masking Policy en 04
    party_address        STRING,   -- PII
    party_email          STRING,   -- NULL en exports de la semana 1
    _flattened_at        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Siniestros aplanados: una fila por persona involucrada. Fuente: RAW_SINIESTROS.';

-- INSERT OVERWRITE: reconstruye el staging completo desde RAW en cada corrida.
-- Mismo argumento de idempotencia que la ingesta relacional — el staging es
-- derivable al 100% de RAW, así que regenerarlo es la forma más simple de que
-- nunca quede desincronizado. Es también lo que ejecuta la task hija del DAG (03).
INSERT OVERWRITE INTO STG_SINIESTROS_FLATTENED (
    claim_id, policy_number, vin, reported_at, incident_type,
    estimated_damage_usd, assigned_workshop,
    party_name, party_role, party_phone, party_address, party_email
)
SELECT
    raw_data:claim_id::STRING,
    raw_data:policy_number::STRING,
    raw_data:vin::STRING,
    raw_data:reported_at::TIMESTAMP_NTZ,
    raw_data:incident_type::STRING,
    raw_data:estimated_damage_usd::FLOAT,
    raw_data:assigned_workshop::STRING,
    p.value:name::STRING,
    p.value:role::STRING,
    p.value:phone::STRING,
    p.value:personal_address::STRING,
    p.value:email::STRING
FROM RAW_SINIESTROS,
     LATERAL FLATTEN(input => raw_data:involved_parties) p;

-- ---------------------------------------------------------------------------
-- Verificación
-- ---------------------------------------------------------------------------
SELECT COUNT(*) AS siniestros FROM RAW_SINIESTROS;
SELECT COUNT(*) AS involucrados FROM STG_SINIESTROS_FLATTENED;

-- El cruce con el mundo relacional: cuánto daño estimado acumula cada póliza
-- REAL del modelo del Momento 1. Este JOIN entre un dominio y el otro es la
-- razón de que ambos vivan en el mismo warehouse.
SELECT
    pol.POLICY_NUMBER,
    COUNT(DISTINCT s.claim_id)      AS siniestros,
    ROUND(SUM(s.estimated_damage_usd), 2) AS danio_estimado_usd
FROM RAW.POLICY pol
JOIN STG_SINIESTROS_FLATTENED s ON s.policy_number = pol.POLICY_NUMBER
GROUP BY pol.POLICY_NUMBER
ORDER BY danio_estimado_usd DESC;
