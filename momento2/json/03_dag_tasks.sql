-- ---------------------------------------------------------------------------
-- 03_dag_tasks.sql — Orquestación con Snowflake Tasks (Momento 2, punto 4)
-- Equipo 5 · RutaSegura — siniestros del call center (JSON)
--
-- DAG de dos tareas: ingesta desde el stage (raíz, con SCHEDULE) y aplanado
-- hacia staging (hija, con AFTER). Todo dentro de Snowflake — sin cron externo,
-- sin Airflow, sin GitHub Actions.
-- ---------------------------------------------------------------------------

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE WH_VEHICLE_COVERGE;
USE DATABASE VEHICLE_COVERAGE;
USE SCHEMA RAW_JSON;

-- ---------------------------------------------------------------------------
-- 1. Tarea raíz: ingesta incremental desde el bucket
-- ---------------------------------------------------------------------------
--
-- Cada hora revisa el stage y carga SOLO los archivos que no ha cargado (el load
-- metadata hace el trabajo incremental — ver la nota en 02 sobre por qué aquí sí
-- y en la ingesta relacional no).
--
-- El cron corre cada hora en punto, zona America/Bogota. Para el volumen real del
-- proveedor (un export semanal) hasta un cron diario sobraría — cada hora hace la
-- espera demostrable en una demo sin ser un desperdicio — la corrida que no
-- encuentra archivos nuevos termina en milisegundos.
CREATE TASK IF NOT EXISTS TASK_INGESTA_SINIESTROS
    WAREHOUSE = WH_VEHICLE_COVERGE
    SCHEDULE  = 'USING CRON 0 * * * * America/Bogota'
    COMMENT   = 'Raiz del DAG: carga incremental de exports JSON desde @STAGE_SINIESTROS.'
AS
COPY INTO RAW_SINIESTROS (raw_data, _stg_file_name, _stg_loaded_at)
FROM (
    SELECT $1, METADATA$FILENAME, CURRENT_TIMESTAMP()
    FROM @STAGE_SINIESTROS
)
FILE_FORMAT = (FORMAT_NAME = FF_SINIESTROS_JSON)
ON_ERROR    = ABORT_STATEMENT;

-- ---------------------------------------------------------------------------
-- 2. Tarea hija: aplanar hacia staging
-- ---------------------------------------------------------------------------
--
-- AFTER y ningún SCHEDULE propio: corre cuando la raíz termina CON ÉXITO, nunca
-- por su cuenta. Esa es la dependencia que convierte dos tareas en un DAG — si la
-- ingesta falla, el staging ni se toca, y no puede quedar un staging "más nuevo"
-- que su RAW.
CREATE TASK IF NOT EXISTS TASK_APLANAR_SINIESTROS
    WAREHOUSE = WH_VEHICLE_COVERGE
    COMMENT   = 'Hija del DAG: reconstruye STG_SINIESTROS_FLATTENED desde RAW_SINIESTROS.'
    AFTER TASK_INGESTA_SINIESTROS
AS
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
-- 3. Administración del DAG
-- ---------------------------------------------------------------------------

-- Las tasks nacen SUSPENDED — Snowflake nunca activa nada solo. Esto enciende la
-- raíz Y todas sus dependientes de un golpe:
SELECT SYSTEM$TASK_DEPENDENTS_ENABLE('VEHICLE_COVERAGE.RAW_JSON.TASK_INGESTA_SINIESTROS');

SHOW TASKS IN SCHEMA VEHICLE_COVERAGE.RAW_JSON;   -- state: ambas 'started'

-- Disparo manual para la demo (no espera el cron). Dispara la raíz; la hija corre
-- sola al terminar la raíz:
EXECUTE TASK TASK_INGESTA_SINIESTROS;

-- Evidencia de ejecución (el criterio pide TASK_HISTORY consultado):
-- Filtrado por nombre: sin TASK_NAME, las tasks internas del sistema (Cortex,
-- notificaciones...) inundan el resultado y las nuestras no aparecen en el LIMIT.
SELECT name, state, scheduled_time, completed_time, error_message
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
    TASK_NAME => 'TASK_INGESTA_SINIESTROS',
    SCHEDULED_TIME_RANGE_START => DATEADD('hour', -6, CURRENT_TIMESTAMP()),
    RESULT_LIMIT => 10))
ORDER BY scheduled_time DESC;

SELECT name, state, scheduled_time, completed_time, error_message
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
    TASK_NAME => 'TASK_APLANAR_SINIESTROS',
    SCHEDULED_TIME_RANGE_START => DATEADD('hour', -6, CURRENT_TIMESTAMP()),
    RESULT_LIMIT => 10))
ORDER BY scheduled_time DESC;

-- ---------------------------------------------------------------------------
-- 4. Apagar el DAG — el orden importa, y es el contrario al intuitivo
-- ---------------------------------------------------------------------------
--
-- Mientras la raíz de un DAG está activa, Snowflake bloquea cambios sobre sus
-- dependientes: un ALTER TASK ... SUSPEND sobre la HIJA con la raíz corriendo
-- falla con el error 091421 ("root task is not suspended"). La raíz se suspende
-- PRIMERO, siempre. (Para activar, en cambio, el orden da igual —
-- SYSTEM$TASK_DEPENDENTS_ENABLE lo resuelve solo.)
--
-- Dejar el DAG apagado al final de la demo también es higiene del trial: una task
-- con cron cada hora despierta el warehouse cada hora, y el trial cobra por
-- segundo de cómputo activo.
ALTER TASK TASK_INGESTA_SINIESTROS SUSPEND;
ALTER TASK TASK_APLANAR_SINIESTROS SUSPEND;

SHOW TASKS IN SCHEMA VEHICLE_COVERAGE.RAW_JSON;   -- state: ambas 'suspended'
