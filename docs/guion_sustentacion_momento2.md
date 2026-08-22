# Guion de sustentación — Momento 2 (22/08/2026, 08:00)

Equipo 5 · RutaSegura. Demo de 10 minutos + 5 de preguntas. Todo lo de abajo está
probado contra la cuenta del equipo la noche anterior — nada es teórico.

## Antes de salir de casa (checklist)

- [ ] `git pull` en la máquina que presenta (los scripts y este guion están en `main`).
- [ ] `momento2/.env` completo en esa máquina, con la llave RSA configurada
      (`SNOWFLAKE_PRIVATE_KEY_PATH`) — la demo no puede depender del MFA del celular.
- [ ] Snowsight abierto con un Worksheet que ya tenga pegados `json/02`, `json/03` y
      `json/04` (para no pegar SQL en vivo).
- [ ] `uv run carga/cargar.py` corrido una vez esa mañana (verifica conectividad).
- [ ] El DAG debe estar **suspended** al empezar (así el "encender" es parte del show).

## Los 10 minutos

**0–1 · Contexto.** Dos fuentes: la transaccional de Neon (Momento 1) y los exports
JSON del call center de siniestros. Ambos caminos construidos, orquestados y
gobernados. Diagrama: `momento2/json/README.md`.

**1–3 · Relacional + schema drift (C2).**
1. `uv run carga/cargar.py` → 7/7 tablas.
2. Drift en vivo (guion detallado en `docs/evidencias_momento2/drift_provocado_y_corregido.md`):
   columna extra en `coverage.csv` → el script falla ANTES de tocar nada, nombra la
   columna y entrega el `ALTER TABLE` → se aplica en Snowsight → recarga en verde.

**3–5 · JSON + FLATTEN (C3).** Del Worksheet (`json/02`):
- Notación de punto sobre `RAW_SINIESTROS`.
- `LATERAL FLATTEN` de `involved_parties` — señalar que `email` es `NULL` en la
  semana 1: el proveedor lo agregó en la 2 y nada se rompió (schema-on-read).
- El JOIN con `RAW.POLICY`: daño estimado por póliza real — los dos mundos se cruzan.

**5–7 · DAG de Tasks (C4).** Del Worksheet (`json/03`):
- `SYSTEM$TASK_DEPENDENTS_ENABLE(...)` → `SHOW TASKS` (ambas `started`).
- `EXECUTE TASK TASK_INGESTA_SINIESTROS` → mientras corre, explicar raíz/hija.
- Las dos queries de `TASK_HISTORY` filtradas por nombre → ambas `SUCCEEDED`.
- Apagar: **raíz primero** (`ALTER TASK ... SUSPEND` x2). Si preguntan por qué:
  con la raíz activa, Snowflake bloquea cambios sobre las dependientes (error 091421).

**7–9 · RBAC + máscara (C5).** El mismo `SELECT` con tres roles
(`ROLE_ANALISTA_SINIESTROS`, `ROLE_GERENTE_COMERCIAL`, `ACCOUNTADMIN`):
- Con Enterprise: tres resultados distintos en vivo (completo / prefijo / oculto).
- Sin Enterprise: mostrar los grants diferenciados en vivo, la política en `json/04`,
  y `docs/evidencias_momento2/masking_intento_standard.md` — el enunciado acepta el
  intento documentado sin penalización.

**9–10 · Cierre.** Todo salió de scripts versionados; el Query History de la cuenta
muestra que ningún objeto se creó por la UI.

## Preguntas probables (y la respuesta corta)

- **¿Por qué la fuente de siniestros?** Es el hueco operativo que el modelo del
  Momento 1 no cubre, cruza por `policy_number`/`vin` reales, y su array de
  involucrados trae PII genuina. Alternativas descartadas en
  `docs/decisiones_momento2.md`, sección A.
- **¿Por qué frenar ante drift en el camino relacional pero absorberlo en el JSON?**
  Porque en el relacional una columna nueva es una decisión humana que el DW no debe
  tragarse solo; en el JSON absorber cambios del proveedor es el objetivo del
  schema-on-read. Cada dominio con su contrato (sección C del mismo doc).
- **¿Por qué la task hija no tiene SCHEDULE?** `AFTER` = corre solo si la raíz
  terminó con éxito; con schedule propio podría correr sobre un RAW a medio cargar.
- **¿Por qué ni ACCOUNTADMIN ve los teléfonos?** Default cerrado: administrar la
  plataforma no es necesitar el dato. Un rol nuevo nace sin acceso a PII.
- **¿Cómo se autentica el pipeline sin humano?** Par de llaves RSA (Snowflake exige
  MFA para contraseñas); la privada vive fuera del repo.
- **¿Qué pasa si corren la carga dos veces?** Relacional: `DELETE`+`COPY` en
  transacción, mismos conteos (demostrable). JSON: el load metadata salta archivos ya
  cargados — incremental por diseño, correcto para exports que no cambian.

## Reparto sugerido

- Contexto + relacional/drift: quien hizo la extracción.
- JSON + FLATTEN: quien hizo la bitácora/setup.
- DAG + RBAC + cierre: David (la cuenta es la suya).
Los tres deben poder responder cualquiera de las preguntas de arriba.
