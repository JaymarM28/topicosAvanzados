-- ===========================================================================
-- V202608081500__add_vehicle_table.sql
--
-- Primera migración evolutiva sobre el estado base de Cobertura Vehicular.
-- El ERD original de referencia modela `Vehicle_Coverage.Vehicle_ID` como un
-- identificador suelto: nunca define la entidad `Vehicle`. Eso funcionó como
-- diagrama de partida, pero en producción no se puede validar un vehicle_id
-- contra nada. Esta migración formaliza la entidad que faltaba.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1. La tabla que el ERD nunca definió
-- ---------------------------------------------------------------------------

CREATE TABLE vehicle (
    id           INTEGER PRIMARY KEY,
    vin          TEXT NOT NULL UNIQUE,
    make         TEXT,
    model        TEXT,
    model_year   SMALLINT,
    plate        TEXT,
    created_date TIMESTAMP NOT NULL DEFAULT now()
);

COMMENT ON TABLE vehicle IS
    'Vehículo asegurado. Entidad implícita en el ERD original: solo existía como '
    'vehicle_id suelto en vehicle_coverage.';

-- ---------------------------------------------------------------------------
-- 2. Backfill: los vehículos ya existían, solo que sin fila propia
-- ---------------------------------------------------------------------------

-- ¿Por qué no dejamos la tabla vacía y seguimos? Porque `vehicle_coverage` ya
-- tiene filas de la carga inicial (Sesión 1) que referencian vehicle_id del 1
-- al 60. Si agregamos la foreign key del paso 3 sin backfill, la restricción
-- fallaría de inmediato contra datos reales. Esto es exactamente lo que en
-- clase se documentó como pendiente: "pensar en la migración de los datos
-- existentes es donde está el aprendizaje".
--
-- El VIN real no existe en ningún lado — nunca se capturó, porque la entidad
-- no existía. Un placeholder explícito y grep-able (`VIN-PENDIENTE-<id>`) es
-- preferible a inventar un VIN plausible: comunica "dato desconocido, hay que
-- completarlo" en vez de fingir que el dato siempre estuvo completo.
INSERT INTO vehicle (id, vin, created_date)
SELECT DISTINCT vehicle_id, 'VIN-PENDIENTE-' || vehicle_id, now()
FROM vehicle_coverage
ORDER BY vehicle_id;

-- ---------------------------------------------------------------------------
-- 3. Ahora sí, la integridad referencial que faltaba
-- ---------------------------------------------------------------------------

ALTER TABLE vehicle_coverage
    ADD CONSTRAINT fk_vehicle_coverage_vehicle
    FOREIGN KEY (vehicle_id) REFERENCES vehicle (id);
