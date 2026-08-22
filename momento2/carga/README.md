# Carga vía Internal Stage — Momento 2, punto 3

Equipo 5 · RutaSegura (Cobertura Vehicular)

Esta carpeta contiene la **carga** del pipeline de ingesta: cómo llegan a Snowflake
los CSV que produce [`../extraer_neon_a_csv.py`](../extraer_neon_a_csv.py).

```
Neon ──(extraer_neon_a_csv.py)──► data_extraida/*.csv ──(PUT)──► @RAW.STAGE_NEON ──(COPY INTO)──► RAW.*
                                                                                          │
                                                                                          └──► CONTROL.BITACORA_CARGA
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `03_file_format_y_stage.sql` | Crea `RAW.FF_CSV_NEON` (file format nombrado) y `RAW.STAGE_NEON` (internal stage), con sus grants |
| `04_raw_tables.sql` | Crea las 7 tablas destino en `RAW`, con el esquema post-migraciones |
| `cargar.py` | Ejecuta `PUT` + `COPY INTO` tabla por tabla y escribe la bitácora |

## Cómo se ejecuta

**Una sola vez**, en un Worksheet de Snowsight, con un rol que pueda crear objetos
(el número de cada script es su turno en el orden global del Momento 2):

1. `../01_setup_snowflake.sql` — base, schema `RAW`, warehouse, rol `TEAM5_LOADER`
2. `../02_bitacora_carga.sql` — schema `CONTROL` y tabla `BITACORA_CARGA`
3. `03_file_format_y_stage.sql`
4. `04_raw_tables.sql`

**Cada vez que se quiera cargar**, desde `momento2/`:

```bash
uv run extraer_neon_a_csv.py     # genera data_extraida/*.csv desde Neon
uv run carga/cargar.py           # PUT + COPY INTO de las 7 tablas
```

Comandos útiles:

```bash
uv run carga/cargar.py --tabla policy    # una sola tabla
uv run carga/cargar.py --listar-stage    # qué archivos hay en el stage
```

El script devuelve código de salida `1` si alguna tabla falló, para que un pipeline
automatizado pueda detectarlo.

## El contrato con la extracción

`cargar.py` espera encontrar en `../data_extraida/` **un archivo por tabla**, llamado
`<nombre_de_tabla>.csv`. El `FILE FORMAT` está construido para el formato que
`extraer_neon_a_csv.py` documenta en su docstring:

| Aspecto | Valor | Opción correspondiente en `FF_CSV_NEON` |
|---|---|---|
| Encoding | UTF-8 | `ENCODING = 'UTF8'` |
| Delimitador | coma | `FIELD_DELIMITER = ','` |
| Quoting | mínimo, con `"` | `FIELD_OPTIONALLY_ENCLOSED_BY = '"'` |
| Primera fila | nombres de columna | `PARSE_HEADER = TRUE` |
| NULL | campo vacío | `NULL_IF = ('')` + `EMPTY_FIELD_AS_NULL = TRUE` |
| Booleanos | `TRUE` / `FALSE` | los reconoce el tipo `BOOLEAN` de Snowflake |
| Fechas | `YYYY-MM-DD` | formato por defecto de Snowflake |
| Timestamps | `YYYY-MM-DD HH:MI:SS` | formato por defecto de Snowflake |
| Compresión | ninguna en disco | `PUT` la comprime a `.gz`; `COMPRESSION = AUTO` la detecta |

Si la extracción cambia alguna de esas convenciones, hay que cambiar el file format
en el mismo commit.

## Decisiones y por qué

### `FILE FORMAT` nombrado, no inline

Son 7 tablas. Inline habría que repetir las mismas ocho opciones siete veces, y el día
que cambie el formato de salida hay que acordarse de tocar las siete. Con un objeto
nombrado el contrato vive en un solo sitio.

### `MATCH_BY_COLUMN_NAME` en vez de carga posicional

Las columnas se emparejan **por nombre**, leyendo el header del CSV (por eso el file
format usa `PARSE_HEADER = TRUE` y no `SKIP_HEADER = 1`; son mutuamente excluyentes).

La alternativa clásica es `SKIP_HEADER = 1` con un `SELECT $1, $2, $3...`. Funciona
igual de bien hasta el día en que alguien agrega una columna en medio del modelo: ahí
el `COPY` posicional **sigue "funcionando"** y mete cada dato en la columna
equivocada, sin error. Con emparejamiento por nombre eso no puede pasar, y si el CSV
trae una columna que la tabla no tiene, el `COPY` falla ruidosamente — que es
exactamente la detección de schema drift que se quiere. Este equipo ya vivió schema
drift real en el Momento 1 (`bill.payment_method`, `bill.paid_date`, la tabla
`vehicle`), así que no es un riesgo hipotético.

### `ON_ERROR = ABORT_STATEMENT`

Explícito aunque coincida con el default de Snowflake: es una decisión, no una
omisión.

Si una sola fila no parsea, se aborta la tabla entera y no se carga nada. El dominio
es una aseguradora: una fila de `BILL` mal parseada es plata mal contada, y una carga
parcial que nadie note es peor que una carga que falla. Además, como la estrategia es
borrar y recargar, reintentar es barato — no hay incentivo para "salvar lo que se
pueda".

Alternativas descartadas:

- **`CONTINUE`** ignora las filas malas y carga el resto. Tiene sentido en logs de
  alto volumen donde perder tres filas de un millón da igual. Aquí significaría un DW
  con un subconjunto silencioso de las facturas.
- **`SKIP_FILE`** salta el archivo completo ante el primer error. Sirve cuando una
  tabla se carga desde muchos archivos particionados y se prefiere perder una
  partición antes que la carga entera. Aquí es un archivo por tabla, así que
  `SKIP_FILE` y `ABORT_STATEMENT` hacen lo mismo salvo por el mensaje de error.

### `FORCE = TRUE` + `DELETE` en transacción

Snowflake recuerda por 64 días qué archivos ya cargó en cada tabla y por defecto los
salta. Eso *parece* idempotencia gratis, pero es una ilusión frágil: depende del
nombre del archivo, caduca sola, y si el CSV cambia de contenido conservando el
nombre, la carga se salta en silencio y el DW queda desactualizado sin que nada lo
reporte.

Preferimos desactivar ese comportamiento implícito (`FORCE = TRUE`) y hacer la
idempotencia explícita en el código: **`DELETE` + `COPY INTO` dentro de una
transacción**, por tabla.

`DELETE` y no `TRUNCATE` porque en Snowflake `TRUNCATE` es DDL, y todo DDL hace commit
implícito de la transacción abierta — o sea, `TRUNCATE` + `COPY` no pueden ser
atómicos. Si el `COPY` falla, la tabla ya quedó vacía y el DW pierde los datos de la
corrida anterior sin haber ganado los nuevos. `DELETE` es DML y sí participa de la
transacción: un fallo hace `ROLLBACK` y la tabla queda exactamente como estaba. En
tablas grandes `TRUNCATE` sería mucho más barato; con los miles de filas de
RutaSegura la diferencia es irrelevante y la atomicidad vale más.

### La bitácora se escribe desde Python

`../registrar_bitacora.sql` propone el patrón `RESULT_SCAN(LAST_QUERY_ID())`, y anota
él mismo su limitación: si el `COPY INTO` falla como comando completo, no hay
resultado que leer y la ejecución fallida **no queda registrada**. Ese es justamente
el caso que más interesa registrar.

`cargar.py` atrapa la excepción y escribe la fila `LOAD_FAILED` a mano, con el mensaje
de error completo de Snowflake. Así la bitácora cubre los tres caminos: `LOADED`,
`PARTIALLY_LOADED` y `LOAD_FAILED` — incluido el caso "el CSV ni siquiera existe".

## Nota sobre el entorno

- **`WH_VEHICLE_COVERGE`** está así escrito en `01_setup_snowflake.sql` (falta la "A" de
  COVERAGE). Como el nombre es consistente en todo ese script, funciona; si se
  corrige, hay que corregirlo también en los `USE WAREHOUSE` de esta carpeta y en
  `.env`.
