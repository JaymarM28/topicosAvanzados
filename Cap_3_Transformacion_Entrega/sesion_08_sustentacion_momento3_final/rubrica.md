# Rúbrica — Momento 3: End-to-End DataOps (Final)

**Sesión:** 8 — sábado 29/08/2026, 08:00–11:00, aula 34-302
**Peso:** 40 % de la nota final · **Total: 100 puntos**

> 📄 **El enunciado completo, con objetivo, alcance, entregables y condiciones de entrega,
> está en [`evaluaciones/momento_3_e2e_dataops.md`](../../evaluaciones/momento_3_e2e_dataops.md).**
> Este archivo es el resumen operativo de calificación para el día de la sustentación.

---

## Criterios y puntajes

| # | Criterio | Puntos | Qué se busca |
|---|---|---|---|
| C1 | Arquitectura del proyecto dbt | **15** | Capas staging/intermediate/marts sin fugas de lógica; `ref()` y `source()` consistentes. |
| C2 | Modelo incremental | **20** | `is_incremental()` + `unique_key` correctos; segunda corrida procesa solo lo nuevo (demostrado). |
| C3 | Pruebas de calidad de datos | **20** | Tests genéricos sobre llaves y relaciones + ≥1 test singular de regla de negocio; falla provocada y corregida. |
| C4 | Documentación y lineage | **10** | Marts y columnas descritos en lenguaje de negocio; lineage graph completo. |
| C5 | Aplicación Streamlit | **15** | Desplegada y funcional, ≥3 visualizaciones pertinentes, filtro interactivo, consulta solo marts. |
| C6 | Automatización e integración E2E | **10** | Job programado con historial; el cambio E2E fluye sin pasos manuales. |
| C7 | Sustentación final | **10** | Demo del cambio E2E en vivo en 15 min; conecta técnica y negocio; retrospectiva con criterio. |
| | **Total** | **100** | |

Los descriptores por nivel (Excelente / Bueno / Suficiente / Insuficiente) de cada
criterio están detallados en la
[sección 6 del enunciado](../../evaluaciones/momento_3_e2e_dataops.md#6-rúbrica-de-evaluación).

---

## Checklist rápido de verificación

Antes de calificar, confirmar sobre el repositorio del equipo (el mismo desde el Momento 1):

- [ ] `dbt build` corre limpio desde cero.
- [ ] Los marts usan `ref()`; ningún mart consulta `source()` directamente.
- [ ] Logs comparativos de 1.ª vs 2.ª corrida del modelo incremental muestran diferencia
      real en filas procesadas.
- [ ] Existe al menos un test **singular** que valida una regla de **negocio**, no una
      restricción estructural.
- [ ] Hay evidencia de un test que falló, su diagnóstico y su corrección.
- [ ] El lineage graph está completo, sin modelos huérfanos.
- [ ] La app de Streamlit está **viva** y consulta marts, no `RAW`.
- [ ] El job automatizado tiene ≥3 ejecuciones en su historial.
- [ ] `profiles.yml.example` y `.env.example` existen y no tienen credenciales reales.
- [ ] Existe `docs/arquitectura_e2e.md` con diagrama del flujo completo.

---

## Criterio integrador

Además de la suma por criterios, se valora que el pipeline **funcione como un sistema**:
que un cambio en el origen se propague de forma trazable hasta el consumo, que los fallos
sean visibles y diagnosticables, y que un tercero pueda operarlo con la documentación
entregada.

Un conjunto de piezas técnicamente correctas pero desconectadas entre sí **no cumple el
objetivo del módulo** y no puede calificarse en nivel Excelente en C6 ni C7.

---

## Logística de la sesión

| Bloque | Duración | Actividad |
|---|---|---|
| Apertura | 10 min | Encuadre de la sustentación final |
| Sustentaciones | ~2 h 20 min | 25 min por equipo (15 exposición + 10 preguntas) |
| Cierre del módulo | 30 min | Síntesis, discusión de temas fuera de alcance (orquestadores, streaming, data contracts) y retroalimentación final |

> ⏱️ **Si el número de equipos no cabe en el bloque de 2 h 20 min**, ajustar a 20 min por
> equipo (12 + 8) y comunicarlo con al menos una semana de anticipación.

**Requisito técnico:** verificar vigencia de los trials de **Snowflake y dbt Cloud** con
anticipación. Por ser la sesión final del módulo **no hay reprogramación**.
