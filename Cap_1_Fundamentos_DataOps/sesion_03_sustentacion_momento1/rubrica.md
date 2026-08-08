# Rúbrica — Momento 1: CI/CD en Base de Datos

**Sesión:** 3 — viernes 14/08/2026, 18:00–21:00, aula 35-203
**Peso:** 30 % de la nota final · **Total: 100 puntos**
**Modalidad:** equipos de 3–4 personas, conformados en clase, sobre un dominio de negocio
**propio** de cada equipo (no Parch & Posey).

> 📄 **El enunciado completo, con objetivo, alcance, entregables y condiciones de entrega,
> está en [`evaluaciones/momento_1_cicd_bd.md`](../../evaluaciones/momento_1_cicd_bd.md).**
> Este archivo es el resumen operativo de calificación para el día de la sustentación.

---

## Criterios y puntajes

| # | Criterio | Puntos | Qué se busca |
|---|---|---|---|
| C1 | Dominio de negocio y modelo de datos propio | **15** | Dominio distinto al de la clase, documentado, con diagrama ER coherente con lo implementado. |
| C2 | Migraciones Flyway | **25** | Baseline + ≥3 evolutivas + ≥1 repetible sobre el modelo propio. Reconstrucción desde cero sin errores. |
| C3 | Workflow de CI/CD | **25** | Se dispara hacia `main`, falla ruidosamente cuando debe, versiones fijadas. |
| C4 | Gestión de secretos | **10** | Cero credenciales en el repositorio (también en el historial). GitHub Secrets bien usados. |
| C5 | Manejo de fallos y evidencia | **10** | Una falla real de diseño documentada, diagnosticada y corregida vía roll forward. |
| C6 | Documentación del repositorio | **5** | Un tercero reproduce el setup sin preguntar nada; enlaza el documento de dominio. |
| C7 | Sustentación oral | **10** | Intro del dominio + demo en vivo en 10 min; participación de todo el equipo. |
| | **Total** | **100** | |

Los descriptores por nivel (Excelente / Bueno / Suficiente / Insuficiente) de cada
criterio están detallados en la
[sección 6 del enunciado](../../evaluaciones/momento_1_cicd_bd.md#6-rúbrica-de-evaluación).

---

## Checklist rápido de verificación

Antes de calificar, confirmar sobre el repositorio del equipo:

- [ ] El modelo de datos **no es** Parch & Posey ni el de otro equipo del curso.
- [ ] Existe `docs/dominio_de_negocio.md` (o equivalente) con la descripción del ámbito y
      el diagrama ER, coherente con las tablas reales.
- [ ] `flyway migrate` reconstruye la base desde cero sin intervención manual.
- [ ] Existe migración baseline, ≥3 versionadas (`V__`) y ≥1 repetible (`R__`).
- [ ] Hay al menos un run **exitoso** en GitHub Actions.
- [ ] Hay al menos un run **fallido** por un error de diseño real, con su corrección vía
      roll forward documentada (no basta un typo de sintaxis).
- [ ] `git log -p` no revela credenciales en ningún commit.
- [ ] El `README.md` lista los secretos requeridos, los comandos exactos, y enlaza el
      documento de dominio.
- [ ] **Todos** los integrantes del equipo tienen commits y todos sustentan.

---

## Logística de la sesión

| Bloque | Duración | Actividad |
|---|---|---|
| Apertura | 15 min | Encuadre de la evaluación y orden de sustentaciones |
| Sustentaciones | ~2 h 15 min | 15 min por equipo (10 exposición + 5 preguntas) |
| Cierre | 30 min | Retroalimentación grupal y puente hacia el Capítulo 2 |

**Requisito técnico:** los equipos deben verificar conectividad y credenciales **antes**
de su turno. Problemas de setup no descuentan tiempo de sustentación de los demás.
