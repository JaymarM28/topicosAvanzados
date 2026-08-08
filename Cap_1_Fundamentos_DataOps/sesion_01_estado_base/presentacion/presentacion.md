---
marp: true
theme: dataops
paginate: true
footer: 'SI6010-5979 · Tendencias emergentes en desarrollo de software · Sesión 1'
title: 'Sesión 1: Estado Base y Branching de BD'
author: 'Pos ST1707 — EAFIT'
lang: es
---

<!-- _class: portada -->

<div class="kicker">Capítulo 1 · Fundamentos de DataOps</div>

# Sesión 1: Estado Base y Branching de BD

<div class="subtitulo">
Antes de automatizar cualquier cosa, hay que tener algo que automatizar.
</div>

<div class="meta">

**Sábado 01/08/2026** · 08:00–11:00 · Aula 34-302
**Stack:** Neon.tech (Serverless PostgreSQL) · GitHub · Python con `uv`

**Objetivo de la sesión** — Aprovisionar la base de datos transaccional de Parch & Posey en Neon, con branches `main` y `dev` aisladas, y cargar los datos semilla **exclusivamente en `dev`**.

</div>

---

## Serverless Postgres: qué cambia realmente

<div class="columnas estrecha-izquierda">
<div>

Un PostgreSQL tradicional acopla **cómputo** y **almacenamiento** en la misma máquina. Apagarlo significa perder la base; escalarlo significa migrarla.

Neon los separa: el almacenamiento vive en un servicio distribuido, y el cómputo es un proceso que **se enciende cuando llega una query y se apaga cuando no hay tráfico**.

La consecuencia interesante no es el ahorro. Es que **crear una base de datos deja de ser un proyecto de infraestructura** y pasa a ser una llamada de API.

</div>
<div>

<div class="diagrama">
 TRADICIONAL
 ┌─────────────────────┐
 │  cómputo + storage  │
 │   (mismo servidor)  │
 └─────────────────────┘
   copiar = copiar todo


 SERVERLESS (Neon)
 ┌──────────┐
 │ cómputo  │  ← efímero
 └────┬─────┘
      │
 ┌────┴───────────────┐
 │  storage (COW)     │
 └────────────────────┘
   copiar = puntero
</div>

<div class="facts">

### Facts

- El storage usa **copy-on-write**: una copia no duplica bytes hasta que algo cambia.
- Por eso una branch de 50 GB se crea en **segundos** y cuesta casi nada.

</div>
</div>
</div>

---

## Branching de bases de datos

<div class="columnas">
<div>

En código, nadie discute el flujo: `git checkout -b feature`, rompes lo que quieras, y `main` ni se entera.

En bases de datos eso históricamente **no existía**. El "entorno de desarrollo" era un servidor compartido donde tres personas se pisaban los cambios, con datos de hace ocho meses.

El copy-on-write cambia la ecuación. Una branch de Neon es una base de datos **completa e independiente**, con los datos reales, creada al instante.

**El schema deja de ser infraestructura y empieza a comportarse como código.**

</div>
<div>

<div class="diagrama">
  main ────●────●────●──→
           │
           └── dev ──●──●──→
               ↑
        branch instantánea
        datos completos
        aislamiento total
</div>

<div class="facts">

### Facts

- Una branch de Neon es **aislada**: un `DROP TABLE` en `dev` no toca `main`.
- Cada branch trae **su propio connection string** — y ahí está el riesgo.

</div>
</div>
</div>

---

## Por qué separar `dev` de `main`

<div class="columnas">
<div>

`main` representa **el estado que el negocio consume**: reportes, cierres de mes, decisiones.

`dev` es donde se rompen cosas a propósito — probar una migración, cargar datos, verificar un índice.

La separación no es burocracia: es la precondición para **automatizar sin miedo**. Si el pipeline solo toca `dev` hasta que alguien apruebe un pull request, un error se vuelve barato.

Hoy esa separación la sostiene tu disciplina. Desde la Sesión 2, la sostiene **CI/CD**.

</div>
<div>

| | `main` | `dev` |
|---|---|---|
| Rol | Referencia | Banco de pruebas |
| Cambios | Merge aprobado | Libres |
| `DROP TABLE` | Nunca | Sin problema |
| Hoy | Queda vacía | Recibe la semilla |

<div class="aviso">

**Regla del curso.** El script de hoy hace `DROP TABLE`. Apuntarlo a `main` borra el estado base. Hay un guardrail que aborta si ambos strings coinciden — pero no te salva de pegar el equivocado.

</div>
</div>
</div>

---

## Checklist pre-taller

<div class="columnas">
<div>

### Cuentas

<ul class="check">
<li>Cuenta de <strong>GitHub</strong> con sesión iniciada.</li>
<li>Cuenta de <strong>Neon.tech</strong> creada — el tier gratuito basta.</li>
</ul>

### Herramientas locales

<ul class="check">
<li><code>git --version</code> responde.</li>
<li><code>uv --version</code> responde.</li>
</ul>

Si falta `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

</div>
<div>

### Repositorio

<ul class="check">
<li>Repositorio del curso clonado.</li>
<li>Los cinco archivos semilla presentes.</li>
</ul>

```bash
git clone https://github.com/davilla41/\
data_ops_course_101.git
cd data_ops_course_101
ls data/*.json     # deben ser 5
```

<div class="facts">

### Facts

- **No** instales PostgreSQL: la base vive en Neon.
- **No** uses `pip` ni `venv`: todo pasa por `uv`.

</div>
</div>
</div>

---

<!-- _class: seccion -->

<div class="kicker">Parte práctica</div>

## Taller: construir el estado base

---

## Paso 1 · Crear el proyecto en Neon

<div class="columnas estrecha-izquierda">
<div>

1. Entra a **https://console.neon.tech** e inicia sesión.
2. **Create project**.
3. Configura:
   - **Name:** `parch_posey_dataops`
   - **Postgres version:** 16
   - **Region:** la más cercana (ej. AWS `us-east-2`)
4. **Create**.

Neon crea el proyecto con una branch por defecto llamada `main` y una base de datos `neondb`.

**Esa branch `main` se queda vacía.** No la toques.

</div>
<div>

<div class="diagrama">
 Proyecto: parch_posey_dataops
 └── branch: main   (por defecto)
     └── database: neondb
         └── schema: public  ← vacío
</div>

<div class="facts">

### Facts

- El proyecto tarda **segundos** en aprovisionarse: no hay servidor que instalar.
- Neon *suspende* el cómputo tras unos minutos sin uso. La primera query después de eso tarda ~1 s en despertar. Es normal, no es un error.

</div>
</div>
</div>

---

## Paso 2 · Crear la branch `dev`

<div class="columnas estrecha-izquierda">
<div>

En el Neon Console, menú lateral → **Branches** → **Create branch**.

- **Name:** `dev`
- **Parent branch:** `main`
- **Include data up to:** *Current point in time*

**Create branch**.

Ya tienes dos bases de datos independientes. Lo que hagas en `dev` no afecta a `main` — y eso es justamente lo que vas a comprobar hoy.

</div>
<div>

<div class="diagrama">
 Proyecto: parch_posey_dataops
 ├── branch: main   ← vacía, intocable
 │   └── neondb
 └── branch: dev    ← aquí trabajas
     └── neondb
</div>

<div class="facts">

### Facts

- La branch se crea **instantáneamente** aunque el padre tenga datos: es copy-on-write.
- Cada branch tiene un **host distinto** en su connection string. Ese sufijo es cómo las distingues.

</div>
</div>
</div>

---

## Paso 3 · Obtener los connection strings

<div class="columnas">
<div>

En **Dashboard** → panel **Connection string**:

1. Selecciona la branch en el desplegable.
2. Copia la URL completa (formato URI, no "parameters only").
3. Repite cambiando el desplegable a la otra branch.

Deben quedarte **dos** cadenas con **hosts distintos**:

```text
# dev
postgresql://user:pass@ep-xxxx-dev.
  us-east-2.aws.neon.tech/neondb?sslmode=require

# main
postgresql://user:pass@ep-yyyy.
  us-east-2.aws.neon.tech/neondb?sslmode=require
```

</div>
<div>

<div class="aviso">

**Compara los hosts antes de continuar.** Si las dos cadenas son idénticas, no cambiaste el desplegable de branch y estás a punto de cargar datos en `main`.

</div>

<div class="facts">

### Facts

- El connection string **contiene la contraseña**. Nunca lo pegues en un archivo versionado, en Slack ni en un issue.
- `?sslmode=require` no es opcional en Neon: sin él, la conexión falla.

</div>
</div>
</div>

---

## Paso 4 · Configurar el entorno local

<div class="columnas">
<div>

El proyecto Python ya existe en el repositorio. Solo hay que sincronizarlo:

```bash
cd Cap_1_Fundamentos_DataOps/\
sesion_01_estado_base/codigo

uv sync
```

`uv sync` lee `pyproject.toml` y `uv.lock`, descarga Python 3.12 si hace falta y crea `.venv` con las dependencias exactas.

Ahora las credenciales:

```bash
cp .env.example .env
```

Abre `.env` y pega **tus** dos connection strings.

</div>
<div>

### Si arrancaras de cero

Así se creó este proyecto — es el patrón para todas las sesiones del curso:

```bash
uv init --name inyeccion-semilla \
        --python 3.12

uv add psycopg2-binary python-dotenv
```

<div class="facts">

### Facts

- `uv.lock` **se versiona**: es lo que garantiza que tu entorno y el del compañero sean idénticos.
- `.env` **no se versiona**. Está en el `.gitignore` raíz. Verifícalo con `git status`.

</div>
</div>
</div>

---

<!-- _class: compacta -->

## Paso 5 · El guardrail

De `inyeccion_semilla.py` — lo que impide que cargues contra `main`:

```python
    # ¿Por qué el script se niega a correr si dev y main apuntan al mismo sitio? Porque en
    # DataOps la branch `main` es sagrada: representa el estado que el negocio consume.
    # Este script hace DROP TABLE. Ejecutarlo contra main destruiría producción sin dejar
    # rastro ni forma de revertir. Un guardrail que aborta es más barato que un incidente,
    # y el patrón se repetirá todo el curso: el entorno destino nunca es implícito.
    if url_main and url_dev.strip() == url_main.strip():
        print(
            "ERROR: NEON_DEV_DATABASE_URL y NEON_MAIN_DATABASE_URL apuntan a la misma base.\n"
            "       Este script hace DROP TABLE — nunca debe correr contra main.",
            file=sys.stderr,
        )
        sys.exit(1)
```

Un guardrail no reemplaza el criterio: **verifica los hosts antes de ejecutar.**

---

<!-- _class: compacta -->

## Paso 5 · La trampa de los tipos

Todo el JSON viene como **string**. Convertir no es cosmética — es donde se rompen las cargas:

```python
def _timestamp(valor: str) -> datetime:
    # ¿Por qué recortamos la cadena a 26 caracteres? Los JSON traen 7 dígitos de fracción
    # de segundo ("17:31:14.0000000"), herencia del export original en SQL Server.
    # PostgreSQL almacena microsegundos — 6 dígitos — y `datetime.fromisoformat` rechaza
    # los 7. Truncar aquí, de forma explícita y visible, es preferible a descubrir el
    # error a mitad de una carga de 6912 filas. Regla general de ingeniería de datos:
    # normaliza en el borde de entrada, no en el medio del pipeline.
    return datetime.fromisoformat(valor[:26])
```

<div class="facts">

### Facts

- Sin conversión explícita, el schema termina lleno de `TEXT` — y las agregaciones de la Sesión 7 dejan de funcionar.

</div>

---

## Paso 6 · Ejecutar la inyección

<div class="columnas">
<div>

Primero, sin escribir nada:

```bash
uv run inyeccion_semilla.py --solo-verificar
```

Debe reportar las cinco tablas como `(no existe)`. Si reporta filas, estás apuntando a una base que ya tiene datos — revisa tu `.env`.

Ahora sí:

```bash
uv run inyeccion_semilla.py
```

</div>
<div>

```text
Creando schema...
  regions           4 filas
  sales_reps       50 filas
  accounts        351 filas
  orders         6912 filas
  web_events     9073 filas

Verificación post-commit:
  OK  regions      esperado=4     real=4
  OK  sales_reps   esperado=50    real=50
  OK  accounts     esperado=351   real=351
  OK  orders       esperado=6912  real=6912
  OK  web_events   esperado=9073  real=9073

Estado base listo.
Total: 16390 filas en 5 tablas.
```

</div>
</div>

---

## El modelo que acabas de crear

<div class="columnas estrecha-derecha">
<div>

<div class="diagrama">
 regions (4)
   id, name
     ▲
     │ region_id
 sales_reps (50)
   id, name, region_id
     ▲
     │ sales_rep_id
 accounts (351)
   id, name, website,
   lat, long, primary_poc
     ▲            ▲
     │ account_id │ account_id
 orders (6912)  web_events (9073)
   occurred_at    occurred_at
   *_qty          channel
   *_amt_usd
</div>

</div>
<div>

Cinco tablas, **16 390 filas**, integridad referencial completa mediante foreign keys.

Datos reales de un distribuidor de papel entre **dic-2013 y ene-2017**: órdenes por línea de producto (standard, gloss, poster) y eventos de visita web por canal.

<div class="facts">

### Facts

- Todo el JSON venía como **string**. El script castea a `INTEGER`, `NUMERIC` y `TIMESTAMP`: el schema es un contrato.
- La carga es **una sola transacción**. O queda completa, o no queda nada.

</div>
</div>
</div>

---

<!-- _class: cierre -->

## Validación y cierre

<div class="columnas">
<div>

### Verifica en el Neon Console

1. **Branches** → selecciona `dev` → **Tables**.
   Deben aparecer las cinco tablas con sus conteos.
2. Cambia a la branch **`main`** → **Tables**.
   **Debe estar vacía.** Esa es la prueba de que el aislamiento funcionó.
3. Corre una query en el SQL Editor de `dev`:

```sql
SELECT r.name AS region,
       count(o.id) AS ordenes
FROM orders o
JOIN accounts a    ON a.id = o.account_id
JOIN sales_reps s  ON s.id = a.sales_rep_id
JOIN regions r     ON r.id = s.region_id
GROUP BY 1 ORDER BY 2 DESC;
```

</div>
<div>

### Lo que te llevas

- Una base transaccional real, aprovisionada por ti, con branches aisladas.
- La intuición de por qué `main` se protege — y de lo fácil que es equivocarse de connection string.

<div class="aviso">

**Esto es el insumo obligatorio del Momento 1.** Sin el estado base en Neon no hay nada que migrar con Flyway. Guarda tus connection strings.

</div>

### Próxima sesión

**08/08 · CI/CD en base de datos con Flyway.** El `DROP TABLE` de hoy se convierte en migraciones versionadas, y GitHub Actions reemplaza tu terminal.

</div>
</div>
