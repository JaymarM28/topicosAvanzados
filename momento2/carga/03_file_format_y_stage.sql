-- ---------------------------------------------------------------------------
-- 03_file_format_y_stage.sql — Momento 2, punto 3 (carga vía Internal Stage)
-- Equipo 5 · RutaSegura (Cobertura Vehicular)
--
-- Crea los dos objetos que consume `cargar.py`: el FILE FORMAT nombrado que
-- describe cómo vienen los CSV, y el Internal Stage donde aterrizan.
--
-- Orden de ejecución del Momento 2:
--   1. 01_setup_snowflake.sql     base, schema RAW, warehouse, rol
--   2. 02_bitacora_carga.sql      schema CONTROL + tabla BITACORA_CARGA
--   3. carga/03_file_format_y_stage.sql   <- este
--   4. carga/04_raw_tables.sql            tablas destino
--   5. uv run carga/cargar.py             PUT + COPY INTO
--
-- Se ejecuta desde un Worksheet de Snowsight, con un rol que pueda crear
-- objetos en el schema (ACCOUNTADMIN o el owner de la base).
-- ---------------------------------------------------------------------------

USE WAREHOUSE WH_VEHICLE_COVERGE;
USE DATABASE VEHICLE_COVERAGE;
USE SCHEMA RAW;

-- ---------------------------------------------------------------------------
-- 1. FILE FORMAT nombrado
-- ---------------------------------------------------------------------------
--
-- ¿Por qué un FILE FORMAT con nombre y no las opciones inline en cada COPY INTO?
-- Porque son 7 tablas: inline habría que repetir las mismas ocho opciones siete
-- veces, y el día que el formato de salida cambie (un delimitador, la forma de
-- escribir NULL) hay que acordarse de tocar los siete. Con un objeto nombrado el
-- contrato vive en un solo lugar y los COPY INTO solo lo referencian.
--
-- Cada opción de aquí abajo corresponde a una decisión que ya tomó
-- `extraer_neon_a_csv.py` al escribir los archivos — están documentadas en su
-- docstring. Esto es el otro extremo de ese contrato.
CREATE OR REPLACE FILE FORMAT VEHICLE_COVERAGE.RAW.FF_CSV_NEON
    TYPE                         = CSV
    FIELD_DELIMITER              = ','
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'     -- el extractor usa QUOTE_MINIMAL
    ENCODING                     = 'UTF8'
    -- PARSE_HEADER = TRUE hace que Snowflake LEA la primera fila como nombres de
    -- columna, en vez de solo saltársela (que es lo que hace SKIP_HEADER = 1).
    -- Es el requisito para poder usar MATCH_BY_COLUMN_NAME en el COPY INTO, o
    -- sea, para emparejar columnas POR NOMBRE y no por posición. Las dos opciones
    -- son mutuamente excluyentes: si se define PARSE_HEADER, no se define
    -- SKIP_HEADER.
    PARSE_HEADER                 = TRUE
    -- El extractor escribe los NULL como campo vacío. Las dos opciones juntas
    -- cubren el campo vacío sin comillas y el campo vacío entrecomillado ("").
    NULL_IF                      = ('')
    EMPTY_FIELD_AS_NULL          = TRUE
    -- FALSE (que además es el default) a propósito: si un dato de negocio trae
    -- espacios al inicio o al final, la capa RAW los conserva. RAW es un espejo
    -- del origen; limpiar es trabajo de las capas de arriba, no de la ingesta.
    TRIM_SPACE                   = FALSE
    -- Los archivos llegan gzipped porque `PUT` los comprime en tránsito
    -- (AUTO_COMPRESS = TRUE). AUTO detecta la compresión por la extensión .gz,
    -- así que el mismo formato sirve si algún día se cargan archivos sin comprimir.
    COMPRESSION                  = AUTO
    COMMENT = 'CSV producidos por momento2/extraer_neon_a_csv.py: UTF-8, coma, quoting minimo, header en la primera fila, NULL como campo vacio.';

-- ---------------------------------------------------------------------------
-- 2. Internal Stage
-- ---------------------------------------------------------------------------
--
-- Un stage interno es almacenamiento gestionado por Snowflake dentro de la
-- cuenta. Es "internal" por oposición a un External Stage (un bucket propio en
-- S3/GCS/Azure): no hay que aprovisionar ni pagar almacenamiento aparte, ni
-- configurar credenciales cruzadas entre nubes. A cambio, los archivos solo son
-- accesibles desde Snowflake — para este proyecto es exactamente lo que se
-- necesita.
--
-- Es un stage con NOMBRE (no el stage de usuario `@~` ni el de tabla `@%tabla`)
-- porque es un recurso del pipeline, no de una persona ni de una tabla: se le
-- pueden dar permisos al rol de servicio, y cualquier integrante del equipo que
-- corra `cargar.py` escribe en el mismo sitio.
--
-- ¿Por qué no se le asocia un FILE_FORMAT por defecto? Porque un formato con
-- PARSE_HEADER = TRUE solo es válido en un COPY INTO con MATCH_BY_COLUMN_NAME;
-- pegado al stage rompería un `SELECT $1, $2 FROM @STAGE_NEON` de inspección
-- manual. El formato se nombra explícitamente en cada COPY INTO — que además es
-- lo que hace que el COPY se lea solo, sin tener que ir a mirar el DDL del stage.
CREATE STAGE IF NOT EXISTS VEHICLE_COVERAGE.RAW.STAGE_NEON
    -- DIRECTORY habilita la directory table: permite hacer
    -- `SELECT * FROM DIRECTORY(@STAGE_NEON)` y ver qué archivos hay, con su
    -- tamaño y fecha. Es lo que se muestra en la sustentación para evidenciar
    -- que el PUT efectivamente subió algo antes de que corriera el COPY.
    DIRECTORY = (ENABLE = TRUE)
    COMMENT   = 'Landing de archivos CSV extraidos de Neon, antes del COPY INTO hacia RAW.';

-- ---------------------------------------------------------------------------
-- 3. Permisos para el rol de servicio
-- ---------------------------------------------------------------------------
--
-- READ para que el COPY INTO pueda leer los archivos, WRITE para que el PUT
-- pueda subirlos. Sin estos grants, `cargar.py` corriendo como TEAM5_LOADER
-- falla con "Stage does not exist or not authorized" — que es el mismo mensaje
-- que da un stage inexistente, y cuesta diagnosticar.
GRANT USAGE      ON FILE FORMAT VEHICLE_COVERAGE.RAW.FF_CSV_NEON TO ROLE TEAM5_LOADER;
GRANT READ, WRITE ON STAGE      VEHICLE_COVERAGE.RAW.STAGE_NEON  TO ROLE TEAM5_LOADER;

-- ---------------------------------------------------------------------------
-- Verificación
-- ---------------------------------------------------------------------------
SHOW FILE FORMATS LIKE 'FF_CSV_NEON' IN SCHEMA VEHICLE_COVERAGE.RAW;
SHOW STAGES       LIKE 'STAGE_NEON'  IN SCHEMA VEHICLE_COVERAGE.RAW;
LIST @VEHICLE_COVERAGE.RAW.STAGE_NEON;
