-- ---------------------------------------------------------------------------
-- Bitácora de carga — Momento 2 (equipo 5, RutaSegura / Cobertura Vehicular)
--
-- Tabla de control que registra, por cada archivo cargado vía COPY INTO:
-- tabla destino, filas cargadas, timestamp y estado (incluye cargas fallidas
-- o parciales, no solo el camino feliz).
--
-- Vive en su propio schema (CONTROL), separado de RAW: RAW es la landing zone
-- de datos de negocio; esta es metadata operativa del pipeline, con un
-- propósito distinto y un ciclo de vida propio (no se trunca junto con RAW).
--
-- Requiere que momento2/01_setup_snowflake.sql ya se haya ejecutado (crea la
-- base de datos VEHICLE_COVERAGE y el rol TEAM5_LOADER).
-- ---------------------------------------------------------------------------

USE DATABASE VEHICLE_COVERAGE;

CREATE SCHEMA IF NOT EXISTS VEHICLE_COVERAGE.CONTROL
    COMMENT = 'Metadata operativa del pipeline de ingesta: bitácora de carga.';

CREATE TABLE IF NOT EXISTS VEHICLE_COVERAGE.CONTROL.BITACORA_CARGA (
    id                INTEGER AUTOINCREMENT START 1 INCREMENT 1,
    tabla_cargada     VARCHAR NOT NULL,
    archivo           VARCHAR,
    filas_cargadas    INTEGER,
    estado            VARCHAR NOT NULL,   -- LOADED | LOAD_FAILED | PARTIALLY_LOADED
    mensaje_error     VARCHAR,
    timestamp_carga   TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_bitacora_carga PRIMARY KEY (id)
)
COMMENT = 'Una fila por archivo procesado en cada ejecución de COPY INTO.';

GRANT USAGE, CREATE TABLE ON SCHEMA VEHICLE_COVERAGE.CONTROL TO ROLE TEAM5_LOADER;
GRANT SELECT, INSERT ON TABLE VEHICLE_COVERAGE.CONTROL.BITACORA_CARGA TO ROLE TEAM5_LOADER;

-- ----------------------------------------------------------------------------
-- Verificación
-- ----------------------------------------------------------------------------
SHOW SCHEMAS LIKE 'CONTROL' IN DATABASE VEHICLE_COVERAGE;
DESCRIBE TABLE VEHICLE_COVERAGE.CONTROL.BITACORA_CARGA;
