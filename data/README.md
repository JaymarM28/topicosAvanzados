# Datos semilla — Parch & Posey

Esta carpeta aloja los **datos semilla públicos** del caso de estudio del módulo:
**Parch & Posey**, un distribuidor ficticio de papel usado ampliamente como dataset
didáctico para SQL analítico.

## Modelo de datos

Cinco tablas relacionadas — diagrama visual en [`er_model.png`](../er_model.png):

| Tabla | Descripción | Llave | Relación |
|---|---|---|---|
| `regions` | Regiones comerciales | `id` | — |
| `sales_reps` | Representantes de ventas | `id` | `region_id` → `regions.id` |
| `accounts` | Cuentas de clientes | `id` | `sales_rep_id` → `sales_reps.id` |
| `orders` | Órdenes de compra, con `occurred_at` y cantidades/montos por línea de producto (standard, gloss, poster) | `id` | `account_id` → `accounts.id` |
| `web_events` | Eventos de visita web con `occurred_at` y canal (organic, adwords, direct, facebook, twitter, banner) | `id` | `account_id` → `accounts.id` |

Volumen: 4 regiones, 50 representantes, 351 cuentas, 6 912 órdenes y 9 073 eventos web. Es
un dataset pequeño **a propósito** — el foco del módulo es la ingeniería del pipeline, no
el procesamiento de gran volumen.

> ⚠️ **`er_model.png` está desactualizado.** Nombra la tabla `region` en singular y omite
> `orders.occurred_at` y `orders.gloss_qty`. La fuente de verdad del schema es el DDL de
> [`inyeccion_semilla.py`](../Cap_1_Fundamentos_DataOps/sesion_01_estado_base/codigo/inyeccion_semilla.py).
> Pendiente de corregir antes de publicarlo a los estudiantes — ver §9.7 del
> [plan de testing](../TESTING_PLAN_E2E.md).

## Contenido

```
data/
├── README.md          ← este archivo
├── regions.json          4 registros
├── sales_reps.json      50 registros
├── accounts.json       351 registros
├── orders.json       6 912 registros
├── web_events.json   9 073 registros
└── output/            ← artefactos generados por los scripts (ignorado por git)
```

**Total: 16 390 registros.** Los cinco JSON **se versionan**: son pequeños y constituyen la
fuente de verdad del caso. `output/` **no** se versiona (excluido en
[.gitignore](../.gitignore)); ahí escriben los scripts de extracción de la Sesión 4 antes de
subir a un Internal Stage.

### Forma de los datos

Cada archivo es un array JSON de objetos planos. **Todos los valores vienen como string**,
incluidos números y fechas — es un artefacto del export original desde SQL Server:

```json
{ "id": "1", "account_id": "1001", "occurred_at": "2015-10-06T17:31:14.0000000",
  "standard_qty": "123", "total_amt_usd": "973.43" }
```

Dos consecuencias prácticas, que se trabajan explícitamente en la Sesión 1:

- Hay que **castear** al cargar. Sin conversión, el schema termina lleno de `TEXT` y las
  agregaciones de la Sesión 7 dejan de funcionar.
- Los timestamps traen **7 dígitos** de fracción de segundo. PostgreSQL almacena
  microsegundos (6) y `datetime.fromisoformat` rechaza los 7: hay que normalizar en el borde
  de entrada.

### Calidad verificada

Comprobado el 31/07/2026 sobre los cinco archivos:

| Verificación | Resultado |
|---|---|
| Integridad referencial (4 relaciones FK) | ✅ 0 huérfanos |
| Valores nulos o vacíos | ✅ ninguno |
| Unicidad de `id` | ✅ en las 5 tablas |
| Consistencia de claves entre registros | ✅ un solo esquema por archivo |
| Rango temporal | 2013-12-04 → 2017-01-02 |
| Canales en `web_events` | `adwords`, `banner`, `direct`, `facebook`, `organic`, `twitter` |

## Cómo se usa a lo largo del módulo

| Sesión | Uso |
|---|---|
| 1 — Estado base | Carga inicial en la branch `dev` de Neon vía [`inyeccion_semilla.py`](../Cap_1_Fundamentos_DataOps/sesion_01_estado_base/codigo/inyeccion_semilla.py) |
| 2 — CI/CD con Flyway | El schema de estas tablas es el baseline de las migraciones |
| 4 y 5 — Ingesta | Se extraen desde Neon y se cargan a Snowflake vía Internal Stage |
| 7 — dbt | Son las `sources` del proyecto de transformación |

## Origen y licencia

Parch & Posey es un dataset didáctico de dominio público, popularizado por el curso *SQL
for Data Analysis* de Udacity. No contiene datos personales reales — todas las cuentas,
nombres y transacciones son sintéticos.

---

> ✅ **Datos presentes y verificados.** Se cargan con
> [`inyeccion_semilla.py`](../Cap_1_Fundamentos_DataOps/sesion_01_estado_base/codigo/inyeccion_semilla.py)
> — ver [Sesión 1](../Cap_1_Fundamentos_DataOps/sesion_01_estado_base/).
