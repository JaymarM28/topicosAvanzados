# RutaSegura — Cobertura Vehicular

Proyecto propio del equipo 5 para el **Momento 1** del módulo de DataOps (SI6010-5979):
tratar el esquema de una base de datos transaccional como código versionado, sobre un
dominio de negocio propio.

> **RutaSegura** es una aseguradora vehicular ficticia. Este repositorio **no** reutiliza el
> dataset de Parch & Posey usado en clase — es un modelo transaccional propio, construido
> desde cero, siguiendo el mismo patrón de trabajo enseñado en el curso.

---

## TL;DR

1. **Dominio propio:** pólizas de seguro vehicular, sus coberturas, facturación y auditoría
   de cambios — 7 tablas, sin relación con Parch & Posey. Ver
   [docs/dominio_de_negocio.md](docs/dominio_de_negocio.md).
2. **Estado base:** [`momento1/inyeccion_semilla_equipo_5.py`](momento1/inyeccion_semilla_equipo_5.py)
   crea el schema y carga los datos semilla de [`data/`](data/) en la branch `dev` de Neon.
3. **Evolución versionada:** 4 migraciones `V__` (tabla nueva, columna, índice, y un fix por
   roll forward) + 2 `R__` (función y procedure) en
   [`momento1/sql_migrations/`](momento1/sql_migrations/).
4. **CI/CD:** [`.github/workflows/flyway-migrate.yml`](.github/workflows/flyway-migrate.yml)
   aplica las migraciones a `main` automáticamente en cada push.

---

## 1. El negocio

RutaSegura vende **pólizas** de seguro vehicular. Cada póliza puede incluir varias
**coberturas** (responsabilidad civil, colisión, asistencia en carretera...), aplicadas a
nivel de la póliza completa o a un **vehículo** específico asegurado bajo esa póliza. La
**facturación** registra los cobros periódicos de cada póliza, y cada cambio relevante sobre
una póliza queda auditado.

Detalle completo del dominio y el diagrama entidad-relación en
[docs/dominio_de_negocio.md](docs/dominio_de_negocio.md).

---

## 2. Estructura del repositorio

```
topicosAvanzados/
├── README.md                          ← este archivo
├── docs/
│   └── dominio_de_negocio.md          ← dominio de negocio + ERD (Mermaid)
├── data/                              ← datos semilla (JSON), uno por tabla
├── momento1/
│   ├── inyeccion_semilla_equipo_5.py  ← crea el schema y carga el estado base en `dev`
│   ├── pyproject.toml / uv.lock       ← entorno Python (uv)
│   ├── ex.flyway.conf                 ← plantilla de configuración de Flyway
│   └── sql_migrations/                ← migraciones Flyway sobre el modelo propio
└── .github/workflows/
    └── flyway-migrate.yml             ← CI/CD: aplica migraciones a `main`
```

---

## 3. Cómo correr esto

### 3.1 Estado base (una sola vez, contra `dev`)

```bash
cd momento1
uv sync
```

Crea `momento1/.env` (no se versiona — ver `.gitignore`) con los connection strings de tu
proyecto de Neon:

```bash
NEON_DEV_DATABASE_URL=postgresql://usuario:password@ep-xxxx-dev.us-east-2.aws.neon.tech/neondb?sslmode=require
NEON_MAIN_DATABASE_URL=postgresql://usuario:password@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require
```

```bash
uv run inyeccion_semilla_equipo_5.py
```

### 3.2 Migraciones con Flyway (local, contra `dev`)

```bash
cd momento1
cp ex.flyway.conf flyway.conf   # y edítalo con tu URL de dev

flyway -baselineVersion=1 \
       -baselineDescription="Cobertura vehicular estado base" \
       baseline

flyway info       # qué está pendiente
flyway migrate    # aplica todo lo pendiente
```

### 3.3 Automatización hacia `main`

En GitHub → *Settings* → *Secrets and variables* → *Actions*, crea el secreto
`NEON_MAIN_DATABASE_URL` con el connection string de tu branch `main`. Cada push a `main`
que toque `momento1/sql_migrations/` dispara
[`flyway-migrate.yml`](.github/workflows/flyway-migrate.yml) y aplica los cambios sin que
nadie se conecte a la base a mano.

---

## 4. Stack

| Capa | Tecnología |
|---|---|
| Base de datos | Neon.tech (PostgreSQL serverless) — branches `dev` y `main` |
| Migraciones | Flyway |
| CI/CD | GitHub Actions |
| Carga inicial | Python (`uv` + `psycopg2`) |

---

## 5. Nota de origen

El ERD de referencia usado como punto de partida fue
`Vehicle-coverage-ERD-Example-Graphic-2.png`. Los datos son sintéticos, generados con fines
didácticos. Este es el entregable del **Momento 1** — ver el
[enunciado del curso](https://github.com/davilla41/data_ops_course_101/blob/main/evaluaciones/momento_1_cicd_bd.md)
para el detalle de la rúbrica.
