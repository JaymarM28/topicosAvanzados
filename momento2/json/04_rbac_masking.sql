-- ---------------------------------------------------------------------------
-- 04_rbac_masking.sql — RBAC y protección de PII (Momento 2, punto 5)
-- Equipo 5 · RutaSegura — gobernanza sobre los datos de siniestros
--
-- Dos roles de negocio con necesidades de acceso reales y distintas, y una
-- Masking Policy sobre el teléfono de los involucrados en siniestros.
--
-- Requiere Enterprise Edition para CREATE MASKING POLICY. En cuenta Standard,
-- todo lo anterior a la sección 3 funciona igual; la política falla con
-- "Unsupported feature 'MASKING POLICY'" — ese error, documentado, es la
-- evidencia de intento que el enunciado acepta.
-- ---------------------------------------------------------------------------

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE WH_VEHICLE_COVERGE;
USE DATABASE VEHICLE_COVERAGE;
USE SCHEMA RAW_JSON;

-- ---------------------------------------------------------------------------
-- 1. Los roles de negocio
-- ---------------------------------------------------------------------------
--
-- Los roles modelan FUNCIONES del negocio, no personas — las personas rotan, la
-- función queda. Dos funciones con necesidades genuinamente distintas:
--
--   ANALISTA_SINIESTROS  gestiona los casos: LLAMA a los involucrados, así que
--                        necesita el teléfono completo. Su mundo es el dominio
--                        de siniestros; no necesita ver la facturación.
--
--   GERENTE_COMERCIAL    lee el negocio completo (pólizas, facturación, y el
--                        agregado de siniestros), pero no gestiona casos: no
--                        tiene por qué ver el teléfono de un tercero. Contacta
--                        clientes a través del equipo de siniestros, no directo.
CREATE ROLE IF NOT EXISTS ROLE_ANALISTA_SINIESTROS
    COMMENT = 'Gestion de casos de siniestros. Ve la PII de los involucrados: los llama.';
CREATE ROLE IF NOT EXISTS ROLE_GERENTE_COMERCIAL
    COMMENT = 'Vision de negocio: polizas, facturacion y agregados de siniestros. Sin PII de terceros.';

-- ---------------------------------------------------------------------------
-- 2. Grants — deliberados y distintos entre sí (no "todos ven todo")
-- ---------------------------------------------------------------------------

-- Lo común: ambos pueden computar y llegar a la base.
GRANT USAGE ON WAREHOUSE WH_VEHICLE_COVERGE TO ROLE ROLE_ANALISTA_SINIESTROS;
GRANT USAGE ON WAREHOUSE WH_VEHICLE_COVERGE TO ROLE ROLE_GERENTE_COMERCIAL;
GRANT USAGE ON DATABASE VEHICLE_COVERAGE TO ROLE ROLE_ANALISTA_SINIESTROS;
GRANT USAGE ON DATABASE VEHICLE_COVERAGE TO ROLE ROLE_GERENTE_COMERCIAL;

-- El analista vive en el dominio de siniestros — y solo ahí.
GRANT USAGE  ON SCHEMA VEHICLE_COVERAGE.RAW_JSON TO ROLE ROLE_ANALISTA_SINIESTROS;
GRANT SELECT ON TABLE VEHICLE_COVERAGE.RAW_JSON.STG_SINIESTROS_FLATTENED TO ROLE ROLE_ANALISTA_SINIESTROS;
-- Nótese lo que NO tiene: ni RAW relacional (facturación), ni RAW_SINIESTROS (el
-- VARIANT crudo — leerlo directo saltaría por encima de cualquier política que
-- proteja el staging).

-- El gerente ve ambos dominios... pero el semi-estructurado solo aplanado.
GRANT USAGE  ON SCHEMA VEHICLE_COVERAGE.RAW      TO ROLE ROLE_GERENTE_COMERCIAL;
GRANT SELECT ON ALL TABLES IN SCHEMA VEHICLE_COVERAGE.RAW TO ROLE ROLE_GERENTE_COMERCIAL;
GRANT USAGE  ON SCHEMA VEHICLE_COVERAGE.RAW_JSON TO ROLE ROLE_GERENTE_COMERCIAL;
GRANT SELECT ON TABLE VEHICLE_COVERAGE.RAW_JSON.STG_SINIESTROS_FLATTENED TO ROLE ROLE_GERENTE_COMERCIAL;

-- Para poder demostrar la diferencia en vivo, el usuario del equipo asume ambos
-- roles (USE ROLE cambia el contexto; la política reacciona al rol ACTIVO):
GRANT ROLE ROLE_ANALISTA_SINIESTROS TO USER DAV;
GRANT ROLE ROLE_GERENTE_COMERCIAL   TO USER DAV;

-- ---------------------------------------------------------------------------
-- 3. La Masking Policy — la protección vive con el dato  [requiere Enterprise]
-- ---------------------------------------------------------------------------
--
-- La alternativa sin masking sería una vista "segura" por rol. El problema: cada
-- consumidor nuevo tiene que ACORDARSE de usar la vista y no la tabla. Con la
-- política, la regla viaja pegada a la columna: cualquier query, de cualquier
-- herramienta, de cualquier consumidor futuro, pasa por ella. La disciplina deja
-- de depender de quien escribe el SELECT.
CREATE MASKING POLICY IF NOT EXISTS MASK_TELEFONO_PII
    AS (val STRING) RETURNS STRING ->
    CASE
        -- El analista llama a la gente: teléfono completo.
        WHEN CURRENT_ROLE() = 'ROLE_ANALISTA_SINIESTROS' THEN val
        -- El gerente ve que HAY un teléfono y su prefijo (útil para saber si es
        -- móvil nacional), nunca el número marcable.
        WHEN CURRENT_ROLE() = 'ROLE_GERENTE_COMERCIAL' THEN LEFT(val, 7) || '-***-****'
        -- Cualquier otro rol — incluido ACCOUNTADMIN y los que se creen después —
        -- no ve nada. El default es cerrado: un rol nuevo nace sin acceso a la
        -- PII, no con él.
        ELSE '+**-***-***-****'
    END
    COMMENT = 'Telefonos de involucrados en siniestros: completo para el analista, prefijo para el gerente, oculto para el resto.';

ALTER TABLE STG_SINIESTROS_FLATTENED
    MODIFY COLUMN party_phone
    SET MASKING POLICY MASK_TELEFONO_PII;

-- La dirección personal es igual de sensible y más simple: nadie fuera de
-- gestión de casos la necesita nunca.
CREATE MASKING POLICY IF NOT EXISTS MASK_DIRECCION_PII
    AS (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() = 'ROLE_ANALISTA_SINIESTROS' THEN val
        ELSE '*** direccion protegida ***'
    END
    COMMENT = 'Direcciones de involucrados: solo gestion de siniestros.';

ALTER TABLE STG_SINIESTROS_FLATTENED
    MODIFY COLUMN party_address
    SET MASKING POLICY MASK_DIRECCION_PII;

-- ---------------------------------------------------------------------------
-- 4. La demo: mismo SELECT, tres resultados
-- ---------------------------------------------------------------------------

USE ROLE ROLE_ANALISTA_SINIESTROS;
SELECT party_name, party_phone, party_address
FROM VEHICLE_COVERAGE.RAW_JSON.STG_SINIESTROS_FLATTENED LIMIT 3;
--> +57-301-215-7091 completo, dirección completa

USE ROLE ROLE_GERENTE_COMERCIAL;
SELECT party_name, party_phone, party_address
FROM VEHICLE_COVERAGE.RAW_JSON.STG_SINIESTROS_FLATTENED LIMIT 3;
--> +57-301-***-****, direccion protegida

USE ROLE ACCOUNTADMIN;
SELECT party_name, party_phone, party_address
FROM VEHICLE_COVERAGE.RAW_JSON.STG_SINIESTROS_FLATTENED LIMIT 3;
--> +**-***-***-**** — ni el administrador ve la PII: administrar la plataforma
--  no es lo mismo que necesitar el dato.
