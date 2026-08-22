# Decisiones de diseño — Momento 2 (Cloud Data Warehouse)

Equipo 5 · RutaSegura (Cobertura Vehicular)

Este documento registra las decisiones no obvias del Momento 2 y, sobre todo, **qué se
descartó y por qué**. El código está en [`momento2/`](../momento2/); acá está el
razonamiento que el código no puede contar.

Las dos primeras secciones responden lo que el entregable E8 pide explícitamente: qué
fuente semi-estructurada elegimos y por qué, y la estrategia de roles.

---

## A. La fuente semi-estructurada: siniestros del call center

**Decisión.** Exports semanales en JSON del call center de siniestros (mock, generado
por [`momento2/json/generar_siniestros_mock.py`](../momento2/json/generar_siniestros_mock.py)
con semilla fija — reproducible como todo lo demás). Cada archivo es un array de
siniestros; cada siniestro trae un array anidado `involved_parties` con las personas
involucradas.

**Por qué esta y no otra.** El enunciado permite inventar la fuente, pero pide que sea
*pertinente al dominio*. Evaluamos tres candidatas:

- **Telemetría GPS de los vehículos.** Volumen natural alto y anidamiento pobre (un
  punto GPS es plano). Descartada: el array anidado habría sido artificial.
- **Logs del portal de clientes.** Anidamiento real (eventos por sesión), pero no cruza
  con el modelo relacional más que por el cliente — y el modelo del Momento 1 no tiene
  tabla de clientes.
- **Siniestros (elegida).** Es el corazón operativo de una aseguradora que el modelo
  relacional del Momento 1 *no cubre* — exactamente el hueco que el enunciado describe
  ("casi siempre hay una segunda fuente, más desordenada, que también importa"). Cruza
  con el modelo por `policy_number` y `vin` reales, así que el DW puede responder
  preguntas nuevas (daño estimado por póliza). El array de involucrados es
  genuinamente variable (1–3 personas por siniestro) y trae PII de verdad (teléfono,
  dirección de terceros) que justifica la parte de gobernanza sin inventar nada.

Además, los exports **evolucionan**: los de la semana 2 agregan `email` y los de la 3
`assigned_workshop`. Eso no es decoración — es lo que demuestra que el camino
schema-on-read (`VARIANT` + `LATERAL FLATTEN`) absorbe cambios del proveedor sin tocar
una línea, mientras que el camino relacional (sección C) los detecta y frena. Los dos
comportamientos son correctos, cada uno en su dominio.

---

## B. Estrategia de roles: dos funciones de negocio, acceso por necesidad

**Decisión.** Además del rol de servicio (`TEAM5_LOADER`, solo para el pipeline), dos
roles de negocio con necesidades reales y **distintas**:

| | `ROLE_ANALISTA_SINIESTROS` | `ROLE_GERENTE_COMERCIAL` |
|---|---|---|
| Función | Gestiona casos: llama a los involucrados | Lee el negocio: pólizas, facturación, agregados |
| Schema `RAW` (relacional) | ✗ sin acceso | ✓ SELECT |
| `STG_SINIESTROS_FLATTENED` | ✓ SELECT | ✓ SELECT |
| `RAW_SINIESTROS` (VARIANT crudo) | ✗ | ✗ |
| Teléfono de involucrados | Completo | Solo prefijo (`+57-301-***-****`) |
| Dirección de involucrados | Completa | Oculta |

Tres decisiones dentro de la tabla merecen explicación:

- **Nadie de negocio lee el VARIANT crudo.** `RAW_SINIESTROS` contiene la PII sin
  procesar; si un rol pudiera consultarlo directo, la Masking Policy del staging sería
  decorativa. El crudo es del pipeline, no de las personas.
- **El default de la máscara es cerrado.** El `ELSE` de la política oculta el dato
  completo — incluso para `ACCOUNTADMIN`. Un rol nuevo nace sin acceso a la PII y hay
  que dárselo a propósito; administrar la plataforma no es lo mismo que necesitar el
  dato.
- **La protección vive en la columna, no en vistas.** La alternativa (una vista
  "segura" por rol) depende de que cada consumidor futuro se acuerde de usar la vista.
  La Masking Policy viaja pegada al dato: cualquier query, de cualquier herramienta,
  pasa por ella.

En cuenta Standard la política no se puede aplicar (`Unsupported feature`); el intento
y el error quedaron documentados en
[`evidencias_momento2/masking_intento_standard.md`](evidencias_momento2/masking_intento_standard.md),
como el enunciado contempla.

---

## C. Detección de schema drift en la ingesta relacional

**Decisión.** Antes de cargar cada tabla, `cargar.py` compara el header del CSV contra
las columnas del destino. Si el origen trae columnas nuevas, la carga de esa tabla se
aborta **antes de tocar nada**, con un mensaje que nombra las columnas y entrega el
`ALTER TABLE` listo para aplicar. Caso provocado y corregido:
[`evidencias_momento2/drift_provocado_y_corregido.md`](evidencias_momento2/drift_provocado_y_corregido.md).

¿Por qué frenar en vez de aplicar el `ALTER` automáticamente? Porque una columna nueva
en el origen es una *decisión* de alguien, y el DW no debería absorberla sin que un
humano la vea. El script deja el costo de decidir en 10 segundos (el DDL ya está
escrito); lo que no delega es la decisión. Es el contraste deliberado con el camino
JSON de la sección A, donde absorber cambios sin intervención es el objetivo.

---

## 1. Estrategia de idempotencia: borrar y recargar, dentro de una transacción

**Decisión.** Cada tabla se carga así, por tabla y de forma atómica:

```sql
BEGIN;
  DELETE FROM RAW.<tabla>;
  COPY INTO RAW.<tabla> FROM @STAGE_NEON FILES = ('<tabla>.csv.gz') ... FORCE = TRUE;
COMMIT;
```

Correr el pipeline dos veces seguidas deja exactamente el mismo estado que correrlo una
vez. Verificado: ejecuciones consecutivas dejan los conteos idénticos a los de Neon en
las 7 tablas (15 / 40 / 60 / 63 / 140 / 143 / 214), y la suite de validaciones pasa
completa después de cada una.

**Por qué.** El modelo de RutaSegura tiene ~675 filas en total y las tablas no traen una
columna confiable de "última modificación": `created_date` dice cuándo nació la fila, no
cuándo cambió. Sin esa columna no hay forma barata de saber qué cambió desde la última
carga, y reemplazar el contenido completo es correcto por construcción: el DW no puede
divergir del origen porque no conserva nada del origen anterior.

**Alternativas descartadas.**

- **`MERGE` (upsert por llave primaria).** Es la respuesta estándar cuando recargar todo
  es caro, y evita reescribir filas que no cambiaron. Se descartó por dos razones. La
  primera es que no resuelve los **borrados**: si una póliza se elimina en Neon, un
  `MERGE` la deja viva en el DW para siempre, y ninguna validación de conteo lo
  detectaría porque el conteo del destino sería mayor, no menor. La segunda es que la
  complejidad no se paga: `MERGE` sobre 7 tablas son 7 sentencias con lógica de
  emparejamiento que hay que mantener, para ahorrar segundos sobre 675 filas.
- **Carga incremental por lotes con deduplicación.** Cargar solo lo nuevo y desduplicar
  después. Tiene sentido cuando el volumen hace inviable releer la fuente completa —
  millones de filas, o una fuente que cobra por lectura. Aquí la extracción completa
  desde Neon tarda menos de dos segundos. Sería optimizar un costo que no existe, a
  cambio de una ventana de error nueva: si la deduplicación falla, aparecen duplicados
  silenciosos.
- **Apoyarse en el load metadata de Snowflake.** Snowflake recuerda por 64 días qué
  archivos ya cargó en cada tabla y por defecto los salta, lo que *parece* idempotencia
  gratis. Se descartó activamente (`FORCE = TRUE`) porque es una garantía frágil:
  depende del **nombre** del archivo, caduca sola a los 64 días, y si el CSV cambia de
  contenido conservando el nombre —que es exactamente lo que pasa en cada corrida— la
  carga se salta en silencio y el DW queda desactualizado sin que nada lo reporte.
  Preferimos una idempotencia que se lee en el código a una que depende de un
  comportamiento implícito del motor.

**Cuándo cambiaría esta decisión.** Si el modelo creciera a millones de filas, o si la
extracción desde Neon empezara a pesar, `MERGE` más una columna `updated_at` real y un
mecanismo de borrado lógico sería el siguiente paso. La decisión está atada al volumen,
no es una preferencia de estilo.

### Por qué `DELETE` y no `TRUNCATE`

`TRUNCATE` sería más barato: no recorre fila por fila. Pero en Snowflake `TRUNCATE` es
DDL, y **todo DDL hace commit implícito** de la transacción abierta. Es decir,
`TRUNCATE` + `COPY` no pueden ser atómicos: si el `COPY` falla, la tabla ya quedó vacía
y el DW pierde los datos de la corrida anterior sin haber ganado los nuevos — el peor de
los dos mundos.

`DELETE` es DML y sí participa de la transacción: un fallo hace `ROLLBACK` y la tabla
queda exactamente como estaba. Con este volumen la diferencia de costo es irrelevante y
la atomicidad vale más.

---

## 2. `ON_ERROR = ABORT_STATEMENT`

Se escribe explícitamente aunque coincida con el default de Snowflake, porque es una
decisión y no una omisión.

Si una sola fila no parsea, se aborta la carga de esa tabla y no entra nada. El dominio
es una aseguradora: una fila de `bill` mal parseada es plata mal contada, y una carga
parcial que nadie note es peor que una carga que falla ruidosamente. Además, como la
estrategia es borrar y recargar, reintentar es barato — no hay incentivo para "salvar lo
que se pueda".

- **`CONTINUE`** (ignora las filas malas y carga el resto) tendría sentido en ingesta de
  logs o telemetría de alto volumen, donde perder tres filas de un millón no cambia
  ninguna conclusión. Aquí significaría un DW con un subconjunto silencioso de las
  facturas.
- **`SKIP_FILE`** salta el archivo completo ante el primer error. Sirve cuando una tabla
  se carga desde muchos archivos particionados y se prefiere perder una partición antes
  que la carga entera. Aquí es un archivo por tabla, así que `SKIP_FILE` y
  `ABORT_STATEMENT` hacen lo mismo salvo por el mensaje de error.

---

## 3. `MATCH_BY_COLUMN_NAME` en vez de carga posicional

Las columnas del CSV se emparejan con las de la tabla **por nombre**, leyendo el header
(`PARSE_HEADER = TRUE` en el file format; es incompatible con `SKIP_HEADER`, hay que
elegir uno).

La alternativa clásica —`SKIP_HEADER = 1` y un `SELECT $1, $2, $3...`— funciona igual de
bien hasta el día en que alguien agrega una columna en medio del modelo: ahí el `COPY`
posicional **sigue "funcionando"** y mete cada dato en la columna equivocada, sin error.

No es un riesgo hipotético para este equipo: en el Momento 1 el modelo cambió tres veces
(`bill.payment_method`, `bill.paid_date`, la tabla `vehicle`).

Verificado de las dos formas: un CSV con las columnas **en orden invertido** carga
correctamente, y un CSV con una **columna de más** aborta la carga con
`Number of columns in file (8) does not match that of the corresponding table (7)`.

---

## 4. La capa RAW no tiene restricciones

Las tablas de `RAW` se crean sin `NOT NULL`, sin `PRIMARY KEY` y sin `FOREIGN KEY`,
aunque el origen en Postgres sí las tiene.

RAW es una landing zone: su trabajo es aceptar lo que venga para que se pueda
diagnosticar **después**. Si la restricción viviera aquí, un dato sucio haría fallar el
`COPY` sin dejar registro de qué llegó mal.

Y hay una razón práctica encima: las validaciones post-carga tienen que poder **detectar**
nulos en llaves primarias y huérfanos referenciales. Si la tabla los rechazara de
entrada, esas validaciones nunca podrían fallar — y una validación que no puede fallar no
valida nada.

(Snowflake, además, acepta la sintaxis de `PRIMARY KEY` y `FOREIGN KEY` pero **no las
hace cumplir**: son metadata informativa. La única restricción que sí impone es
`NOT NULL`. Declararlas daría una falsa sensación de integridad.)

---

## 5. Validaciones: consultas que devuelven lo que no debería existir

Cada validación es una consulta que selecciona las **filas que violan la regla**. Cero
filas devueltas = la regla se cumple.

Esa inversión es lo que las hace útiles: una validación escrita como "cuenta y compara"
solo dice que algo está mal; una que devuelve las filas ofensoras dice **qué** está mal, y
se puede pegar en un worksheet para investigar. Agregar una validación nueva es escribir
una consulta y sumarla a la lista, no escribir código.

Son 36 chequeos en seis familias: conteo origen vs. destino, llaves primarias no nulas,
llaves primarias únicas, integridad referencial, coherencia de fechas y una regla de
negocio (`status = 'Paid'` implica `balance = 0`).

La suite devuelve código de salida `1` cuando algo falla. Sin ese código, un job
automatizado daría "verde" sobre datos rotos.

**Evidencia de que fallan cuando deben fallar.** No es una afirmación teórica: durante el
desarrollo la extracción omitía la tabla `vehicle` (no aparece en los JSON semilla porque
la creó la migración `V202608081500`), y la suite lo detectó sin que nadie lo estuviera
buscando — 3 de 36 chequeos en rojo, señalando el mismo defecto desde tres ángulos
independientes: el conteo contra el origen (Neon 60 vs Snowflake 0), los 214 registros de
`vehicle_coverage` que quedaban huérfanos, y la tabla vacía. Corregida la extracción,
los 36 pasan.

Se reproduce en cualquier momento comentando una tabla en la lista `TABLAS` de
`extraer_neon_a_csv.py` y volviendo a correr el pipeline.

---

## 6. Autenticación por par de llaves RSA

El script se conecta a Snowflake con una llave privada RSA
(`SNOWFLAKE_PRIVATE_KEY_PATH`), no con usuario y contraseña.

No es preferencia: Snowflake **exige MFA con TOTP** para los inicios de sesión con
contraseña, y un segundo factor interactivo es incompatible con un proceso automatizado —
no hay nadie para teclear el código cuando el pipeline corre solo. `externalbrowser`
tampoco sirve: la cuenta no tiene un proveedor de identidad SAML configurado. El par de
llaves es el mecanismo que Snowflake documenta para cuentas de servicio.

La llave privada vive **fuera del repositorio** y solo se referencia por ruta, así que el
repo nunca contiene material criptográfico, ni siquiera por accidente en el historial de
commits.

---

## 7. Cada integrante usa su propia cuenta de Snowflake

Las cuentas de trial de Snowflake son inquilinos independientes: lo que un integrante
carga en la suya no existe en la de los demás, y no hay forma de compartir credenciales
que lo cambie.

Por eso **lo compartido es el código, no la cuenta**. Cada quien corre el mismo
`setup_snowflake.sql` versionado en su cuenta y obtiene la misma arquitectura. Que eso
funcione es la prueba de que el setup es reproducible — si hiciera falta que alguien
pasara algo por fuera del repositorio, no lo sería.

La única fuente compartida es la base de Neon del proyecto, que sí es una sola.

---
