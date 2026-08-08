# Sesión 1 — Estado base: el problema que DataOps resuelve

**Capítulo:** 1 — Fundamentos de DataOps
**Fecha:** sábado **01/08/2026** · 08:00–11:00 · Aula **34-302**
**Tipo:** contenido
**Stack:** Neon.tech (Serverless PostgreSQL) · GitHub · Python gestionado con `uv`

---

## Objetivo

Aprovisionar la base de datos transaccional de Parch & Posey en Neon.tech, con branches
`main` y `dev` aisladas, y cargar los datos semilla **exclusivamente en `dev`** mediante un
script de Python.

Al terminar la sesión, cada estudiante tiene una base de datos real, creada por él mismo, y
la experiencia concreta de por qué `main` se protege.

### Objetivos específicos

1. Entender qué cambia con **Serverless Postgres**: la separación entre cómputo y
   almacenamiento, y por qué eso hace viable el branching de bases de datos.
2. Crear un proyecto en Neon con dos branches (`main` y `dev`) y comprobar su **aislamiento**.
3. Inicializar un proyecto Python con `uv` y ejecutar una carga de datos parametrizada por
   variables de entorno.
4. Verificar el estado base: 5 tablas, 16 390 filas, integridad referencial completa.

---

## Prerrequisitos

### Cuentas (crear **antes** de la sesión)

| Servicio | URL | Notas |
|---|---|---|
| GitHub | https://github.com | Con sesión iniciada; se usa desde la Sesión 2 en adelante |
| Neon.tech | https://neon.tech | El tier gratuito es suficiente para todo el módulo |

### Herramientas locales

```bash
git --version    # cualquier versión reciente
uv --version     # gestor de proyectos Python del curso
```

Si falta `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> **No necesitas instalar PostgreSQL localmente.** La base de datos vive en Neon.
> **No uses `pip` ni `venv`** en este curso — ver la convención en el
> [README del módulo](../../README.md#convención-de-entornos-python).

### Repositorio

```bash
git clone https://github.com/davilla41/data_ops_course_101.git
cd data_ops_course_101
ls data/*.json     # deben aparecer 5 archivos
```

### Conocimiento previo

SQL intermedio (joins y agregaciones) y Python básico. No se asume experiencia previa con
Neon, con Serverless Postgres ni con `uv`.

---

## Contenido de la carpeta

| Ruta | Qué es |
|---|---|
| [presentacion/presentacion.md](presentacion/presentacion.md) | Presentación en formato Marp (15 slides) |
| [presentacion/markmap.html](presentacion/markmap.html) | Mapa mental introductorio de DataOps — ábrelo en el navegador |
| [codigo/inyeccion_semilla.py](codigo/inyeccion_semilla.py) | Script de creación del schema y carga de la semilla |
| [codigo/pyproject.toml](codigo/pyproject.toml) | Definición del proyecto `uv` y sus dependencias |
| [codigo/.env.example](codigo/.env.example) | Plantilla de variables de entorno — cópiala a `.env` |
| [../../data/](../../data/) | Datos semilla de Parch & Posey en JSON |
| [../../er_model.png](../../er_model.png) | Diagrama entidad-relación del modelo |

> 🪟 **En Windows**, configura Git Bash antes de empezar: [WINDOWS_USERS.md](../../WINDOWS_USERS.md).
> El `markmap.html` necesita conexión a internet — carga sus librerías desde un CDN.

---

## Guion del taller

### 1. Crear el proyecto en Neon

En https://console.neon.tech → **Create project**:

- **Name:** `parch_posey_dataops`
- **Postgres version:** 16
- **Region:** la más cercana (ej. AWS `us-east-2`)

Neon crea el proyecto con una branch por defecto llamada `main`. **Esa branch se queda
vacía** — es la referencia intocable.

### 2. Crear la branch `dev`

Menú lateral → **Branches** → **Create branch**:

- **Name:** `dev`
- **Parent branch:** `main`
- **Include data up to:** *Current point in time*

### 3. Obtener los connection strings

**Dashboard** → panel **Connection string**. Selecciona la branch en el desplegable y copia
la URL completa (formato URI). Repite para la otra branch.

Deben quedarte dos cadenas con **hosts distintos**. Si son idénticas, no cambiaste el
desplegable.

### 4. Configurar el entorno local

```bash
cd Cap_1_Fundamentos_DataOps/sesion_01_estado_base/codigo
uv sync
cp .env.example .env
```

Edita `.env` y pega tus dos connection strings. El archivo está excluido en el
[`.gitignore`](../../.gitignore) raíz — verifícalo con `git status`.

### 5. Ejecutar la inyección

```bash
uv run inyeccion_semilla.py --solo-verificar   # debe reportar las 5 tablas como (no existe)
uv run inyeccion_semilla.py                    # carga
```

Salida esperada:

```text
Verificación post-commit:
  OK  regions      esperado=     4 real=     4
  OK  sales_reps   esperado=    50 real=    50
  OK  accounts     esperado=   351 real=   351
  OK  orders       esperado=  6912 real=  6912
  OK  web_events   esperado=  9073 real=  9073

Estado base listo. Total: 16390 filas en 5 tablas.
```

### 6. Validar el aislamiento

En el Neon Console:

1. Branch `dev` → **Tables** → deben estar las cinco tablas pobladas.
2. Branch `main` → **Tables** → **debe estar vacía**. Esa es la prueba de que el branching
   funcionó.

---

## El modelo de datos resultante

Versión visual: [`er_model.png`](../../er_model.png) — ⚠️ pendiente de corregir; nombra
`region` en singular y omite `orders.occurred_at` y `orders.gloss_qty`. La fuente de verdad
es el DDL del script.

```
regions (4)
  id, name
    ▲ region_id
sales_reps (50)
  id, name, region_id
    ▲ sales_rep_id
accounts (351)
  id, name, website, lat, long, primary_poc, sales_rep_id
    ▲ account_id              ▲ account_id
orders (6912)               web_events (9073)
  occurred_at, *_qty,         occurred_at, channel
  *_amt_usd
```

Rango temporal de los datos: **diciembre 2013 – enero 2017**.

---

## Decisiones de diseño del script

Vale la pena leer [`inyeccion_semilla.py`](codigo/inyeccion_semilla.py) completo: los
comentarios explican el *por qué* de cada decisión, no el *qué*. Los cuatro puntos que se
discuten en clase:

| Decisión | Por qué |
|---|---|
| **Guardrail** que aborta si `NEON_DEV_DATABASE_URL` y `NEON_MAIN_DATABASE_URL` coinciden | El script hace `DROP TABLE`. El entorno destino nunca debe ser implícito. |
| **Una sola transacción** para todo el DDL + la carga | Un `DROP` exitoso seguido de un `INSERT` fallido dejaría al estudiante sin punto de partida. |
| **Conversión explícita de tipos** | Todo el JSON viene como string. Sin cast, el schema termina en `TEXT` y las agregaciones de la Sesión 7 se rompen. |
| **`execute_values`** en lugar de `INSERT` fila a fila | Neon es serverless: 6912 round-trips de red tardan minutos. El costo dominante en pipelines de datos es la latencia, no el CPU. |

---

## Relación con el Momento Evaluativo 1

Lo que se construye hoy es el **insumo obligatorio** del
[Momento 1 — CI/CD en Base de Datos](../../evaluaciones/momento_1_cicd_bd.md) (30 % de la
nota final, se sustenta el **viernes 14/08/2026**).

Concretamente:

- El **schema** que crea `inyeccion_semilla.py` es el que se convierte en la migración
  baseline `V1__baseline_parch_posey.sql` en la Sesión 2. Sin él no hay nada que versionar.
- Las **dos branches de Neon** son los dos entornos que el workflow de GitHub Actions va a
  distinguir: `dev` en los pull requests, `main` en los merges.
- Los **connection strings** se convierten en los GitHub Secrets `FLYWAY_URL_DEV` y
  `FLYWAY_URL_PROD` (ver la plantilla
  [`.github/workflows/flyway-migrate.yml`](../../.github/workflows/flyway-migrate.yml)).

> ⚠️ **Guarda tus connection strings.** Si pierdes el proyecto de Neon tendrás que rehacer
> esta sesión completa antes de poder avanzar con el Momento 1.

A partir de la Sesión 2, **ningún cambio de schema se hace con un script como este**: se
hace con migraciones Flyway versionadas y aplicadas por CI/CD. `inyeccion_semilla.py` es
deliberadamente el "antes" de la historia — el trabajo manual que el resto del módulo
elimina.

---

## Renderizar la presentación

```bash
# desde la raíz del repositorio
npx @marp-team/marp-cli@latest \
  Cap_1_Fundamentos_DataOps/sesion_01_estado_base/presentacion/presentacion.md --pdf
```

El tema editorial del curso vive en [`.marp/tema_dataops.css`](../../.marp/tema_dataops.css)
y está registrado en [`.marprc.yml`](../../.marprc.yml). En VS Code, la extensión
*Marp for VS Code* lo toma de [`.vscode/settings.json`](../../.vscode/settings.json).

---

## Próxima sesión

**[Sesión 2 — CI/CD en base de datos con Flyway](../sesion_02_cicd_flyway/)** · 08/08/2026.
El `DROP TABLE` de hoy se convierte en migraciones versionadas, y GitHub Actions reemplaza
tu terminal.
