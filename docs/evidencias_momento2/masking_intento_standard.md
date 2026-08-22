# Evidencia: intento de Masking Policy en cuenta Standard

**Fecha:** 2026-08-21, ~20:10 (America/Bogota)
**Contexto:** el enunciado del Momento 2 indica que si la cuenta no tiene Enterprise
Edition, no se penaliza no ejecutar la Masking Policy en vivo, siempre que la política
esté escrita y correcta y quede **evidencia del intento y del error de edición**. Esta
es esa evidencia.

## La edición de la cuenta, verificada desde la organización

```
USE ROLE ORGADMIN;
SHOW ACCOUNTS;
-- CUENTA: SJ52216 | edicion: STANDARD | org: DBXZBCC | es_org_account: true
```

## El intento

Ejecutando `momento2/json/04_rbac_masking.sql` contra la cuenta:

```
OK   CREATE ROLE IF NOT EXISTS ROLE_ANALISTA_SINIESTROS
OK   CREATE ROLE IF NOT EXISTS ROLE_GERENTE_COMERCIAL
OK   GRANT ... (los 13 grants de la sección 2, todos exitosos)

FAIL CREATE MASKING POLICY IF NOT EXISTS MASK_TELEFONO_PII ...
     000002 (0A000): Unsupported feature 'MASKING POLICY'.

FAIL ALTER TABLE STG_SINIESTROS_FLATTENED MODIFY COLUMN party_phone
       SET MASKING POLICY MASK_TELEFONO_PII
     000002 (0A000): Unsupported feature 'MASKING POLICY'.

FAIL CREATE MASKING POLICY IF NOT EXISTS MASK_DIRECCION_PII ...
     000002 (0A000): Unsupported feature 'MASKING POLICY'.

FAIL ALTER TABLE STG_SINIESTROS_FLATTENED MODIFY COLUMN party_address
       SET MASKING POLICY MASK_DIRECCION_PII
     000002 (0A000): Unsupported feature 'MASKING POLICY'.
```

## El "antes" que la política corregiría

Con los tres roles, el mismo `SELECT` sobre `STG_SINIESTROS_FLATTENED` devuelve la PII
completa — no hay ninguna protección en la columna:

```
USE ROLE ROLE_ANALISTA_SINIESTROS;  -> +57-301-215-7091 | Cl 37 Sur #45-21, Sabaneta
USE ROLE ROLE_GERENTE_COMERCIAL;    -> +57-301-215-7091 | Cl 37 Sur #45-21, Sabaneta
USE ROLE ACCOUNTADMIN;              -> +57-301-215-7091 | Cl 37 Sur #45-21, Sabaneta
```

Todo lo demás del script (roles, grants diferenciados, cambio de rol en vivo) funciona
en Standard y quedó aplicado.

## Plan

El doc del curso señala que el upgrade es self-service:
`ALTER ACCOUNT SJ52216 SET EDITION = 'ENTERPRISE'` con rol `ORGADMIN` (esta cuenta es
la Organization Account y el usuario tiene ese rol — ambas cosas verificadas). Si el
upgrade se aplica antes de la sustentación, se re-ejecuta la sección 3 de
`04_rbac_masking.sql` y la demo muestra los tres resultados distintos en vivo; si no,
esta evidencia respalda el criterio C5.
