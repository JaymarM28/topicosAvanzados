-- ---------------------------------------------------------------------------
-- 05_esquema_y_stage.sql — Ingesta semi-estructurada (Momento 2, punto 3)
-- Equipo 5 · RutaSegura — siniestros del call center (JSON)
--
-- Crea el schema del dominio semi-estructurado, el FILE FORMAT para los exports
-- JSON y el External Stage que apunta al bucket S3 del equipo.
--
-- Orden completo del Momento 2:
--   1. 01_setup_snowflake.sql            (warehouse, DB, RAW relacional, rol)
--   2. 02_bitacora_carga.sql             (schema CONTROL + bitácora)
--   3. carga/03_file_format_y_stage.sql  (ingesta relacional)
--   4. carga/04_raw_tables.sql
--   5. json/05_esquema_y_stage.sql       <- este
--   6. json/06_tablas_raw_y_staging.sql
--   7. json/07_dag_tasks.sql
--   8. json/08_rbac_masking.sql
-- ---------------------------------------------------------------------------

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE WH_VEHICLE_COVERGE;
USE DATABASE VEHICLE_COVERAGE;

-- ---------------------------------------------------------------------------
-- 1. Schema separado para el dominio semi-estructurado
-- ---------------------------------------------------------------------------
--
-- ¿Por qué un schema aparte y no meter RAW_SINIESTROS dentro de RAW? Porque son
-- dominios con contratos distintos. RAW (relacional) es un espejo 1:1 de Neon: sus
-- tablas tienen columnas conocidas y su fuente está bajo el control del equipo vía
-- Flyway. RAW_JSON recibe datos de un proveedor EXTERNO cuyo esquema puede cambiar
-- sin aviso — schema-on-read. Separarlos hace que los permisos, las validaciones y
-- las conversaciones ("¿dónde está esto?") tengan una frontera clara.
CREATE SCHEMA IF NOT EXISTS VEHICLE_COVERAGE.RAW_JSON
    COMMENT = 'Dominio semi-estructurado: exports JSON del call center de siniestros. Schema-on-read.';

USE SCHEMA RAW_JSON;

-- ---------------------------------------------------------------------------
-- 2. FILE FORMAT para los exports
-- ---------------------------------------------------------------------------
--
-- STRIP_OUTER_ARRAY = TRUE es obligatorio aquí: cada export semanal es un array
-- JSON ( [ {...}, {...} ] ). Con esta opción, cada elemento del array se vuelve
-- una fila VARIANT. Sin ella, el archivo completo cargaría como UNA sola fila —
-- técnicamente sin error, semánticamente inútil.
CREATE FILE FORMAT IF NOT EXISTS VEHICLE_COVERAGE.RAW_JSON.FF_SINIESTROS_JSON
    TYPE              = JSON
    STRIP_OUTER_ARRAY = TRUE
    COMMENT = 'Exports semanales del call center: un array JSON de siniestros por archivo.';

-- ---------------------------------------------------------------------------
-- 3. External Stage hacia el bucket S3 del equipo
-- ---------------------------------------------------------------------------
--
-- ¿External y no Internal como en la ingesta relacional? Porque el escenario es
-- otro. En la relacional NOSOTROS producimos los archivos y los subimos (PUT); acá
-- el proveedor externo deposita sus exports en un bucket y Snowflake solo LEE de
-- ahí. Un External Stage es exactamente eso: Snowflake apuntando fuera de sí mismo.
--
-- El bucket tiene lectura pública anónima, por eso no hay CREDENTIALS ni STORAGE
-- INTEGRATION (fuera del alcance del momento, según el enunciado).
--
-- El bucket del equipo. La policy necesita DOS statements: GetObject sobre los
-- objetos Y ListBucket+GetBucketLocation sobre el bucket — sin el segundo,
-- Snowflake da "Access Denied" aunque los objetos sean públicos en el navegador
-- (lección aprendida en vivo la noche del 21/08).
CREATE OR REPLACE STAGE VEHICLE_COVERAGE.RAW_JSON.STAGE_SINIESTROS
    URL         = 's3://rutasegura-1234567890/siniestros/'
    FILE_FORMAT = FF_SINIESTROS_JSON
    DIRECTORY   = (ENABLE = TRUE)
    COMMENT     = 'Bucket S3 del proveedor (lectura publica): exports JSON de siniestros.';

-- Para desarrollo local sin bucket, la variante interna equivalente es:
--   CREATE OR REPLACE STAGE VEHICLE_COVERAGE.RAW_JSON.STAGE_SINIESTROS
--       FILE_FORMAT = FF_SINIESTROS_JSON
--       DIRECTORY   = (ENABLE = TRUE);
-- y subir los mocks con:  PUT file://.../json/datos_mock/*.json @STAGE_SINIESTROS
-- Todo lo demás (COPY, FLATTEN, tasks) funciona idéntico con cualquiera de las dos.

-- ---------------------------------------------------------------------------
-- 4. Permisos del rol de servicio
-- ---------------------------------------------------------------------------
GRANT USAGE ON SCHEMA VEHICLE_COVERAGE.RAW_JSON TO ROLE TEAM5_LOADER;
GRANT CREATE TABLE ON SCHEMA VEHICLE_COVERAGE.RAW_JSON TO ROLE TEAM5_LOADER;
GRANT USAGE ON FILE FORMAT VEHICLE_COVERAGE.RAW_JSON.FF_SINIESTROS_JSON TO ROLE TEAM5_LOADER;
GRANT READ, WRITE ON STAGE VEHICLE_COVERAGE.RAW_JSON.STAGE_SINIESTROS TO ROLE TEAM5_LOADER;
GRANT SELECT, INSERT, UPDATE, DELETE ON FUTURE TABLES IN SCHEMA VEHICLE_COVERAGE.RAW_JSON TO ROLE TEAM5_LOADER;

-- ---------------------------------------------------------------------------
-- Verificación: explorar ANTES de cargar (patrón del taller, Paso A)
-- ---------------------------------------------------------------------------
LIST @VEHICLE_COVERAGE.RAW_JSON.STAGE_SINIESTROS;

-- Un SELECT directo contra el stage no persiste nada — es la forma barata de ver
-- qué trae el JSON antes de decidir cómo aplanarlo:
-- SELECT $1 FROM @STAGE_SINIESTROS (FILE_FORMAT => FF_SINIESTROS_JSON) LIMIT 3;
