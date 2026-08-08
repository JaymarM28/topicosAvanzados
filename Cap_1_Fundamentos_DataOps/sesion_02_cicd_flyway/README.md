# Sesión 2 — CI/CD en base de datos con Flyway

**Capítulo:** 1 — Fundamentos de DataOps
**Fecha:** sábado **08/08/2026** · 08:00–11:00 · Aula **33-302**
**Tipo:** contenido
**Stack:** Flyway · GitHub Actions · Neon (PostgreSQL)

---

## Objetivo

Convertir el schema de Parch & Posey en código versionado: que Flyway tome control de la
base existente, que los cambios se expresen como migraciones y que GitHub Actions los
aplique a la branch `main` de Neon sin que nadie se conecte a la base a mano.

### Objetivos específicos

1. Hacer que Flyway adopte una base de datos que **ya existe** (`flyway baseline`) y
   entender qué guarda la tabla `flyway_schema_history`.
2. Distinguir cuándo un cambio va en una migración **versionada** (`V__`) y cuándo en una
   **repetible** (`R__`), y por qué la lógica de negocio pertenece a la segunda.
3. Vivir un error de diseño desplegado y corregirlo mediante **roll forward**, entendiendo
   por qué Flyway se niega a que reescribas el pasado.
4. Automatizar el despliegue con GitHub Actions usando la imagen oficial de Flyway y
   gestionando la credencial como secreto.

---

## Prerrequisitos

### Haber completado la Sesión 1

Esta sesión **no arranca desde cero**. Necesitas:

| Requisito | Cómo verificarlo |
|---|---|
| Proyecto de Neon con branches `main` y `dev` | Neon Console → *Branches* |
| Branch `dev` con las 5 tablas y 16 390 filas | `uv run inyeccion_semilla.py --solo-verificar` desde [la carpeta de la Sesión 1](../sesion_01_estado_base/codigo/) |
| Los dos connection strings a la mano | Neon Console → *Dashboard* → *Connection string* |
| Repositorio propio en GitHub con permisos de administración | Necesario para crear el secreto |

> Si perdiste la branch `dev` (por ejemplo, si la creaste con *Auto-delete: After 1 day*),
> recréala y vuelve a correr la carga de la Sesión 1 **antes** de la clase.

### 🔴 Bootstrap de la branch `main`

La Sesión 1 dejó `main` **vacía** a propósito. Pero las migraciones de hoy modifican tablas
que deben existir: `CREATE INDEX ON orders` falla si `orders` no está.

Antes de que el pipeline pueda correr, `main` necesita el estado base. Esta es **la última
vez en todo el curso que te conectas a `main` a mano**:

```bash
cd ../sesion_01_estado_base/codigo

# Apunta la variable de dev al connection string de main, solo para este comando.
# Se vacía NEON_MAIN_DATABASE_URL para que el guardrail del script no aborte.
NEON_DEV_DATABASE_URL="$(grep '^NEON_MAIN_DATABASE_URL=' .env | cut -d= -f2-)" \
NEON_MAIN_DATABASE_URL="" \
  uv run inyeccion_semilla.py
```

De aquí en adelante, `main` solo cambia por pipeline.

> **Por qué es coherente con la Sesión 1.** Lo que se prohibió allí no fue tocar `main`
> nunca: fue tratarla como un banco de pruebas. Establecer el estado inicial de producción
> una vez, de forma deliberada y documentada, es distinto de aplicarle DDL improvisado cada
> martes. Y es exactamente el escenario que Flyway está diseñado para adoptar: una base que
> ya existía antes de que existiera el control de versiones.

### Herramientas

```bash
git --version
flyway -v        # brew install flyway  (macOS)
docker --version # opcional: para correr Flyway igual que el pipeline
```

> 🪟 **En Windows**, todos los comandos van en **Git Bash**, no en PowerShell ni CMD.
> Ver [WINDOWS_USERS.md](../../WINDOWS_USERS.md).

---

## Contenido de la carpeta

| Ruta | Qué es |
|---|---|
| [presentacion/presentacion.md](presentacion/presentacion.md) | Presentación en Marp (14 slides) |
| [sql_migrations/](sql_migrations/) | Las 4 migraciones del taller |
| [flyway.conf.example](flyway.conf.example) | Plantilla de configuración — cópiala a `flyway.conf` |
| [../../.github/workflows/flyway-migrate.yml](../../.github/workflows/flyway-migrate.yml) | El pipeline de despliegue |

### Las migraciones

| Archivo | Tipo | Qué hace |
|---|---|---|
| `V202608081000__add_index_and_col.sql` | Versionada | Índice compuesto en `orders`; agrega `web_events.utm_source` **como `VARCHAR(2)`** |
| `R__fn_calculate_discount.sql` | Repetible | Función de descuento por volumen (5 / 10 / 15 %) |
| `R__sp_process_order.sql` | Repetible | Procedure que registra una orden y su evento web; llama a la función |
| `V202608081100__fix_web_events_utm_length.sql` | Versionada | Amplía `utm_source` a `VARCHAR(100)` |

> ⚠️ **Nota para el docente.** El `VARCHAR(2)` de la primera migración es un **error
> intencional**. Es el eje narrativo de la sesión: se despliega, el procedure falla al
> recibir `'google'`, y se corrige con roll forward en lugar de editar el script original.
> No lo "arregles" antes de la clase.

---

## Guion del taller

### 1. Que Flyway tome control (`baseline`)

```bash
cd Cap_1_Fundamentos_DataOps/sesion_02_cicd_flyway
cp flyway.conf.example flyway.conf     # y edítalo con tu URL de dev

flyway -baselineVersion=1 \
       -baselineDescription="Parch and Posey estado base" \
       baseline
```

Crea `flyway_schema_history` y registra el estado actual como versión 1. **No toca ninguna
tabla.**

### 2. Primera migración versionada

```bash
flyway info                          # qué está pendiente
flyway migrate -target=202608081000  # aplicar solo hasta aquí
```

Aplica `V202608081000` y, detrás, los dos repetibles.

> ⚠️ **Por qué `-target` y no un `flyway migrate` a secas.** Este repositorio entrega las
> 4 migraciones completas desde el día uno — incluida `V202608081100`, el fix del paso 5.
> En un proyecto real ese archivo **no existiría todavía** en este punto de la historia: se
> escribe recién después de descubrir el error. Un `flyway migrate` sin `-target` aplicaría
> las 4 de una sola vez y el fallo del paso 3 nunca ocurriría — el bug ya vendría corregido.
> `-target` le dice a Flyway "llega hasta aquí y detente", que es la forma correcta de
> reproducir la cronología sin editar ni ocultar archivos.

### 3. Provocar el fallo

```bash
psql "$(grep '^NEON_DEV_DATABASE_URL=' ../sesion_01_estado_base/codigo/.env | cut -d= -f2-)" \
  -c "CALL sp_process_order(1001, 100, 50, 20, 'adwords', 'google');"
```

```text
ERROR: value too long for type character varying(2)
```

Sin `psql` instalado, usa el **SQL Editor** del Neon Console sobre la branch `dev`.

### 4. Comprobar que Flyway protege el pasado

Edita `V202608081000__add_index_and_col.sql`, cambia el `2` por `100` y ejecuta
`flyway migrate`:

```text
ERROR: Validate failed: Migrations have failed validation
Migration checksum mismatch for migration version 202608081000
```

**Revierte esa edición.** El punto era ver el error, no dejarlo.

### 5. Roll forward

`V202608081100__fix_web_events_utm_length.sql` ya estaba en el repositorio — lo que faltaba
era aplicarlo. Ahora sí, sin `-target`, para que Flyway tome todo lo pendiente:

```bash
flyway migrate
```

Y la llamada que fallaba ahora funciona.

### 6. Automatizar hacia `main`

En GitHub → *Settings* → *Secrets and variables* → *Actions* → **New repository secret**:

| Campo | Valor |
|---|---|
| Name | `NEON_MAIN_DATABASE_URL` |
| Secret | El connection string completo de tu branch **`main`** |

Luego:

```bash
git add Cap_1_Fundamentos_DataOps/sesion_02_cicd_flyway/sql_migrations/
git commit -m "feat(db): atribución utm_source y descuento por volumen"
git push origin main
```

Sigue el run en la pestaña **Actions**.

---

## Detalles que vale la pena mirar en el código

| Dónde | Qué |
|---|---|
| [`R__fn_calculate_discount.sql`](sql_migrations/R__fn_calculate_discount.sql) | Por qué `CREATE OR REPLACE` y no `DROP`+`CREATE`; qué promete `IMMUTABLE` al planificador |
| [`R__sp_process_order.sql`](sql_migrations/R__sp_process_order.sql) | Por qué el descuento se aplica línea por línea y no solo al total; la deuda documentada del `MAX(id)+1` |
| [`V202608081100__...`](sql_migrations/V202608081100__fix_web_events_utm_length.sql) | Por qué ampliar un `VARCHAR` es instantáneo y reducirlo no |
| [`flyway-migrate.yml`](../../.github/workflows/flyway-migrate.yml) | La traducción URI→JDBC y por qué `::add-mask::` es obligatorio |

---

## Relación con el Momento Evaluativo 1

Esta sesión **es** el Momento 1. Lo que se construye hoy es el entregable, y se sustenta el
**viernes 14/08/2026** — ver el
[enunciado completo](../../evaluaciones/momento_1_cicd_bd.md) (30 % de la nota final).

Cobertura del alcance exigido:

| Requisito del Momento 1 | Estado tras esta sesión |
|---|---|
| Baseline del schema | ✅ Vía `flyway baseline` |
| ≥ 3 migraciones evolutivas (`V__`) | ⚠️ **Hoy son 2** — falta al menos una |
| ≥ 1 migración repetible (`R__`) | ✅ Hay 2 |
| Tabla nueva, columna añadida, índice o restricción | ⚠️ Falta la **tabla nueva** |
| Workflow de GitHub Actions | ✅ Aplica a `main` en cada push |
| Secretos en GitHub, cero credenciales en el repo | ✅ |
| Evidencia de una ejecución fallida y su corrección | ✅ El paso 3–5 es exactamente eso — **documéntalo** |

### Lo que te falta para el entregable

Dos ideas que cierran los huecos y salen del propio taller:

1. **Una tabla nueva.** `utm_campaign` o una tabla de parámetros para los tramos de
   descuento, que permitiría degradar la función de `IMMUTABLE` a `STABLE` y discutir por
   qué.
2. **Convertir `orders.id` y `web_events.id` en `IDENTITY`.** El procedure calcula el id con
   `MAX(id)+1`, que no resiste concurrencia — está comentado en el propio script. Una
   migración `V__` que añada la secuencia y la ajuste al máximo actual es un ejercicio
   realista y elimina una deuda real.

Ambas requieren pensar en la migración de los datos existentes, que es donde está el
aprendizaje.

---

## Renderizar la presentación

```bash
# desde la raíz del repositorio
npx @marp-team/marp-cli@latest \
  Cap_1_Fundamentos_DataOps/sesion_02_cicd_flyway/presentacion/presentacion.md --pdf
```

---

## Próxima sesión

**[Sesión 3 — Sustentación Momento 1](../sesion_03_sustentacion_momento1/)** · viernes
14/08/2026. Demo en vivo de 10 minutos: crear una migración, hacer push, mostrar el workflow
aplicándola y el cambio reflejado en Neon.
