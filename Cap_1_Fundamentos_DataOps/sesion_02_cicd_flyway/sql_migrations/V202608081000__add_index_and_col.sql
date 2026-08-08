-- ===========================================================================
-- V202608081000__add_index_and_col.sql
--
-- Primera migración evolutiva sobre el estado base de Parch & Posey.
-- Responde a dos solicitudes del equipo de producto:
--   1. El dashboard de cuentas está lento al listar las últimas órdenes.
--   2. Marketing quiere saber de qué campaña viene cada visita web.
-- ===========================================================================

-- ¿Por qué el nombre es V202608081000 y no V2? Porque en un equipo, dos personas
-- trabajando en branches distintas crearían ambas "V2__algo.sql" y al hacer merge
-- Flyway abortaría con un conflicto de versión duplicada. Un timestamp
-- (AAAAMMDDHHMM) es único por construcción: nadie más va a crear una migración en
-- ese mismo minuto. Además el nombre del archivo te dice CUÁNDO se decidió el
-- cambio, que es justo lo que quieres saber seis meses después.


-- ---------------------------------------------------------------------------
-- 1. Índice para el listado de órdenes recientes por cuenta
-- ---------------------------------------------------------------------------

-- ¿Por qué un índice compuesto y no dos índices separados? La query real es
-- "dame las últimas N órdenes de ESTA cuenta": filtra por account_id y ordena por
-- occurred_at. Un índice compuesto en ese orden permite a PostgreSQL localizar el
-- bloque de la cuenta y leer las filas ya ordenadas, sin un paso de sort. Dos
-- índices sueltos obligarían a combinar resultados y ordenar después.
-- El orden de las columnas importa: primero por lo que se filtra, luego por lo que
-- se ordena. Invertirlo haría el índice inútil para esta consulta.
CREATE INDEX idx_orders_account_occurred
    ON orders (account_id, occurred_at DESC);


-- ---------------------------------------------------------------------------
-- 2. Atribución de campaña en los eventos web
-- ---------------------------------------------------------------------------

-- Nota del equipo de backend que solicitó el cambio:
--   "Vamos a guardar el parámetro utm_source de la URL. Por ahora solo estamos
--    etiquetando dos campañas internas con códigos de dos letras, así que con
--    VARCHAR(2) sobra y nos ahorramos espacio en una tabla de 9 000 filas."
--
-- Esa justificación va a resultar cara. Guárdala: en el paso 4 del taller veremos
-- exactamente cómo falla y qué se hace al respecto.
ALTER TABLE web_events
    ADD COLUMN utm_source VARCHAR(2);

-- ¿Por qué la columna admite NULL en vez de tener un DEFAULT? Porque los 9 073
-- eventos históricos son anteriores a que existiera la atribución de campaña: no
-- es que su utm_source sea vacío, es que se desconoce. NULL comunica "no se sabe";
-- una cadena vacía comunicaría "se sabe que no tiene campaña". Elegir el default
-- equivocado es una forma silenciosa de inventar datos.

COMMENT ON COLUMN web_events.utm_source IS
    'Parámetro utm_source de la URL de origen. NULL para eventos previos a la atribución de campañas.';
