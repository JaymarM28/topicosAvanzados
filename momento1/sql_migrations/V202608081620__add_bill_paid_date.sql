-- ===========================================================================
-- V202608081620__add_bill_paid_date.sql
--
-- Sexta migración evolutiva: nueva columna sobre una tabla existente.
-- Cobranza necesita reportar el tiempo real entre el vencimiento de una
-- factura y su pago (due_date vs. cuándo se saldó), y hoy esa fecha no se
-- guarda en ningún lado: `status` dice SI quedó pagada, pero no CUÁNDO.
-- ===========================================================================

-- ¿Por qué una columna nueva y no derivarla de policy_edit_log o de algún
-- log de auditoría? Porque no existe ninguno para bill: sp_register_payment
-- (R__sp_register_payment.sql) actualiza `balance` y `status` in place, sin
-- dejar rastro de cuándo ocurrió el pago que la dejó en cero.
--
-- ¿Por qué nullable y sin backfill? A diferencia de la migración de
-- `vehicle` (V202608081500), aquí no hay forma de reconstruir el dato: para
-- las facturas ya pagadas antes de esta migración, la fecha exacta del pago
-- nunca se registró. NULL aquí significa honestamente "se pagó, pero no
-- sabemos cuándo" — no "no se pagó" (para eso está `status`). Inventar una
-- fecha (p.ej. due_date) sería peor que no tener el dato: parecería preciso
-- sin serlo.
ALTER TABLE bill
    ADD COLUMN paid_date DATE;

COMMENT ON COLUMN bill.paid_date IS
    'Fecha en la que la factura quedó saldada (balance = 0). NULL si sigue '
    'pendiente, o si se pagó antes de que esta columna existiera y el dato '
    'no se pudo reconstruir. Columna agregada por esta migración: '
    'sp_register_payment todavía no la escribe (pendiente de una migración '
    'aparte que actualice el procedimiento).';
