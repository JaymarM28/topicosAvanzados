-- ===========================================================================
-- R__fn_calculate_discount.sql
--
-- Descuento por volumen de compra. Devuelve la TASA (0.000 a 0.150), no el monto:
-- así quien la llame decide sobre qué base aplicarla.
-- ===========================================================================

-- ¿Por qué este script empieza con R__ y no con V__? Porque una función es lógica
-- de negocio, y la lógica de negocio cambia. Si la versionáramos, cada ajuste de
-- los tramos de descuento crearía un archivo nuevo: V...__fn_descuento_v2.sql,
-- V...__fn_descuento_v3.sql. A los seis meses tendrías veinte archivos y para
-- saber qué hace la función hoy tendrías que leerlos todos en orden.
--
-- Con R__ (repeatable) hay UN archivo que siempre refleja el estado actual. Flyway
-- guarda su checksum: si el contenido cambió, vuelve a ejecutarlo; si no, lo salta.
-- El historial de cómo evolucionó la función lo lleva git, que es su lugar natural.
--
-- La regla práctica: V__ para lo que altera datos o estructura (no se puede
-- "volver a aplicar"), R__ para lo que se puede recrear desde cero sin consecuencias
-- — funciones, procedimientos, vistas.

-- ¿Por qué CREATE OR REPLACE y no DROP + CREATE? Porque un script repeatable se
-- ejecuta muchas veces y debe ser idempotente. DROP fallaría la primera vez (no
-- existe) y rompería los permisos concedidos sobre la función en las siguientes.
CREATE OR REPLACE FUNCTION fn_calculate_discount(p_monto_bruto NUMERIC)
RETURNS NUMERIC
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    -- Un monto nulo no es un monto cero: es un dato que falta. Devolver 0 aquí
    -- escondería el problema aguas abajo, así que propagamos el NULL.
    IF p_monto_bruto IS NULL THEN
        RETURN NULL;
    END IF;

    IF p_monto_bruto < 0 THEN
        RAISE EXCEPTION 'El monto bruto no puede ser negativo (recibido: %)', p_monto_bruto;
    END IF;

    RETURN CASE
        WHEN p_monto_bruto >= 5000 THEN 0.150
        WHEN p_monto_bruto >= 2000 THEN 0.100
        WHEN p_monto_bruto >=  500 THEN 0.050
        ELSE                            0.000
    END;
END;
$$;

-- ¿Por qué IMMUTABLE? Le promete al planificador que para el mismo argumento la
-- función siempre devuelve lo mismo, sin consultar tablas ni depender de la hora.
-- Con esa garantía PostgreSQL puede cachear el resultado e incluso usar la función
-- dentro de un índice. Si algún día los tramos salieran de una tabla de parámetros,
-- habría que degradarla a STABLE: mentirle al planificador produce resultados
-- incorrectos, no solo lentos.

COMMENT ON FUNCTION fn_calculate_discount(NUMERIC) IS
    'Tasa de descuento por volumen: 5% desde USD 500, 10% desde 2000, 15% desde 5000.';
