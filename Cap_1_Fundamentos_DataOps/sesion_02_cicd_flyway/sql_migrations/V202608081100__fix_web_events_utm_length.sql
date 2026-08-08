-- ===========================================================================
-- V202608081100__fix_web_events_utm_length.sql
--
-- INCIDENTE: el backend intentó registrar una visita proveniente de Google Ads y
-- la llamada a sp_process_order falló con:
--
--     ERROR: value too long for type character varying(2)
--
-- Causa: en V202608081000 la columna utm_source se definió como VARCHAR(2),
-- dimensionada para códigos internos de dos letras. Los valores reales que envían
-- las plataformas de campañas son "google", "facebook", "linkedin", "newsletter".
--
-- Este script corrige el error. NO se ejecuta a mano en producción: se hace commit,
-- se abre el pull request y el pipeline lo aplica.
-- ===========================================================================

-- ¿Por qué no simplemente editamos el archivo V202608081000 y le cambiamos el 2 por
-- un 100? Porque ese script YA SE EJECUTÓ. Está registrado en flyway_schema_history
-- junto con el checksum de su contenido. Si lo editas, en la siguiente ejecución
-- Flyway compara el checksum guardado con el del archivo, ve que no coinciden y
-- aborta con "Migration checksum mismatch".
--
-- Y esa negativa es una característica, no un obstáculo. Piensa qué pasaría si lo
-- permitiera: tu base de desarrollo, donde borraste todo y volviste a migrar,
-- tendría VARCHAR(100). Producción, donde el script viejo ya corrió, seguiría con
-- VARCHAR(2). Dos entornos con el mismo historial de migraciones y esquemas
-- distintos — que es exactamente el problema que Flyway existe para eliminar.
--
-- La regla en DataOps: nunca reescribimos el pasado, hacemos ROLL FORWARD. El error
-- queda en el historial, y encima queda la corrección. Esa cicatriz es el registro
-- de auditoría: dentro de un año alguien podrá ver que la columna nació corta, por
-- qué, y cuándo se arregló.

-- ---------------------------------------------------------------------------
-- Corrección
-- ---------------------------------------------------------------------------

-- Ampliar el tipo de un VARCHAR es una operación segura: PostgreSQL solo actualiza
-- el catálogo, no reescribe la tabla, y no necesita validar las filas existentes
-- porque todo lo que cabía en 2 caracteres cabe en 100. Es instantáneo incluso en
-- tablas grandes.
--
-- La operación inversa (reducir de 100 a 2) SÍ obliga a revisar cada fila y falla
-- si alguna no cabe. Por eso equivocarse por defecto —definir un tipo más estrecho
-- de lo necesario— sale caro, y equivocarse por exceso casi nunca.
ALTER TABLE web_events
    ALTER COLUMN utm_source TYPE VARCHAR(100);

COMMENT ON COLUMN web_events.utm_source IS
    'Parámetro utm_source de la URL de origen (google, facebook, newsletter...). '
    'NULL para eventos previos a la atribución de campañas. '
    'Ampliado de VARCHAR(2) a VARCHAR(100) el 2026-08-08 tras fallo en producción.';
