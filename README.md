# Tendencias emergentes en desarrollo de software — DataOps

**Código del módulo:** SI6010-5979 · **Programa:** Pos ST1707
**Intensidad:** 24 horas (8 sesiones de 3 horas) · **Modalidad:** presencial
**Periodo:** agosto de 2026

---

## 1. De qué se trata este módulo

DataOps es la aplicación disciplinada de las prácticas de DevOps al ciclo de vida del dato:
control de versiones sobre el esquema, integración y despliegue continuos, pruebas
automatizadas, observabilidad y entrega de valor al usuario final. En este módulo no
hablamos de DataOps en abstracto: lo **construimos**.

A lo largo de las 8 sesiones vamos a levantar, pieza por pieza, un **pipeline End-to-End**
que arranca en una base de datos transaccional versionada y termina en un dashboard
consumible por un usuario de negocio. Cada capítulo agrega una capa al mismo artefacto —
no son ejercicios desconectados.

### Objetivo general

> Diseñar, implementar y operar un pipeline de datos End-to-End que aplique prácticas de
> DataOps —versionamiento de esquema, CI/CD, ingesta gobernada a un Cloud Data Warehouse,
> transformación modular y entrega analítica— sobre un caso de negocio realista.

### Objetivos específicos

1. Versionar la evolución del esquema de una base de datos relacional con migraciones
   idempotentes y reproducibles (Flyway).
2. Automatizar el despliegue de esos cambios mediante un workflow de CI/CD (GitHub Actions).
3. Implementar la ingesta de datos hacia un Cloud Data Warehouse usando Internal Stages y
   extracción programática en Python.
4. Modelar transformaciones analíticas con dbt, aplicando materializaciones incrementales
   y pruebas de calidad de datos.
5. Entregar el resultado en una capa de consumo (Streamlit in Snowflake) y sustentar las
   decisiones técnicas tomadas.

---

## 2. El caso: Parch & Posey (y el proyecto propio de cada equipo)

En clase trabajamos sobre el dataset público **Parch & Posey**, un distribuidor ficticio
de papel con tres líneas de producto. Es un modelo relacional pequeño (5 tablas:
`accounts`, `orders`, `web_events`, `sales_reps`, `regions`) pero suficientemente rico para
enseñar cada técnica del módulo en vivo, con un caso compartido que permite comparar
resultados entre estudiantes. Los datos semilla viven en [data/](data/).

**Parch & Posey es el vehículo pedagógico de las sesiones — no el entregable evaluativo.**
A partir del Momento 1, cada equipo elige su **propio** ámbito de negocio y diseña su
**propio** modelo transaccional, y repite sobre ese proyecto el mismo patrón enseñado en
clase. Ese proyecto propio **continúa durante todo el módulo**: es la misma base que se
lleva a Snowflake en el Momento 2 y se transforma con dbt en el Momento 3. Ver el
[enunciado del Momento 1](evaluaciones/momento_1_cicd_bd.md) para el detalle.

---

## 3. Tech stack

| Capa | Tecnología | Rol en el pipeline |
|---|---|---|
| Base de datos OLTP | **Neon.tech** (PostgreSQL serverless) | Sistema fuente; soporta branching de BD |
| Control de versiones | **GitHub** | Fuente única de verdad del código y del esquema |
| Migraciones de esquema | **Flyway** (CLI) | Evolución versionada y auditable de la BD |
| CI/CD | **GitHub Actions** | Aplica migraciones automáticamente por entorno |
| Extracción | **Python** (`uv` + librerías nativas) | Extrae de Neon y produce archivos para carga |
| Cloud DW | **Snowflake** | Almacenamiento analítico; Internal Stages para landing |
| Transformación | **dbt Cloud** | Modelado en capas, materializaciones incrementales, tests |
| Entrega | **Streamlit in Snowflake** | Dashboard / kiosk analítico sobre los marts |

### Convención de entornos Python

Todo el Python de este repositorio se gestiona con **[`uv`](https://docs.astral.sh/uv/)**
(Astral). No usamos `pip install` global ni `venv` creados a mano.

Cada script o proyecto Python independiente tiene su propio `pyproject.toml`:

```bash
# crear un proyecto nuevo dentro de la carpeta de la sesión
uv init

# agregar dependencias
uv add snowflake-connector-python
uv add --dev ruff

# reconstruir el entorno a partir del lockfile
uv sync

# ejecutar un script dentro del entorno del proyecto
uv run extraer_parch_posey.py
```

Si algún workflow externo exige un `requirements.txt`, se **genera** —nunca se escribe a
mano:

```bash
uv export --format requirements-txt --no-hashes > requirements.txt
```

Instalación de `uv` (si no lo tienes):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 4. Cronograma — agosto de 2026

| # | Fecha | Día | Horario | Aula | Sesión | Capítulo |
|---|---|---|---|---|---|---|
| 1 | 01/08/2026 | Sábado | 08:00–11:00 | 34-302 | [Estado base: el problema que DataOps resuelve](Cap_1_Fundamentos_DataOps/sesion_01_estado_base/) | Cap. 1 |
| 2 | 08/08/2026 | Sábado | 08:00–11:00 | 33-302 | [CI/CD en base de datos con Flyway](Cap_1_Fundamentos_DataOps/sesion_02_cicd_flyway/) | Cap. 1 |
| 3 | 14/08/2026 | Viernes | 18:00–21:00 | 35-203 | **Sustentación Momento 1** *(evaluativa)* | Cap. 1 |
| 4 | 15/08/2026 | Sábado | 08:00–11:00 | 34-302 | [Ingesta hacia Snowflake](Cap_2_Modern_Data_Warehouse/sesion_04_ingesta_snowflake/) | Cap. 2 |
| 5 | 21/08/2026 | Viernes | 18:00–21:00 | 35-203 | [Internal Stages y carga gobernada](Cap_2_Modern_Data_Warehouse/sesion_05_internal_stages/) | Cap. 2 |
| 6 | 22/08/2026 | Sábado | 08:00–11:00 | 33-302 | **Sustentación Momento 2** *(evaluativa)* | Cap. 2 |
| 7 | 28/08/2026 | Viernes | 18:00–21:00 | 35-203 | [dbt e incremental models](Cap_3_Transformacion_Entrega/sesion_07_dbt_incremental/) | Cap. 3 |
| 8 | 29/08/2026 | Sábado | 08:00–11:00 | 34-302 | **Sustentación Momento 3 — Final** *(evaluativa)* | Cap. 3 |

> **Nota sobre aulas:** los sábados alternan entre las aulas **34-302** y **33-302**; la
> asignación de la tabla es **provisional** y asume que la serie inicia en 34-302 el
> 01/08. Pendiente de confirmación con la coordinación del programa — ver
> [TESTING_PLAN_E2E.md §9.3](TESTING_PLAN_E2E.md). Los viernes son siempre **35-203**.

---

## 5. Estructura del repositorio

```
data_ops_course_101/
├── README.md                          ← este archivo
├── WINDOWS_USERS.md                   ← configuración de Git Bash (obligatorio en Windows)
├── TESTING_PLAN_E2E.md                ← plan de verificación E2E (human-in-the-loop)
├── er_model.png                       ← diagrama entidad-relación de Parch & Posey
├── .marp/tema_dataops.css             ← tema editorial de las presentaciones
├── .github/workflows/
│   └── flyway-migrate.yml             ← plantilla de CI/CD para migraciones
├── data/                              ← datos semilla de Parch & Posey
├── evaluaciones/                      ← enunciados y rúbricas de los 3 momentos
│   ├── momento_1_cicd_bd.md
│   ├── momento_2_cloud_dw.md
│   └── momento_3_e2e_dataops.md
├── Cap_1_Fundamentos_DataOps/
│   ├── sesion_01_estado_base/
│   ├── sesion_02_cicd_flyway/
│   └── sesion_03_sustentacion_momento1/
├── Cap_2_Modern_Data_Warehouse/
│   ├── sesion_04_ingesta_snowflake/
│   ├── sesion_05_internal_stages/
│   └── sesion_06_sustentacion_momento2/
└── Cap_3_Transformacion_Entrega/
    ├── sesion_07_dbt_incremental/
    └── sesion_08_sustentacion_momento3_final/
```

Cada carpeta de sesión contiene:

- `README.md` — guía de la sesión: objetivo, agenda, prerrequisitos, pasos.
- `presentacion/` — material de exposición (`presentacion.md` en Marp y apoyos visuales).
- `codigo/` o `proyecto/` — artefactos ejecutables de la sesión *(solo sesiones de contenido)*.
- `rubrica.md` — criterios de calificación *(solo sesiones evaluativas)*.

---

## 6. Evaluación

La nota final se compone de tres momentos evaluativos, cada uno sustentado en una sesión
específica. **Los tres son acumulativos sobre el mismo pipeline**: el Momento 2 parte del
entregable del Momento 1, y el Momento 3 integra todo — y los tres se hacen sobre el mismo
**proyecto propio de cada equipo** (dominio de negocio y modelo de datos elegidos en el
Momento 1), no sobre Parch & Posey.

| Momento | Tema | Peso | Se sustenta en | Enunciado |
|---|---|---|---|---|
| **1** | CI/CD en Base de Datos (Neon + Flyway + GitHub Actions) | **30 %** | Sesión 3 — viernes 14/08/2026 | [momento_1_cicd_bd.md](evaluaciones/momento_1_cicd_bd.md) |
| **2** | Cloud DW e Ingesta (Snowflake + Internal Stages) | **30 %** | Sesión 6 — sábado 22/08/2026 | [momento_2_cloud_dw.md](evaluaciones/momento_2_cloud_dw.md) |
| **3** | End-to-End DataOps (dbt + Streamlit) | **40 %** | Sesión 8 — sábado 29/08/2026 | [momento_3_e2e_dataops.md](evaluaciones/momento_3_e2e_dataops.md) |
| | | **100 %** | | |

---

## 7. Prerrequisitos de los estudiantes

**Conocimiento previo**

- SQL intermedio (joins, agregaciones, CTEs).
- Python básico (scripts, manejo de archivos, librerías estándar).
- Git básico (clone, branch, commit, push, pull request).

**Cuentas a crear antes de la Sesión 1** (todas tienen tier gratuito suficiente):

| Servicio | URL | Para qué |
|---|---|---|
| GitHub | https://github.com | Repositorio y CI/CD |
| Neon.tech | https://neon.tech | Base de datos PostgreSQL fuente |
| Snowflake Trial | https://signup.snowflake.com | Cloud Data Warehouse (30 días) |
| dbt Cloud | https://www.getdbt.com/signup | Transformación (Developer plan) |

**Herramientas locales**

```bash
# uv — gestor de proyectos Python
curl -LsSf https://astral.sh/uv/install.sh | sh

# Flyway CLI (macOS con Homebrew)
brew install flyway

# GitHub CLI
brew install gh && gh auth login
```

> 🪟 **¿Trabajas en Windows?** Lee **[WINDOWS_USERS.md](WINDOWS_USERS.md) antes de la
> primera sesión.** Es obligatorio usar **Git Bash** como terminal: todos los comandos del
> curso están escritos para shells POSIX y fallan en PowerShell o CMD.

Ver el detalle de verificación en [TESTING_PLAN_E2E.md](TESTING_PLAN_E2E.md).

---

## 8. Cómo obtener el repositorio

```bash
git clone https://github.com/davilla41/data_ops_course_101.git
cd data_ops_course_101
```

**Repositorio:** https://github.com/davilla41/data_ops_course_101 (público)

---

## 9. Estado del repositorio

| Sesión | Estado |
|---|---|
| 1 — Estado base | ✅ Completa y verificada de extremo a extremo contra Neon |
| 2 a 8 | 🚧 Placeholder — se generan sesión por sesión |

El detalle de qué está verificado y qué queda pendiente está en
[TESTING_PLAN_E2E.md](TESTING_PLAN_E2E.md).
