# Momento 3 — End-to-End DataOps (Final)

**Módulo:** Tendencias emergentes en desarrollo de software (SI6010-5979) · Pos ST1707
**Peso sobre la nota final:** **40 %**
**Capítulo:** 3 — Transformación y Entrega
**Se sustenta en:** [Sesión 8 — Sustentación Momento 3 (Final)](../Cap_3_Transformacion_Entrega/sesion_08_sustentacion_momento3_final/) · sábado **29/08/2026**, 08:00–11:00, aula 34-302
**Stack:** dbt Cloud · Snowflake · Streamlit in Snowflake · GitHub Actions

---

## 1. Objetivo

Integrar todo lo construido en el módulo en **un único pipeline End-to-End operable**: del
sistema fuente al dashboard, versionado, probado y automatizado. Este momento no evalúa
una tecnología nueva aislada — evalúa que **las piezas encajen** y que el estudiante pueda
sostener el conjunto.

Al terminar este momento, el estudiante debe poder responder con evidencia:

- Si el negocio pide un campo nuevo, ¿cuál es el camino desde el commit hasta el
  dashboard, y cuánto tarda?
- ¿Cómo sé que los números del dashboard son correctos?
- ¿Qué se rompe si la fuente cambia sin avisar, y cómo me entero?

---

## 2. Contexto del caso

Este momento, igual que los dos anteriores, se hace sobre el **proyecto propio** de cada
equipo — el dominio de negocio y el modelo transaccional elegidos en el Momento 1, no sobre
Parch & Posey (que en la Sesión 7 sigue siendo el ejemplo compartido de clase).

Los Momentos 1 y 2 dejaron los datos crudos del proyecto propio aterrizando en Snowflake de
forma automatizada. Pero nadie puede usarlos todavía: están en su forma normalizada de
origen, sin lógica de negocio aplicada y sin garantías de calidad.

El negocio que el equipo definió en el Momento 1 necesita responder preguntas concretas
sobre su propia operación — las mismas que motivaron el modelo de datos original. El
encargo es cerrar el camino: modelar, probar, automatizar y **entregar** esas respuestas.

> **Este momento integra los entregables de los Momentos 1 y 2.** No se evalúa como
> proyecto independiente, y no se evalúa sobre Parch & Posey.

---

## 3. Alcance

### Incluido en el alcance

1. **Proyecto dbt** conectado a Snowflake, versionado en el repositorio, con arquitectura
   en capas:
   - `staging/` — una vista por tabla fuente: renombrado, casting, limpieza básica. Sin
     joins ni lógica de negocio.
   - `intermediate/` — lógica de negocio reutilizable (opcional pero valorado).
   - `marts/` — al menos **dos modelos** listos para consumo, que respondan preguntas de
     negocio explícitas.
2. **Al menos un modelo incremental** (`materialized='incremental'`) correctamente
   implementado:
   - Con bloque `is_incremental()` y filtro sobre la fuente.
   - Con `unique_key` y estrategia de actualización elegida conscientemente.
   - Demostrando que un `dbt run` posterior procesa **solo** los registros nuevos.
3. **Pruebas de calidad de datos**:
   - Tests genéricos (`unique`, `not_null`, `accepted_values`, `relationships`) sobre las
     columnas críticas de todos los marts.
   - Al menos **un test singular** (SQL propio en `tests/`) que verifique una regla de
     negocio real — no una restricción estructural.
4. **Documentación dbt**: descripciones en `schema.yml` para todos los modelos de mart y
   sus columnas; `dbt docs generate` produce un lineage graph completo.
5. **Automatización**: un job programado en dbt Cloud (o disparado desde GitHub Actions)
   que ejecute `dbt build` y falle visiblemente cuando un test no pase.
6. **Capa de entrega — Streamlit in Snowflake**: una aplicación con mínimo:
   - Tres visualizaciones que respondan preguntas de negocio distintas.
   - Al menos un filtro interactivo.
   - Consultas exclusivamente contra los modelos de mart de dbt (**nunca** contra `RAW`).
7. **Documento de arquitectura E2E** con un diagrama del flujo completo desde Neon hasta
   Streamlit, identificando en cada tramo: qué corre, qué lo dispara y qué pasa si falla.

### Fuera del alcance

- Orquestadores externos (Airflow, Dagster, Prefect) — se mencionan en la discusión de
  cierre.
- Autenticación y control de acceso por usuario en la aplicación Streamlit.
- Optimización de costos más allá de lo razonable en tier gratuito.
- Streaming o ingesta en tiempo real.

---

## 4. Entregables

| # | Entregable | Formato | Dónde |
|---|---|---|---|
| E1 | Proyecto dbt completo (`models/`, `tests/`, `dbt_project.yml`, `packages.yml`) | Código versionado | `dbt/` del repositorio |
| E2 | Modelo incremental con evidencia de ejecución diferencial (logs de 1.ª vs 2.ª corrida) | Código + logs | `dbt/models/marts/` y `docs/evidencias/` |
| E3 | Suite de tests con salida de `dbt test` (incluyendo una falla provocada y corregida) | Código + logs | En el repositorio |
| E4 | `schema.yml` documentado + captura del lineage graph | YAML + imagen | En el repositorio |
| E5 | Job automatizado configurado, con evidencia de al menos 3 ejecuciones | Captura / enlace | `docs/evidencias/` |
| E6 | Aplicación Streamlit in Snowflake desplegada y funcional | Código `.py` + app viva | `streamlit/` del repositorio |
| E7 | Documento de arquitectura E2E con diagrama | Markdown + imagen | `docs/arquitectura_e2e.md` |
| E8 | `profiles.yml.example` y `.env.example` — **sin credenciales reales** | Texto | En el repositorio |
| E9 | Sustentación final | 15 min de exposición + 10 min de preguntas | Sesión 8 — 29/08/2026 |

### Sobre la sustentación final (E9)

Es la sustentación más exigente del módulo. **15 minutos**, con esta estructura sugerida:

1. **(2 min)** El caso de negocio y las preguntas que el pipeline responde.
2. **(3 min)** Recorrido de la arquitectura sobre el diagrama.
3. **(7 min)** **Demo en vivo del cambio E2E**: hacer un cambio real —agregar una métrica
   a un mart, por ejemplo—, commitear, ejecutar el pipeline y mostrar el resultado
   reflejado en el dashboard de Streamlit. Este es el corazón de la evaluación.
4. **(3 min)** Retrospectiva: qué fue lo más difícil, qué harías distinto, qué queda
   pendiente.

Luego, **10 minutos de preguntas** del docente y del grupo.

---

## 5. Condiciones de entrega

- **Fecha límite de código:** sábado **29/08/2026, 07:00** (una hora antes de la sesión).
- **Modalidad:** mismos equipos de los momentos anteriores.
- **Entregas tardías:** por ser el momento final del módulo, **no se aceptan entregas
  tardías** salvo excusa institucional formal.
- **Verificar vigencia de los trials** (Snowflake, dbt Cloud) con anticipación. Un trial
  vencido el día de la sustentación no es causal de reprogramación.

---

## 6. Rúbrica de evaluación

**Total: 100 puntos** → equivalen al 40 % de la nota final.

### C1. Arquitectura del proyecto dbt — 15 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 14–15 | Capas staging/intermediate/marts con responsabilidades limpias y sin fugas de lógica entre capas. Uso consistente de `ref()` y `source()`. Convención de nombres coherente. Configuración por capa en `dbt_project.yml`. |
| Bueno | 10–13 | Capas presentes, pero hay lógica de negocio en staging o marts que consultan sources directamente. |
| Suficiente | 6–9 | Modelos planos sin capas, o SQL duplicado entre modelos. |
| Insuficiente | 0–5 | Proyecto dbt que no compila, o modelos que no usan `ref()`. |

### C2. Modelo incremental — 20 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 18–20 | `is_incremental()` correctamente implementado con `unique_key` y estrategia justificada. Se demuestra en vivo que la segunda corrida procesa solo lo nuevo (logs comparativos). Contempla el caso de `--full-refresh`. Explica el riesgo de late-arriving data. |
| Bueno | 13–17 | Incremental funciona y se demuestra, pero sin manejo de duplicados o sin justificar la estrategia. |
| Suficiente | 8–12 | El modelo está marcado como incremental pero reprocesa todo, o el filtro es incorrecto. |
| Insuficiente | 0–7 | No hay modelo incremental. |

### C3. Pruebas de calidad de datos — 20 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 18–20 | Tests genéricos cubren llaves y relaciones de todos los marts. Al menos un test singular sobre una **regla de negocio real** (no estructural). Se demuestra una falla provocada, su diagnóstico y su corrección. Severidad configurada donde tiene sentido. |
| Bueno | 13–17 | Buena cobertura de tests genéricos y un test singular presente, pero sin evidencia de falla real. |
| Suficiente | 8–12 | Solo tests genéricos, o cobertura parcial de los marts. |
| Insuficiente | 0–7 | Sin tests, o tests que nunca se han ejecutado. |

### C4. Documentación y lineage — 10 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 9–10 | Todos los marts y sus columnas descritos con lenguaje de negocio, no técnico. Lineage graph completo y legible. Sources documentadas con su origen. |
| Bueno | 6–8 | Documentación presente en los modelos principales, con vacíos en columnas. |
| Suficiente | 3–5 | `schema.yml` mínimo, descripciones genéricas o copiadas del nombre de la columna. |
| Insuficiente | 0–2 | Sin documentación. |

### C5. Aplicación Streamlit — 15 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 14–15 | App desplegada y funcional en Snowflake. ≥3 visualizaciones que responden preguntas de negocio distintas y bien elegidas para el tipo de dato. Filtro interactivo funcional. Consulta exclusivamente los marts. Carga en tiempo razonable. |
| Bueno | 10–13 | App funcional con las visualizaciones requeridas, pero con elecciones de gráfico cuestionables o sin interactividad real. |
| Suficiente | 6–9 | App con menos de 3 visualizaciones, o que consulta tablas `RAW` en lugar de marts. |
| Insuficiente | 0–5 | App no desplegada o no funcional. |

### C6. Automatización e integración E2E — 10 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 9–10 | Job programado ejecutándose con historial de corridas exitosas. `dbt build` falla visiblemente ante tests rotos. El cambio E2E demostrado en vivo fluye sin intervención manual. |
| Bueno | 6–8 | Job configurado y funcionando, pero el flujo E2E requiere algún paso manual. |
| Suficiente | 3–5 | Solo ejecución manual del pipeline. |
| Insuficiente | 0–2 | Sin automatización. |

### C7. Sustentación final — 10 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 9–10 | Demo del cambio E2E en vivo, exitosa y dentro del tiempo. Discurso articulado que conecta decisiones técnicas con necesidades de negocio. Retrospectiva honesta y con criterio. Responde con solvencia preguntas no anticipadas. |
| Bueno | 6–8 | Demo funciona; buena explicación técnica pero débil conexión con el negocio, o retrospectiva superficial. |
| Suficiente | 3–5 | Presenta capturas en lugar de demo en vivo, o excede considerablemente el tiempo. |
| Insuficiente | 0–2 | No sustenta, o no puede explicar componentes de su propio pipeline. |

---

## 7. Criterio integrador

Más allá de la rúbrica por componentes, se valora que el pipeline **funcione como un
sistema**: que un cambio en el origen se propague de forma trazable hasta el consumo, que
los fallos sean visibles y diagnosticables, y que un tercero pueda operarlo con la
documentación entregada.

Un conjunto de piezas técnicamente correctas pero desconectadas entre sí **no cumple el
objetivo del módulo**.

---

## 8. Recursos

- Sesión 7 — [dbt e incremental models](../Cap_3_Transformacion_Entrega/sesion_07_dbt_incremental/)
- Momento 1 — [CI/CD en Base de Datos](momento_1_cicd_bd.md)
- Momento 2 — [Cloud DW e Ingesta](momento_2_cloud_dw.md)
- dbt — Incremental models: https://docs.getdbt.com/docs/build/incremental-models
- dbt — Tests: https://docs.getdbt.com/docs/build/data-tests
- Streamlit in Snowflake: https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit
