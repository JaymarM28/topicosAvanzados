# Momento 2 — Cloud Data Warehouse e Ingesta

**Módulo:** Tendencias emergentes en desarrollo de software (SI6010-5979) · Pos ST1707
**Peso sobre la nota final:** **30 %**
**Capítulo:** 2 — Modern Data Warehouse
**Se sustenta en:** [Sesión 6 — Sustentación Momento 2](../Cap_2_Modern_Data_Warehouse/sesion_06_sustentacion_momento2/) · sábado **22/08/2026**, 08:00–11:00, aula 33-302
**Stack:** Snowflake (Internal Stages) · Python gestionado con `uv` · Neon.tech como fuente

---

## 1. Objetivo

Demostrar que el estudiante puede **mover datos desde un sistema transaccional hacia un
Cloud Data Warehouse de forma programática, repetible y gobernada** — es decir, mediante
código versionado que otra persona pueda ejecutar y obtener el mismo resultado.

Al terminar este momento, el estudiante debe poder responder con evidencia:

- ¿Cómo llegan los datos de Neon a Snowflake, y quién ejecuta ese proceso?
- Si el proceso se corre dos veces, ¿se duplican los datos?
- ¿Dónde queda registro de qué se cargó, cuándo y con qué resultado?

---

## 2. Contexto del caso

En clase trabajamos las Sesiones 4 y 5 sobre Parch & Posey, como ejemplo compartido. **Este
momento evaluativo no se hace sobre Parch & Posey**: continúa sobre el **proyecto propio**
de cada equipo — el dominio de negocio y el modelo transaccional que diseñaron y
desplegaron en el Momento 1.

El Momento 1 dejó esa base de datos transaccional versionada y desplegada
automáticamente. Pero el equipo analítico no puede consultarla: las queries pesadas
degradan el sistema operacional, y el modelo relacional normalizado no responde bien a
preguntas agregadas.

La solución es separar cargas: llevar los datos del proyecto propio a **Snowflake**, donde
el cómputo analítico escala independientemente. El encargo es construir ese camino de
ingesta.

> **Este momento parte del entregable del Momento 1.** La fuente de datos es la base de
> datos Neon del proyecto propio del equipo, ya versionada con Flyway — no Parch & Posey.

---

## 3. Alcance

### Incluido en el alcance

1. **Arquitectura de la cuenta Snowflake** creada por código (script SQL versionado):
   - Base de datos, esquemas por capa (`RAW`, y al menos un esquema de trabajo).
   - Warehouse dimensionado apropiadamente (X-SMALL con auto-suspend).
   - Un rol y un usuario de servicio con permisos mínimos necesarios.
2. **Script de extracción en Python**, gestionado con `uv`:
   - Proyecto propio con su `pyproject.toml` y `uv.lock` (creado con `uv init` /
     `uv add`, **no** con `pip` ni `requirements.txt` escrito a mano).
   - Se conecta a Neon, extrae las tablas del modelo propio del equipo (el diseñado en el
     Momento 1) y genera archivos planos (CSV o similar) en una carpeta local de trabajo.
   - Parametrizado por variables de entorno — cero credenciales en el código.
3. **Carga vía Internal Stage**:
   - Creación del stage (`CREATE STAGE`).
   - Subida de archivos con `PUT`.
   - Carga a tablas con `COPY INTO`, con `FILE FORMAT` explícito y manejo de errores
     (`ON_ERROR`).
4. **Idempotencia**: ejecutar el proceso completo dos veces seguidas debe dejar el DW en
   un estado consistente (no duplicar filas). La estrategia queda a criterio del
   estudiante — truncate-and-load, merge, o carga por lotes con deduplicación — pero debe
   estar **justificada**.
5. **Bitácora de carga**: una tabla de control en Snowflake que registre, por ejecución:
   tabla cargada, filas cargadas, timestamp y estado.
6. **Validación post-carga**: al menos tres verificaciones automatizadas — por ejemplo,
   conteo origen vs. destino, ausencia de nulos en llaves primarias, rango de fechas
   esperado.

### Fuera del alcance

- dbt y modelado analítico (Momento 3).
- External Stages (S3/GCS/Azure) — se mencionan pero no se implementan.
- Snowpipe, streams y tasks — se discuten conceptualmente.
- Cualquier capa de visualización.

---

## 4. Entregables

| # | Entregable | Formato | Dónde |
|---|---|---|---|
| E1 | Scripts SQL de creación de la arquitectura Snowflake | `.sql` versionados | `snowflake/setup/` del repositorio |
| E2 | Proyecto Python de extracción con `pyproject.toml` + `uv.lock` | Código | `ingesta/` del repositorio |
| E3 | Scripts de carga (`PUT` + `COPY INTO`) con file format explícito | `.sql` o Python | En el repositorio |
| E4 | Tabla de bitácora + evidencia de al menos 2 ejecuciones registradas | Script DDL + captura de la tabla poblada | En el repositorio |
| E5 | Suite de validaciones post-carga con su resultado | Script + salida | `validaciones/` del repositorio |
| E6 | `.env.example` documentando todas las variables requeridas | Texto | Raíz del repositorio |
| E7 | Documento de decisiones (1–2 páginas): estrategia de idempotencia elegida y por qué | Markdown | `docs/` del repositorio |
| E8 | Sustentación oral | 10 min de exposición + 5 min de preguntas | Sesión 6 — 22/08/2026 |

### Sobre la sustentación (E8)

**Demo en vivo obligatoria:** ejecutar el pipeline de ingesta completo de extremo a
extremo delante del grupo, y luego **ejecutarlo una segunda vez** para demostrar la
idempotencia. Mostrar la bitácora antes y después.

---

## 5. Condiciones de entrega

- **Fecha límite de código:** sábado **22/08/2026, 07:00** (una hora antes de la sesión).
- **Modalidad:** mismos equipos del Momento 1. Cambios de equipo deben avisarse con
  anticipación al docente.
- **Entregas tardías:** se califican sobre el 70 % hasta 48 horas después.
- **Cuidado con el trial de Snowflake:** son 30 días. Si iniciaste tu trial antes del
  01/08, verifica que siga vigente el 22/08 y avisa al docente si no lo está.

---

## 6. Rúbrica de evaluación

**Total: 100 puntos** → equivalen al 30 % de la nota final.

### C1. Arquitectura Snowflake como código — 15 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 14–15 | Todo el setup es reproducible desde scripts versionados. Separación de esquemas por capa con propósito claro. Warehouse con auto-suspend configurado. Rol de servicio con permisos mínimos, no `ACCOUNTADMIN`. |
| Bueno | 10–13 | Setup scriptado y funcional, pero usa un rol sobre-privilegiado o no separa capas. |
| Suficiente | 6–9 | Objetos creados parcialmente a mano por la UI; scripts incompletos. |
| Insuficiente | 0–5 | Todo creado por interfaz gráfica, sin scripts. |

### C2. Extracción en Python con `uv` — 20 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 18–20 | Proyecto con `pyproject.toml` y `uv.lock` versionados. `uv sync && uv run <script>` funciona en una máquina limpia. Código legible, con manejo de errores y logging. Credenciales solo por variables de entorno. |
| Bueno | 13–17 | Corre correctamente con `uv`, pero el código tiene poco manejo de errores o falta el lockfile. |
| Suficiente | 8–12 | Funciona, pero usa `requirements.txt` escrito a mano o instrucciones basadas en `pip install` — incumple la convención del curso. |
| Insuficiente | 0–7 | El script no corre de forma reproducible, o tiene credenciales hardcodeadas. |

### C3. Carga vía Internal Stages — 20 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 18–20 | Stage creado por código. `PUT` y `COPY INTO` correctos, con `FILE FORMAT` explícito y nombrado. Política de `ON_ERROR` elegida conscientemente y explicada. Maneja archivos comprimidos. |
| Bueno | 13–17 | Carga funciona, pero con file format inline repetido o `ON_ERROR` por defecto sin justificar. |
| Suficiente | 8–12 | Carga funciona solo para algunas tablas, o requiere pasos manuales. |
| Insuficiente | 0–7 | Datos cargados por la UI de Snowflake o por `INSERT` fila a fila. |

### C4. Idempotencia — 15 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 14–15 | Doble ejecución demostrada en vivo sin duplicación. Estrategia explícita, documentada y adecuada al volumen de datos. Discute las alternativas descartadas. |
| Bueno | 10–13 | Es idempotente y se demuestra, pero la elección de estrategia no está justificada. |
| Suficiente | 6–9 | Idempotencia parcial (algunas tablas sí, otras no). |
| Insuficiente | 0–5 | La segunda ejecución duplica datos o falla. |

### C5. Bitácora y validaciones — 20 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 18–20 | Bitácora poblada automáticamente con filas, timestamp y estado, incluyendo ejecuciones fallidas. ≥3 validaciones automatizadas que **fallan cuando deben fallar** (demostrado). |
| Bueno | 13–17 | Bitácora y validaciones existen y corren, pero solo registran el camino feliz. |
| Suficiente | 8–12 | Solo uno de los dos componentes, o validaciones ejecutadas manualmente. |
| Insuficiente | 0–7 | Sin bitácora ni validaciones. |

### C6. Sustentación oral — 10 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 9–10 | Ejecución en vivo del pipeline completo + demostración de idempotencia, dentro del tiempo. Justifica decisiones de diseño. Responde preguntas sobre escalabilidad y costos. |
| Bueno | 6–8 | Demo funciona; explicación correcta pero superficial. |
| Suficiente | 3–5 | Presenta resultados grabados o capturas en lugar de ejecución en vivo. |
| Insuficiente | 0–2 | No sustenta, o no puede explicar su propio código. |

---

## 7. Recursos

- Sesión 4 — [Ingesta hacia Snowflake](../Cap_2_Modern_Data_Warehouse/sesion_04_ingesta_snowflake/)
- Sesión 5 — [Internal Stages](../Cap_2_Modern_Data_Warehouse/sesion_05_internal_stages/)
- Snowflake — `COPY INTO <table>`: https://docs.snowflake.com/en/sql-reference/sql/copy-into-table
- Snowflake — Internal Stages: https://docs.snowflake.com/en/user-guide/data-load-local-file-system-create-stage
- `uv` — gestión de proyectos: https://docs.astral.sh/uv/guides/projects/
