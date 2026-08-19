-- ---------------------------------------------------------------------------
-- 02_raw_tables.sql — Momento 2, punto 3 (carga vía Internal Stage)
-- Equipo 5 · RutaSegura (Cobertura Vehicular)
--
-- Tablas destino del COPY INTO, en el schema RAW.
--
-- Reflejan el esquema de Neon TAL COMO QUEDÓ después de las migraciones del
-- Momento 1 — no el baseline. Concretamente incluyen lo que agregaron las
-- migraciones evolutivas:
--   V202608081500  la tabla VEHICLE completa
--   V202608081510  BILL.PAYMENT_METHOD
--   V202608081600  su ampliación a VARCHAR(20)
--   V202608081620  BILL.PAID_DATE
-- Un DDL copiado del baseline se vería casi igual y fallaría en el COPY INTO
-- con "column not found" en esas tres columnas.
--
-- Se ejecuta después de 01_file_format_y_stage.sql.
-- ---------------------------------------------------------------------------

USE WAREHOUSE WH_VEHICLE_COVERGE;
USE DATABASE VEHICLE_COVERAGE;
USE SCHEMA RAW;

-- ---------------------------------------------------------------------------
-- Nota de diseño: por qué RAW no tiene NOT NULL, PRIMARY KEY ni FOREIGN KEY
-- ---------------------------------------------------------------------------
--
-- Tentador ponerlos: el origen en Postgres sí los tiene. Pero RAW es una landing
-- zone, y su trabajo es aceptar lo que venga para que se pueda diagnosticar
-- DESPUÉS. Si la restricción vive aquí, un dato sucio hace fallar el COPY y no
-- queda registro de qué llegó mal — hay que ir a mirar el CSV a mano.
--
-- Y hay una razón práctica encima: las validaciones post-carga (punto 6) tienen
-- que poder DETECTAR nulos en llaves primarias y huérfanos referenciales. Si la
-- tabla los rechazara de entrada, esas validaciones nunca podrían fallar, y una
-- validación que no puede fallar no valida nada.
--
-- (Snowflake, además, acepta la sintaxis de PRIMARY KEY y FOREIGN KEY pero NO
-- las hace cumplir: son metadata informativa para el optimizador y las
-- herramientas de modelado. La única restricción que sí impone es NOT NULL.
-- Declararlas aquí daría una falsa sensación de integridad.)

CREATE TABLE IF NOT EXISTS VEHICLE_COVERAGE.RAW.COVERAGE (
    ID                  NUMBER(38,0),
    COVERAGE_NAME       VARCHAR,
    COVERAGE_GROUP      VARCHAR,
    CODE                VARCHAR,
    IS_POLICY_COVERAGE  BOOLEAN,
    IS_VEHICLE_COVERAGE BOOLEAN,
    DESCRIPTION         VARCHAR
) COMMENT = 'RAW espejo de public.coverage en Neon. Catalogo de tipos de cobertura.';

CREATE TABLE IF NOT EXISTS VEHICLE_COVERAGE.RAW.POLICY (
    ID                    NUMBER(38,0),
    POLICY_NUMBER         VARCHAR,
    POLICY_EFFECTIVE_DATE DATE,
    POLICY_EXPIRE_DATE    DATE,
    PAYMENT_OPTION        VARCHAR,
    TOTAL_AMOUNT          NUMBER(10,2),
    ACTIVE                BOOLEAN,
    ADDITIONAL_INFO       VARCHAR,
    CREATED_DATE          TIMESTAMP_NTZ
) COMMENT = 'RAW espejo de public.policy en Neon. Polizas de seguro vehicular.';

CREATE TABLE IF NOT EXISTS VEHICLE_COVERAGE.RAW.POLICY_EDIT_LOG (
    ID                NUMBER(38,0),
    POLICY_ID         NUMBER(38,0),
    EDITED_TABLE_NAME VARCHAR,
    EDITED_DATE       TIMESTAMP_NTZ,
    ADDITIONAL_INFO   VARCHAR,
    EDITED_BY         VARCHAR
) COMMENT = 'RAW espejo de public.policy_edit_log en Neon. Auditoria de cambios sobre polizas.';

-- BILL es la tabla con más historia: tres de las seis migraciones del Momento 1
-- la tocaron. PAYMENT_METHOD es VARCHAR(20) y no VARCHAR(2) por el incidente
-- documentado en V202608081600 ("value too long for type character varying(2)").
-- Se respeta el largo del origen a propósito: si mañana alguien vuelve a mandar
-- un valor más largo, se quiere que falle aquí también y no que RAW lo acepte
-- silenciosamente y el problema aparezca dos capas más arriba.
CREATE TABLE IF NOT EXISTS VEHICLE_COVERAGE.RAW.BILL (
    ID              NUMBER(38,0),
    POLICY_ID       NUMBER(38,0),
    DUE_DATE        DATE,
    MINIMUM_PAYMENT NUMBER(10,2),
    CREATED_DATE    TIMESTAMP_NTZ,
    BALANCE         NUMBER(10,2),
    STATUS          VARCHAR,
    PAYMENT_METHOD  VARCHAR(20),
    PAID_DATE       DATE
) COMMENT = 'RAW espejo de public.bill en Neon. Incluye PAYMENT_METHOD (V202608081510/1600) y PAID_DATE (V202608081620).';

CREATE TABLE IF NOT EXISTS VEHICLE_COVERAGE.RAW.POLICY_COVERAGE (
    ID           NUMBER(38,0),
    POLICY_ID    NUMBER(38,0),
    COVERAGE_ID  NUMBER(38,0),
    ACTIVE       BOOLEAN,
    CREATED_DATE TIMESTAMP_NTZ
) COMMENT = 'RAW espejo de public.policy_coverage en Neon. Coberturas contratadas a nivel poliza.';

-- VEHICLE no existe en el baseline: la creó la migración V202608081500, que
-- además hizo backfill de los 60 vehículos que vivían como vehicle_id suelto en
-- vehicle_coverage. Por eso no hay un data/vehicle.json semilla — y por eso es
-- la tabla que más fácil se olvida al armar la lista de extracción.
CREATE TABLE IF NOT EXISTS VEHICLE_COVERAGE.RAW.VEHICLE (
    ID           NUMBER(38,0),
    VIN          VARCHAR,
    MAKE         VARCHAR,
    MODEL        VARCHAR,
    MODEL_YEAR   NUMBER(5,0),
    PLATE        VARCHAR,
    CREATED_DATE TIMESTAMP_NTZ
) COMMENT = 'RAW espejo de public.vehicle en Neon. Tabla creada por la migracion V202608081500.';

CREATE TABLE IF NOT EXISTS VEHICLE_COVERAGE.RAW.VEHICLE_COVERAGE (
    ID           NUMBER(38,0),
    VEHICLE_ID   NUMBER(38,0),
    COVERAGE_ID  NUMBER(38,0),
    ACTIVE       BOOLEAN,
    CREATED_DATE TIMESTAMP_NTZ
) COMMENT = 'RAW espejo de public.vehicle_coverage en Neon. Coberturas contratadas a nivel vehiculo.';

-- El rol de servicio necesita DELETE además de INSERT: la estrategia de carga es
-- borrar-y-cargar dentro de una transacción (ver carga/README.md). El grant ON
-- FUTURE TABLES de setup_snowflake.sql ya lo cubre para las tablas creadas
-- después de ese script, pero se repite explícitamente aquí para que este
-- archivo funcione aunque se ejecute en una cuenta donde el orden fue otro.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA VEHICLE_COVERAGE.RAW TO ROLE TEAM5_LOADER;

-- ---------------------------------------------------------------------------
-- Verificación
-- ---------------------------------------------------------------------------
SHOW TABLES IN SCHEMA VEHICLE_COVERAGE.RAW;

SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM VEHICLE_COVERAGE.INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'RAW'
ORDER BY TABLE_NAME, ORDINAL_POSITION;
