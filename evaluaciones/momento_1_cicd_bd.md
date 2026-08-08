# Momento 1 — CI/CD en Base de Datos

**Módulo:** Tendencias emergentes en desarrollo de software (SI6010-5979) · Pos ST1707
**Peso sobre la nota final:** **30 %**
**Capítulo:** 1 — Fundamentos de DataOps
**Se sustenta en:** [Sesión 3 — Sustentación Momento 1](../Cap_1_Fundamentos_DataOps/sesion_03_sustentacion_momento1/) · viernes **14/08/2026**, 18:00–21:00, aula 35-203
**Stack:** Neon.tech (PostgreSQL) · Flyway · GitHub + GitHub Actions

---

## 1. Objetivo

Demostrar que el equipo es capaz de **tratar el esquema de una base de datos como
código**: versionarlo, evolucionarlo mediante migraciones reproducibles y desplegarlo de
forma automatizada, sin intervención manual sobre el servidor de base de datos.

Al terminar este momento, el equipo debe poder responder con evidencia:

- ¿Cuál es el estado exacto del esquema en cada entorno, y quién lo cambió?
- ¿Puedo reconstruir la base de datos desde cero con un solo comando?
- ¿Qué pasa cuando alguien intenta desplegar una migración que rompe algo?

---

## 2. Contexto del caso

En las Sesiones 1 y 2 trabajamos en clase sobre un caso compartido —**Parch & Posey**—
para que todos partiéramos del mismo punto y pudiéramos comparar resultados en vivo.
**Este momento evaluativo no se hace sobre Parch & Posey.**

El encargo real de un Data Engineer casi nunca es replicar exactamente el pipeline de un
tutorial: es aplicar el mismo patrón —control de versiones del esquema, migraciones
reproducibles, despliegue automatizado— sobre un dominio de negocio distinto cada vez. Por
eso el Momento 1 pide que cada equipo elija su **propio** ámbito de negocio, diseñe su
**propio** modelo transaccional, y repita sobre ese proyecto exactamente el flujo de
trabajo de las Sesiones 1 y 2: estado base en Neon, control de versiones con Flyway,
despliegue con GitHub Actions.

El objetivo no cambia respecto a lo dicho en la Sección 1: **eliminar el trabajo manual de
administrar el esquema.** Lo que cambia es que ahora el esquema, los datos y las
decisiones de diseño son enteramente del equipo.

---

## 3. Alcance

### Incluido en el alcance

**0. Dominio de negocio y modelo de datos propios** — condición de entrada al resto del
alcance:

- Un ámbito de negocio elegido por el equipo, **distinto** al de Parch & Posey y al de
  cualquier otro proyecto ya usado en el curso (biblioteca, veterinaria, gimnasio, taller
  mecánico, cafetería, torneo deportivo... cualquier dominio con entidades y relaciones
  reales sirve).
- Complejidad sugerida: entre **4 y 10 tablas** relacionadas — suficiente para tener
  foreign keys reales y al menos dos niveles de jerarquía, sin convertirse en un proyecto
  de varias semanas. Parch & Posey (5 tablas) es una referencia razonable de escala.
- Volumen de datos que quepa cómodamente en el **tier gratuito de Neon** (0.5 GB de
  almacenamiento por proyecto): miles de filas, no cientos de miles. Datos sintéticos o
  generados son válidos — no hace falta un dataset real.
- Un documento en el repositorio (`docs/dominio_de_negocio.md` o similar) que describa en
  1–2 párrafos el ámbito de negocio elegido, y el **diagrama entidad-relación** del modelo
  transaccional que lo representa. El diagrama puede ser una imagen o un bloque Mermaid
  `erDiagram` embebido en el markdown — GitHub lo renderiza directamente, sin depender de
  un archivo externo.

**1. Repositorio propio** del equipo, creado desde cero — **no** un fork del repositorio
del curso. Debe contener el modelo de datos propio, no el de Parch & Posey.

**2. Dos entornos** en Neon.tech gestionados desde el mismo repositorio:
   - `dev` — branch de desarrollo.
   - `main` — branch principal.

**3. Migraciones Flyway** sobre el modelo propio, que cubran como mínimo:
   - El *baseline* del esquema inicial (equivalente a lo que hizo `inyeccion_semilla.py`
     en la Sesión 1, adaptado al modelo propio).
   - Al menos **tres migraciones evolutivas** (`V__`) que incluyan, entre las tres: una
     tabla nueva, una columna añadida a una tabla existente, y una restricción o índice.
   - Al menos **una migración repetible** (`R__`) — una función, un procedimiento o una
     vista, análoga a `fn_calculate_discount` / `sp_process_order` de la Sesión 2.
   - Evidencia de al menos **un error real de diseño**, desplegado y corregido mediante
     **roll forward** — el mismo patrón demostrado en clase con `utm_source VARCHAR(2)`,
     aplicado a un error propio del modelo del equipo.

**4. Workflow de GitHub Actions** que ejecute las migraciones de forma automática hacia
`main`. Puede adaptarse de la plantilla
[`.github/workflows/flyway-migrate.yml`](../.github/workflows/flyway-migrate.yml) del
curso — ajustando la ruta de las migraciones y el nombre del secreto a la estructura del
repositorio propio.

**5. Manejo de secretos** vía GitHub Secrets — **cero credenciales en el repositorio**.

### Fuera del alcance

- Usar el esquema de Parch & Posey, o el de otro equipo, como base del proyecto propio.
- Snowflake, dbt y cualquier capa analítica (esos son los Momentos 2 y 3).
- Estrategias de rollback automatizado (se discuten conceptualmente, no se implementan).
- Migraciones de datos masivos (>10 000 filas) o tuning de rendimiento.

---

## 4. Entregables

| # | Entregable | Formato | Dónde |
|---|---|---|---|
| E1 | Repositorio propio del equipo (no fork), con commits de todos los integrantes | URL de GitHub | Enviado por el canal del curso |
| E2 | Documento del dominio de negocio + diagrama ER del modelo propio | Markdown (imagen o Mermaid `erDiagram`) | `docs/dominio_de_negocio.md` del repositorio |
| E3 | Migraciones Flyway sobre el modelo propio | Archivos `.sql` versionados | En el repositorio |
| E4 | Workflow `.github/workflows/*.yml` funcional, adaptado de la plantilla del curso | YAML | En el repositorio |
| E5 | Evidencia de al menos **una ejecución exitosa** y **una ejecución fallida corregida** (roll forward) | Capturas o enlaces a los runs de GitHub Actions | `docs/evidencias/` del repositorio |
| E6 | `README.md` del repositorio: cómo se ejecuta localmente, cómo se agrega una migración, qué secretos requiere, enlace al documento de dominio | Markdown | Raíz del repositorio |
| E7 | Sustentación oral en equipo | 10 min de exposición + 5 min de preguntas | Sesión 3 — 14/08/2026 |

### Sobre la sustentación (E7)

Cada **equipo** (3–4 integrantes, conformados en clase) dispone de **10 minutos**. Se
espera:

1. **Introducción breve del dominio de negocio** (1–2 min): qué representa el modelo, por
   qué lo eligieron, y el diagrama ER en pantalla.
2. **Demo en vivo** (no diapositivas de código, el resto del tiempo): crear una migración
   nueva, hacer commit, hacer push, mostrar el workflow ejecutándose y el cambio reflejado
   en Neon.
3. Explicación de **una decisión técnica** que hayan tomado y su alternativa descartada.
4. **Todos los integrantes deben participar** en la exposición o en las respuestas — el
   docente puede dirigir preguntas a cualquier miembro del equipo, no solo a quien esté
   hablando.

> ⚠️ **Un pipeline que solo funciona en la máquina de un integrante no cumple el objetivo
> del momento.** La ejecución debe ocurrir en GitHub Actions.

---

## 5. Condiciones de entrega

- **Fecha límite de código:** viernes **14/08/2026, 17:00** (una hora antes de la sesión).
  Se evalúa el estado del branch `main` en ese instante.
- **Modalidad:** equipos de **3 a 4 personas**, conformados en clase. Todos los
  integrantes deben tener commits en el historial y todos sustentan.
- **Entregas tardías:** se califican sobre el 70 % hasta 48 horas después; posteriormente
  no se reciben.

---

## 6. Rúbrica de evaluación

**Total: 100 puntos** → equivalen al 30 % de la nota final.

### C1. Dominio de negocio y modelo de datos propio — 15 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 14–15 | Dominio de negocio propio, no trivial ni copiado de Parch & Posey ni de otro equipo. Documento claro que describe el dominio y su lógica. Diagrama ER completo y coherente con las migraciones realmente aplicadas. Complejidad y volumen razonables, compatibles con el tier gratuito de Neon. |
| Bueno | 10–13 | Dominio propio y ER presentes, pero la documentación del dominio es escueta o el ER no refleja exactamente lo implementado en la base de datos. |
| Suficiente | 6–9 | El dominio es genérico o muy similar a un ejemplo visto en clase; ER incompleto o ausente, aunque el schema en sí sea propio. |
| Insuficiente | 0–5 | Reutiliza el modelo de Parch & Posey (u otro dataset del curso), o no hay documento de dominio ni diagrama ER. |

### C2. Migraciones Flyway — 25 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 23–25 | Convención de nombres correcta y consistente. Baseline + ≥3 migraciones evolutivas + ≥1 repetible, sobre el modelo propio. Cada migración es atómica y tiene un propósito único y claro. `flyway migrate` desde cero reconstruye la BD sin errores. |
| Bueno | 18–22 | Todas las migraciones requeridas existen y corren, pero hay migraciones que mezclan cambios no relacionados o nombres poco descriptivos. |
| Suficiente | 12–17 | Faltan una o dos migraciones requeridas, o la reconstrucción desde cero requiere pasos manuales no documentados. |
| Insuficiente | 0–11 | Migraciones que no corren, esquema aplicado a mano, o ausencia de baseline. |

### C3. Workflow de CI/CD — 25 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 23–25 | Workflow se dispara correctamente hacia `main`. Usa una imagen o CLI de Flyway fijados a una versión. Falla ruidosamente cuando debe fallar. Tiempos de ejecución razonables. |
| Bueno | 18–22 | El workflow funciona en el camino feliz pero no maneja bien los fallos, o depende de pasos manuales previos no documentados. |
| Suficiente | 12–17 | Existe un workflow que ejecuta Flyway, pero se dispara solo manualmente (`workflow_dispatch`) o ha fallado sin corregirse. |
| Insuficiente | 0–11 | No hay workflow, o nunca ha corrido exitosamente. |

### C4. Gestión de secretos y seguridad — 10 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 9–10 | Cero credenciales en el repositorio (verificado también en el historial de commits). GitHub Secrets correctamente configurados. `.gitignore` cubre `flyway.conf`, `.env` y similares. |
| Bueno | 7–8 | Secretos gestionados correctamente en el estado actual, pero hay credenciales en commits antiguos del historial. |
| Suficiente | 4–6 | Uso parcial de secretos; algún parámetro sensible (host, usuario) hardcodeado. |
| Insuficiente | 0–3 | Contraseñas o connection strings completos en el repositorio. |

### C5. Manejo de fallos y evidencia — 10 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 9–10 | Documenta una falla real de diseño (no un typo de sintaxis), su diagnóstico y su corrección vía roll forward. Evidencia clara de ambos runs en GitHub Actions. Explica qué hizo el pipeline y por qué. |
| Bueno | 6–8 | Muestra la falla y la corrección, pero sin análisis de la causa, o la falla es puramente sintáctica. |
| Suficiente | 3–5 | Solo hay evidencia de ejecuciones exitosas. |
| Insuficiente | 0–2 | Sin evidencia. |

### C6. Documentación del repositorio — 5 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 5 | `README.md` permite que un tercero reproduzca el setup completo sin preguntar nada. Lista secretos requeridos, comandos exactos, y enlaza el documento de dominio de negocio. |
| Bueno | 3–4 | Documentación presente pero con vacíos que exigen inferencia. |
| Suficiente | 1–2 | README mínimo o genérico. |
| Insuficiente | 0 | Sin documentación. |

### C7. Sustentación oral — 10 puntos

| Nivel | Puntos | Descripción |
|---|---|---|
| Excelente | 9–10 | Introducción del dominio clara y breve. Demo en vivo fluida dentro del tiempo. Justifica decisiones técnicas con criterio propio. Todos los integrantes participan y responden con solvencia. |
| Bueno | 6–8 | Demo funciona; explicación correcta pero descriptiva más que argumentativa. Participación desigual entre integrantes. |
| Suficiente | 3–5 | Presenta capturas en lugar de demo en vivo, excede significativamente el tiempo, o solo un integrante sostiene toda la exposición. |
| Insuficiente | 0–2 | No sustenta, o el equipo no puede explicar el código de su propio repositorio. |

---

## 7. Recursos

- Sesión 1 — [Estado base](../Cap_1_Fundamentos_DataOps/sesion_01_estado_base/) — el
  patrón a replicar sobre el modelo propio.
- Sesión 2 — [CI/CD con Flyway](../Cap_1_Fundamentos_DataOps/sesion_02_cicd_flyway/) — el
  patrón de migraciones, roll forward y automatización a replicar.
- Plantilla de workflow — [`.github/workflows/flyway-migrate.yml`](../.github/workflows/flyway-migrate.yml)
  (adaptar la ruta de migraciones y el nombre del secreto al repositorio propio).
- Documentación oficial de Flyway — https://documentation.red-gate.com/flyway
- Neon branching — https://neon.tech/docs/introduction/branching
- Neon — límites del tier gratuito — https://neon.tech/docs/introduction/plans
- Diagramas ER sin salir del repositorio — sintaxis Mermaid `erDiagram`:
  https://mermaid.js.org/syntax/entityRelationshipDiagram.html (GitHub la renderiza nativa
  en cualquier `.md`)
- Alternativa visual — https://dbdiagram.io (exporta PNG para incrustar en el documento de
  dominio)
