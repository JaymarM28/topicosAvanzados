---
marp: true
theme: dataops
paginate: true
footer: 'SI6010-5979 · Tendencias emergentes en desarrollo de software · Sesión 2'
title: 'Sesión 2: CI/CD de Base de Datos con Flyway'
author: 'Pos ST1707 — EAFIT'
lang: es
---

<!-- _class: portada -->

<div class="kicker">Capítulo 1 · Fundamentos de DataOps</div>

# Sesión 2: CI/CD de Base de Datos con Flyway

<div class="subtitulo">
El schema deja de ser algo que alguien cambió un martes, y pasa a ser código con historial.
</div>

<div class="meta">

**Sábado 08/08/2026** · 08:00–11:00 · Aula 33-302
**Stack:** Flyway · GitHub Actions · Neon (PostgreSQL)

**Evaluación** — Lo que construyas hoy es el núcleo del **Momento 1 (30 %)**, que se sustenta el **viernes 14/08**. Se evalúa el repositorio, no la base de datos.

</div>

---

## `flyway_schema_history`: la tabla que lo cambia todo

<div class="columnas estrecha-izquierda">
<div>

Flyway no adivina el estado de tu base: **lo lee de una tabla que él mismo mantiene** dentro de tu schema.

Cada migración aplicada deja una fila con su versión, su descripción, quién la aplicó, cuánto tardó y —lo importante— el **checksum** del archivo.

Ese checksum es el mecanismo completo. Al arrancar, Flyway compara el checksum guardado con el del archivo en disco. Si difieren, se detiene.

**La base de datos deja de ser un misterio y pasa a tener un `git log`.**

</div>
<div>

<div class="diagrama">
 installed_rank | version      | state
 ---------------+--------------+-------
 1              | 1            | BASELINE
 2              | 202608081000 | Success
 3              | 202608081100 | Success
 4              | (repeatable) | Success
</div>

<div class="facts">

### Facts

- Vive **dentro** de tu base, en el mismo schema. Si clonas la branch, se clona con ella.
- Sin esa tabla, Flyway no sabe qué falta — y por eso el primer paso siempre es crearla.

</div>
</div>
</div>

---

## Timestamps vs. secuenciales

<div class="columnas">
<div>

La convención obvia es `V1__`, `V2__`, `V3__`. Funciona perfecto — hasta que son dos personas.

Ana crea `V2__add_index.sql` en su branch. Luis crea `V2__add_column.sql` en la suya. Ambos hacen merge. Flyway encuentra **dos versiones 2** y aborta el pipeline.

Con un timestamp `AAAAMMDDHHMM` la colisión es prácticamente imposible: nadie más creó una migración en ese minuto exacto.

Y el nombre gana información: `V202608081000` te dice **cuándo se decidió** el cambio.

</div>
<div>

| | Secuencial | Timestamp |
|---|---|---|
| Ejemplo | `V2__` | `V202608081000__` |
| Colisión en merge | Frecuente | Casi imposible |
| Orden legible | Sí | Sí |
| Dice cuándo | No | Sí |
| Equipos grandes | Duele | Escala |

<div class="facts">

### Facts

- Flyway ordena por **valor numérico**, no alfabético: `202608081000` va después de `2`.
- La convención se elige **una vez** y no se cambia. Mezclarlas es pedir problemas.

</div>
</div>
</div>

---

## `V__` versus `R__`: la distinción que importa

<div class="columnas">
<div>

**`V__` — Versioned.** Se ejecuta **una sola vez**, en orden, y queda registrada. Para todo lo que no se puede repetir sin consecuencias: crear una tabla, agregar una columna, migrar datos.

**`R__` — Repeatable.** Se ejecuta **cada vez que su contenido cambia**, siempre al final. Para todo lo que se puede recrear desde cero: funciones, procedimientos, vistas.

El criterio no es el tipo de objeto: es si **volver a ejecutarlo** deja la base igual.

</div>
<div>

<div class="diagrama">
 ORDEN DE EJECUCIÓN

 1. V202608081000  ─┐
 2. V202608081100   │ por versión
                   ─┘
 3. R__fn_...      ─┐
 4. R__sp_...       │ alfabético,
                   ─┘ siempre al final
</div>

<div class="facts">

### Facts

- Sin `R__`, cambiar una línea de un procedure crearía un archivo `V__` nuevo cada vez. Veinte archivos para saber qué hace hoy.
- Los `R__` corren **después** de todos los `V__`: la función se recrea sobre el schema ya migrado.

</div>
</div>
</div>

---

## Checklist pre-taller

<div class="columnas">
<div>

### Entorno

<ul class="check">
<li><strong>Git Bash</strong> abierto — no PowerShell ni CMD (ver <code>WINDOWS_USERS.md</code>).</li>
<li>Repositorio actualizado: <code>git pull</code>.</li>
<li>Flyway instalado: <code>flyway -v</code>.</li>
</ul>

Si falta Flyway:

```bash
# macOS
brew install flyway
# Windows: descargar el ZIP de
# flywaydb.org y agregarlo al PATH
```

</div>
<div>

### Credenciales a la mano

<ul class="check">
<li>Connection string de <strong>dev</strong> — trabajarás aquí.</li>
<li>Connection string de <strong>main</strong> — irá a GitHub Secrets.</li>
<li>Sesión iniciada en el Neon Console.</li>
</ul>

<div class="aviso">

**Requisito de la Sesión 1.** Tu branch `dev` debe tener las 5 tablas con 16 390 filas. Verifícalo antes de empezar:
`uv run inyeccion_semilla.py --solo-verificar`

</div>
</div>
</div>

---

<!-- _class: seccion -->

<div class="kicker">Parte práctica</div>

## Taller: de la terminal al pipeline

---

## Paso 1 · Que Flyway tome control

<div class="columnas">
<div>

Tu base **ya existe** — la creaste en la Sesión 1. Flyway no puede aplicar migraciones sin saber de dónde parte.

`baseline` resuelve eso: crea `flyway_schema_history` y registra el estado actual como versión 1, **sin tocar una sola tabla**.

```bash
cd Cap_1_Fundamentos_DataOps/\
sesion_02_cicd_flyway

cp flyway.conf.example flyway.conf
# edita flyway.conf con tu URL de dev

flyway -baselineVersion=1 \
  -baselineDescription="Parch and Posey \
estado base" baseline
```

</div>
<div>

```text
Creating Schema History table
"public"."flyway_schema_history"
with baseline ...
Successfully baselined schema
with version: 1
```

<div class="facts">

### Facts

- `baseline` es **no destructivo**: solo escribe una fila de control.
- Todo lo anterior a la versión 1 queda declarado como "ya estaba ahí". Flyway nunca intentará recrearlo.

</div>
</div>
</div>

---

## Paso 2 · Primera migración versionada

<div class="columnas estrecha-izquierda">
<div>

Producto pide dos cosas: acelerar el listado de órdenes por cuenta, y guardar de qué campaña viene cada visita.

`sql_migrations/V202608081000__add_index_and_col.sql`

```sql
CREATE INDEX idx_orders_account_occurred
    ON orders (account_id, occurred_at DESC);

ALTER TABLE web_events
    ADD COLUMN utm_source VARCHAR(2);
```

El índice es compuesto porque la query filtra por cuenta **y** ordena por fecha. El orden de las columnas no es decorativo.

</div>
<div>

```bash
flyway info
flyway migrate -target=202608081000
```

```text
Migrating schema "public" to version
"202608081000 - add index and col"
```

<div class="facts">

### Facts

- **`-target` es clave hoy.** El archivo del fix ya está en el repo desde el inicio. Sin `-target`, `migrate` lo aplicaría de una vez y el fallo del Paso 4 nunca ocurriría.
- La columna admite NULL a propósito: los eventos históricos no tienen campaña *conocida*, que no es lo mismo que no tener campaña.

</div>
</div>
</div>

---

## Paso 3 · La lógica de negocio va en `R__`

<div class="columnas">
<div>

Dos objetos nuevos, ambos repeatable:

`R__fn_calculate_discount.sql` — descuento por volumen: 5 % desde USD 500, 10 % desde 2 000, 15 % desde 5 000.

`R__sp_process_order.sql` — lo que el backend llama al confirmar una compra: valida la cuenta, calcula el bruto, **invoca la función**, e inserta la orden y su evento web.

Ya se aplicaron: **los repeatables corren siempre al final de cualquier `migrate`**, sin importar el `-target`. Fue la misma llamada del paso anterior.

```text
Migrating with repeatable migration "fn calculate discount"
Migrating with repeatable migration "sp process order"
```

</div>
<div>

<div class="facts">

### Facts

- Se aplican en **orden alfabético**: `fn...` antes que `sp...`. Aquí funciona por suerte tipográfica — cuando el orden importe de verdad, hay que forzarlo con un prefijo numérico.
- Cambia una línea del `.sql` y el próximo `flyway migrate` lo vuelve a aplicar solo. No hace falta archivo nuevo.

</div>

<div class="aviso">

**El criterio, otra vez.** ¿Puedo ejecutar esto dos veces sin romper nada? Si sí → `R__`. Si no → `V__`.

</div>
</div>
</div>

---

## Paso 4 · El desastre

<div class="columnas">
<div>

Llega una visita desde Google Ads. El backend hace lo suyo:

```sql
CALL sp_process_order(
  1001, 100, 50, 20, 'adwords', 'google'
);
```

```text
ERROR: value too long for type
       character varying(2)
CONTEXT: SQL statement "INSERT INTO
  web_events (... utm_source)"
```

`'google'` son 6 caracteres. La columna acepta 2.

**El schema estaba versionado, revisado y desplegado. Y estaba mal.**

</div>
<div>

<div class="facts">

### Facts

- La orden **no quedó a medias**: el procedure se revirtió completo. Sin transacción, habrías tenido una orden sin su evento.
- CI/CD no evita las malas decisiones. Las hace **rápidas de detectar y baratas de corregir**.

</div>

<div class="aviso">

**La tentación.** Abrir `V202608081000__...sql`, cambiar el `2` por `100`, hacer commit. Es lo que haría cualquiera. Es exactamente lo que no se debe hacer.

</div>
</div>
</div>

---

<!-- _class: compacta -->

## Paso 5 · Por qué no se edita el pasado

Cambias el `2` por `100` en la migración ya aplicada y ejecutas `flyway migrate`:

```text
ERROR: Validate failed: Migrations have failed validation
Migration checksum mismatch for migration version 202608081000
-> Applied to database : -826601744
-> Resolved locally    : 124738967
Either revert the changes to the migration, or run repair to update the schema history.
```

Flyway se niega. Y esa negativa te está salvando:

<div class="columnas">
<div>

**Si lo permitiera**, tu base de dev —donde borraste todo y volviste a migrar— tendría `VARCHAR(100)`.

Producción, donde el script viejo ya corrió, seguiría con `VARCHAR(2)`.

</div>
<div>

Dos entornos con **el mismo historial de migraciones** y **schemas distintos**. Que es literalmente el problema que Flyway existe para eliminar.

</div>
</div>

---

## Paso 6 · Roll forward

<div class="columnas estrecha-izquierda">
<div>

No se corrige el pasado: se agrega encima.

`V202608081100__fix_web_events_utm_length.sql`

```sql
ALTER TABLE web_events
    ALTER COLUMN utm_source
    TYPE VARCHAR(100);
```

```bash
flyway migrate
```

Y la llamada que fallaba, ahora pasa:

```sql
CALL sp_process_order(
  1001, 100, 50, 20, 'adwords', 'google'
);
-- NOTICE: Orden 6914 registrada
```

</div>
<div>

<div class="facts">

### Facts

- Ampliar un `VARCHAR` es instantáneo: solo cambia el catálogo, no reescribe la tabla. Reducirlo sí revisa cada fila — por eso quedarse corto sale caro y pasarse casi nunca.
- El error **queda** en el historial, y encima queda la corrección. Esa cicatriz es el registro de auditoría.

</div>

En un año, alguien verá que la columna nació corta, por qué, y cuándo se arregló. Editar el archivo viejo habría borrado esa historia.

</div>
</div>

---

## Paso 7 · Automatizar hacia `main`

<div class="columnas">
<div>

Hasta aquí todo salió de tu terminal contra `dev`. **`main` no se toca a mano.**

**1. Guardar el secreto.** En GitHub → *Settings* → *Secrets and variables* → *Actions* → **New repository secret**:

- **Name:** `NEON_MAIN_DATABASE_URL`
- **Value:** el connection string de tu branch `main`

**2. Disparar el pipeline.**

```bash
git add sql_migrations/
git commit -m "feat(db): utm_source y \
descuento por volumen"
git push origin main
```

</div>
<div>

El workflow hace tres cosas relevantes:

- **Traduce** la URI de Neon al formato JDBC que Flyway espera, y enmascara la contraseña en los logs.
- Corre `validate` **antes** de `migrate`: si alguien editó una migración vieja, se detiene sin tocar la base.
- Usa `baselineOnMigrate`: en el primer run registra el estado de `main` como versión 1 y aplica el resto.

<div class="facts">

### Facts

- `cleanDisabled=true` bloquea `flyway clean`, que borraría el schema entero.
- Un solo secreto, no tres: es lo que el Console te da tal cual.

</div>
</div>
</div>

---

<!-- _class: cierre -->

## Conclusiones

<div class="columnas">
<div>

### Lo que cambió hoy

- El schema tiene **historial**: quién, cuándo, qué y con qué checksum.
- Dos entornos que **no pueden divergir**, porque el mismo pipeline los construye.
- Un error en producción se corrige con un commit, no con una conexión manual a la base.

### Las tres reglas

1. `V__` para lo irrepetible, `R__` para lo recreable.
2. **Nunca** se edita una migración aplicada. Roll forward.
3. `main` se migra por pipeline. Tu terminal solo habla con `dev`.

</div>
<div>

<div class="aviso">

**Esto es el Momento 1.** Se evalúa el 14/08: migraciones versionadas, workflow funcional, secretos bien gestionados y evidencia de **una falla y su corrección**. Lo que pasó en el Paso 4 es exactamente esa evidencia — documéntalo.

</div>

### Para el entregable

El Momento 1 pide **≥3 migraciones evolutivas** y **≥1 repetible**. Hoy hiciste 2 y 2: falta al menos una más. La deuda del `MAX(id)+1` del procedure es una buena candidata — conviértela en `IDENTITY`.

### Próxima sesión

**14/08 · Sustentación Momento 1.** Demo en vivo, no diapositivas.

</div>
</div>
