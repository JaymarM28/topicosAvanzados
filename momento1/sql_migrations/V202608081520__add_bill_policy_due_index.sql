-- ===========================================================================
-- V202608081520__add_bill_policy_due_index.sql
--
-- Tercera migración evolutiva: índice sobre una tabla existente.
-- Responde a una solicitud del equipo de producto: el dashboard de cobranza
-- está lento al listar las próximas facturas por vencer de una póliza.
-- ===========================================================================

-- La query real es "dame las facturas de ESTA póliza ordenadas por
-- vencimiento": filtra por policy_id y ordena por due_date. Un índice
-- compuesto en ese orden permite a PostgreSQL localizar el bloque de la
-- póliza y leer las filas ya ordenadas, sin un paso de sort aparte.
--
-- El orden de las columnas importa: primero lo que se filtra (policy_id),
-- luego lo que se ordena (due_date). Invertirlo haría el índice inútil para
-- esta consulta.
CREATE INDEX idx_bill_policy_due
    ON bill (policy_id, due_date);
