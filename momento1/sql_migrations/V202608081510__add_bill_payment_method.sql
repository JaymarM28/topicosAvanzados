-- ===========================================================================
-- V202608081510__add_bill_payment_method.sql
--
-- Segunda migración evolutiva: columna nueva sobre una tabla existente.
--
-- Nota del equipo de cobranza que solicitó el cambio:
--   "Por ahora solo aceptamos tres medios de pago y los identificamos con
--    código de dos letras: CC (tarjeta de crédito), DB (débito), TR
--    (transferencia). Con VARCHAR(2) sobra."
--
-- Esa justificación va a resultar cara. Guárdala: en
-- V202608081600__fix_bill_payment_method_length.sql veremos exactamente cómo
-- falla y qué se hace al respecto.
-- ===========================================================================

ALTER TABLE bill
    ADD COLUMN payment_method VARCHAR(2);

-- ¿Por qué admite NULL en vez de tener un DEFAULT? Las facturas ya cargadas en
-- la Sesión 1 son anteriores a que existiera el registro de medio de pago: no
-- es que se sepa que no tienen uno, es que se desconoce. NULL comunica "no se
-- sabe"; un default fijo inventaría un dato que nunca se capturó.
COMMENT ON COLUMN bill.payment_method IS
    'Medio de pago usado para saldar la factura. NULL para facturas previas al registro de medio de pago.';
