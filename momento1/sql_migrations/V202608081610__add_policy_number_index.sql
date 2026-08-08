-- ===========================================================================
-- V202608081610__add_policy_number_index.sql
--
-- Quinta migración evolutiva: índice único sobre una columna existente.
-- Responde a un hallazgo de soporte: el buscador de pólizas por número
-- (policy_number) hace un seq scan completo sobre `policy`, y nada impide
-- hoy que dos filas compartan el mismo número.
-- ===========================================================================

-- policy_number es el identificador que usa el cliente y cobranza para
-- ubicar una póliza (por teléfono, por el PDF de la carátula). Un índice
-- único resuelve dos problemas a la vez: acelera ese lookup y convierte en
-- error de base de datos lo que hoy solo se podía detectar a mano.
--
-- ¿Por qué UNIQUE y no un índice simple? Porque policy_number ya debería ser
-- único por regla de negocio (es el número que se le entrega al asegurado).
-- Si la carga inicial tuviera duplicados, este CREATE fallaría y eso es
-- preferible a descubrirlo después, con la restricción ya en producción y
-- datos sucios encima.
CREATE UNIQUE INDEX idx_policy_policy_number
    ON policy (policy_number);
