-- ===========================================================================
-- R__fn_calculate_late_fee.sql
--
-- Recargo por mora sobre el saldo de una factura. Devuelve la TASA
-- (0.000 a 0.100), no el monto: así quien la llame decide sobre qué base
-- aplicarla.
-- ===========================================================================

-- ¿Por qué R__ y no V__? Porque es lógica de negocio, y la política de mora
-- cambia con el tiempo. Versionarla crearía un archivo nuevo cada vez que
-- cobranza ajuste los tramos: V...__fn_mora_v2.sql, V...__fn_mora_v3.sql. Con
-- R__ hay un solo archivo que siempre refleja la política vigente, y git
-- lleva el historial de cómo llegó ahí.

-- ¿Por qué recibe los días de atraso como parámetro en vez de calcularlos
-- internamente con CURRENT_DATE? Porque una función IMMUTABLE le promete al
-- planificador que, para el mismo argumento, siempre devuelve lo mismo.
-- CURRENT_DATE cambia todos los días — usarlo aquí dentro rompería esa
-- promesa. Quien llama ya sabe la fecha de vencimiento y la de hoy; que la
-- resta viva afuera mantiene la función honestamente pura.
CREATE OR REPLACE FUNCTION fn_calculate_late_fee(p_dias_atraso INTEGER, p_balance NUMERIC)
RETURNS NUMERIC
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    -- Un balance nulo no es un balance cero: es un dato que falta. Propagar
    -- el NULL evita esconder el problema aguas abajo.
    IF p_dias_atraso IS NULL OR p_balance IS NULL THEN
        RETURN NULL;
    END IF;

    IF p_balance < 0 THEN
        RAISE EXCEPTION 'El saldo de la factura no puede ser negativo (recibido: %)', p_balance;
    END IF;

    RETURN CASE
        WHEN p_dias_atraso <= 0  THEN 0.000
        WHEN p_dias_atraso <= 15 THEN 0.020
        WHEN p_dias_atraso <= 30 THEN 0.050
        ELSE                          0.100
    END;
END;
$$;

COMMENT ON FUNCTION fn_calculate_late_fee(INTEGER, NUMERIC) IS
    'Tasa de recargo por mora: 2% hasta 15 días de atraso, 5% hasta 30, 10% después.';
