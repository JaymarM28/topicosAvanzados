# Rúbrica — Momento 2: Cloud Data Warehouse e Ingesta

**Sesión:** 6 — sábado 22/08/2026, 08:00–11:00, aula 33-302
**Peso:** 30 % de la nota final · **Total: 100 puntos**

> 📄 **El enunciado completo, con objetivo, alcance, entregables y condiciones de entrega,
> está en [`evaluaciones/momento_2_cloud_dw.md`](../../evaluaciones/momento_2_cloud_dw.md).**
> Este archivo es el resumen operativo de calificación para el día de la sustentación.

---

## Criterios y puntajes

| # | Criterio | Puntos | Qué se busca |
|---|---|---|---|
| C1 | Arquitectura Snowflake como código | **15** | Setup reproducible desde scripts, esquemas por capa, rol de servicio con permisos mínimos. |
| C2 | Extracción en Python con `uv` | **20** | `pyproject.toml` + `uv.lock` versionados; `uv sync && uv run` funciona en máquina limpia; credenciales por entorno. |
| C3 | Carga vía Internal Stages | **20** | Stage por código, `PUT` + `COPY INTO` con `FILE FORMAT` explícito y `ON_ERROR` justificado. |
| C4 | Idempotencia | **15** | Doble ejecución sin duplicación, demostrada en vivo, con estrategia justificada. |
| C5 | Bitácora y validaciones | **20** | Bitácora poblada automáticamente + ≥3 validaciones que fallan cuando deben fallar. |
| C6 | Sustentación oral | **10** | Ejecución en vivo del pipeline completo en 10 min, decisiones justificadas. |
| | **Total** | **100** | |

Los descriptores por nivel (Excelente / Bueno / Suficiente / Insuficiente) de cada
criterio están detallados en la
[sección 6 del enunciado](../../evaluaciones/momento_2_cloud_dw.md#6-rúbrica-de-evaluación).

---

## Checklist rápido de verificación

Antes de calificar, confirmar sobre el repositorio del equipo:

- [ ] Los objetos de Snowflake se crean desde scripts versionados, no desde la UI.
- [ ] El proyecto Python tiene `pyproject.toml` **y** `uv.lock` en el repositorio.
- [ ] No hay `requirements.txt` escrito a mano ni instrucciones basadas en `pip install`.
- [ ] El `COPY INTO` usa un `FILE FORMAT` nombrado, no inline repetido.
- [ ] **Doble ejecución en vivo** → los conteos no cambian.
- [ ] La bitácora registra también las ejecuciones fallidas, no solo el camino feliz.
- [ ] Al menos una validación se hace fallar deliberadamente y falla.
- [ ] `.env.example` existe y no contiene valores reales.

---

## Logística de la sesión

| Bloque | Duración | Actividad |
|---|---|---|
| Apertura | 15 min | Encuadre y orden de sustentaciones |
| Sustentaciones | ~2 h 15 min | 15 min por equipo (10 exposición + 5 preguntas) |
| Cierre | 30 min | Retroalimentación grupal y puente hacia el Capítulo 3 |

**Requisito técnico:** verificar **vigencia del trial de Snowflake** con anticipación. Un
trial vencido el día de la sustentación no es causal de reprogramación — coordinar con el
docente **antes** si hay riesgo.
