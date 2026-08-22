# Ingesta semi-estructurada, Tasks y gobernanza — Momento 2

Equipo 5 · RutaSegura — siniestros del call center (JSON)

El segundo camino de ingesta del Momento 2: una fuente JSON del dominio, cargada vía
External Stage a `VARIANT`, aplanada con `LATERAL FLATTEN`, orquestada con un DAG de
Snowflake Tasks y protegida con RBAC + Masking Policy.

```
bucket S3 ──(COPY, task raíz)──► RAW_JSON.RAW_SINIESTROS (VARIANT)
                                        │ LATERAL FLATTEN (task hija, AFTER)
                                        ▼
                          RAW_JSON.STG_SINIESTROS_FLATTENED ◄─ Masking Policy (PII)
                                        │
                     cruza con RAW.POLICY / RAW.VEHICLE por policy_number y vin
```

## Archivos, en orden de ejecución

| Archivo | Qué hace |
|---|---|
| `generar_siniestros_mock.py` | Genera los 3 exports JSON mock (semilla fija, reproducible) |
| `01_esquema_y_stage.sql` | Schema `RAW_JSON`, `FILE FORMAT` JSON, External Stage |
| `02_tablas_raw_y_staging.sql` | `RAW_SINIESTROS` (VARIANT) + `COPY` + `FLATTEN` + staging |
| `03_dag_tasks.sql` | DAG: `TASK_INGESTA_SINIESTROS` (raíz, cron) → `TASK_APLANAR_SINIESTROS` (AFTER) |
| `04_rbac_masking.sql` | 2 roles de negocio + Masking Policies sobre teléfono y dirección |

Antes de ejecutar `01`, **reemplazar la URL del bucket** (`s3://BUCKET-DEL-EQUIPO-PENDIENTE/`)
por la real. Los mocks de `datos_mock/` se suben al bucket con la policy de lectura
pública del curso. Para desarrollo sin bucket existe la variante interna comentada en
`01` (`PUT` local) — todo lo demás funciona idéntico.

## El porqué de cada decisión

- **Fuente elegida y alternativas**: [`docs/decisiones_momento2.md`](../../docs/decisiones_momento2.md), sección A.
- **Estrategia de roles y máscara**: misma, sección B.
- **Evidencias** (Masking en Standard, drift provocado): [`docs/evidencias_momento2/`](../../docs/evidencias_momento2/).

## Estado verificado (2026-08-21, cuenta del equipo)

- `COPY` cargó los 3 exports → 12 siniestros en `RAW_SINIESTROS`.
- `FLATTEN` → 20 involucrados en `STG_SINIESTROS_FLATTENED`; los campos que solo
  existen en exports recientes (`email`, `assigned_workshop`) salen `NULL` en los
  viejos, sin error.
- DAG: raíz `SUCCEEDED`, hija disparada por `AFTER` y `SUCCEEDED` 1.5 s después
  (`TASK_HISTORY` como evidencia). Suspendido en orden correcto (raíz primero).
- RBAC: ambos roles creados, grants diferenciados, cambio de rol en vivo.
- Masking: pendiente del upgrade a Enterprise — el intento en Standard quedó
  documentado como evidencia.
