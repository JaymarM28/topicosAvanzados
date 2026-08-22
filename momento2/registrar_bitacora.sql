-- ---------------------------------------------------------------------------
-- Patrón para registrar cada COPY INTO en la bitácora — pégalo justo después
-- de cada COPY INTO, en la misma sesión (usa RESULT_SCAN(LAST_QUERY_ID()),
-- que lee el resultado de la ÚLTIMA query ejecutada — por eso el orden
-- importa: nada debe correr entre el COPY INTO y este INSERT).
--
-- RESULT_SCAN expone, por cada archivo que procesó el COPY INTO: "file",
-- "status" (LOADED | LOAD_FAILED | PARTIALLY_LOADED), "rows_loaded",
-- "errors_seen", "first_error". Una fila del resultado = una fila en la
-- bitácora, así que si ON_ERROR = 'CONTINUE' deja pasar unos archivos y
-- falla otros, la bitácora refleja exactamente eso — no solo el camino feliz.
--
-- Requiere que momento2/02_bitacora_carga.sql ya se haya ejecutado.
-- ---------------------------------------------------------------------------

-- Ejemplo completo para UNA tabla (repetir este bloque por cada una de las 6):

-- COPY INTO VEHICLE_COVERAGE.RAW.POLICY
--     FROM @VEHICLE_COVERAGE.RAW.STAGE_NEON/policy.csv
--     FILE_FORMAT = (FORMAT_NAME = VEHICLE_COVERAGE.RAW.FF_CSV_NEON)
--     ON_ERROR = 'CONTINUE';

INSERT INTO VEHICLE_COVERAGE.CONTROL.BITACORA_CARGA
    (tabla_cargada, archivo, filas_cargadas, estado, mensaje_error)
SELECT
    'POLICY'                AS tabla_cargada,   -- <- cambia esto por cada tabla
    "file"                  AS archivo,
    "rows_loaded"           AS filas_cargadas,
    "status"                AS estado,
    "first_error"           AS mensaje_error
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- ----------------------------------------------------------------------------
-- Verificación rápida: últimas ejecuciones registradas
-- ----------------------------------------------------------------------------
SELECT *
FROM VEHICLE_COVERAGE.CONTROL.BITACORA_CARGA
ORDER BY timestamp_carga DESC
LIMIT 20;

-- Nota: si el COPY INTO falla como comando completo (p. ej. el stage o el
-- archivo no existen, error de sintaxis), RESULT_SCAN no tiene nada que leer
-- porque esa query nunca produjo un resultado — ese caso no queda cubierto
-- por este patrón. Para capturarlo también haría falta envolver la carga en
-- un stored procedure con manejo de excepciones (fuera del alcance de hoy).
