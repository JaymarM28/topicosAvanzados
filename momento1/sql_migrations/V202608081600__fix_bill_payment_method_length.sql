-- ===========================================================================
-- V202608081600__fix_bill_payment_method_length.sql
--
-- INCIDENTE: cobranza intentó registrar un pago con tarjeta de crédito y la
-- llamada a sp_register_payment falló con:
--
--     ERROR: value too long for type character varying(2)
--
-- Causa: en V202608081510 la columna payment_method se definió como
-- VARCHAR(2), dimensionada para los códigos internos ("CC", "DB", "TR"). El
-- valor real que manda la pasarela de pagos es "credit_card".
--
-- Este script corrige el error. NO se ejecuta a mano en producción: se hace
-- commit, se abre el pull request y el pipeline lo aplica.
-- ===========================================================================

-- ¿Por qué no editamos V202608081510 y le cambiamos el 2 por un 20? Porque
-- ese script YA SE EJECUTÓ. Está registrado en flyway_schema_history junto
-- con el checksum de su contenido. Si lo editamos, en la siguiente ejecución
-- Flyway compara el checksum guardado contra el del archivo, ve que no
-- coinciden y aborta con "Migration checksum mismatch".
--
-- Y esa negativa es una característica, no un obstáculo: si se permitiera,
-- la base de desarrollo (recreada desde cero) tendría VARCHAR(20), mientras
-- que producción, donde el script viejo ya corrió, seguiría con VARCHAR(2).
-- Dos entornos con el mismo historial de migraciones y esquemas distintos —
-- justo lo que Flyway existe para eliminar.
--
-- La regla en DataOps: nunca reescribimos el pasado, hacemos ROLL FORWARD. El
-- error queda en el historial, y encima queda la corrección. Esa cicatriz es
-- el registro de auditoría: dentro de un año alguien podrá ver que la
-- columna nació corta, por qué, y cuándo se arregló.

-- ---------------------------------------------------------------------------
-- Corrección
-- ---------------------------------------------------------------------------

-- Ampliar un VARCHAR es una operación segura: PostgreSQL solo actualiza el
-- catálogo, no reescribe la tabla, y no necesita validar las filas
-- existentes porque todo lo que cabía en 2 caracteres cabe en 20. Es
-- instantáneo incluso en tablas grandes.
--
-- La operación inversa (reducir de 20 a 2) sí obliga a revisar cada fila y
-- falla si alguna no cabe. Por eso equivocarse por defecto —un tipo más
-- angosto de lo necesario— sale caro, y equivocarse por exceso casi nunca.
ALTER TABLE bill
    ALTER COLUMN payment_method TYPE VARCHAR(20);

COMMENT ON COLUMN bill.payment_method IS
    'Medio de pago usado para saldar la factura (credit_card, debit_card, bank_transfer...). '
    'NULL para facturas previas al registro de medio de pago. '
    'Ampliado de VARCHAR(2) a VARCHAR(20) el 2026-08-08 tras fallo en producción.';
