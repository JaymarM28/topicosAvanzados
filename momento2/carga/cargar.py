"""
Carga vía Internal Stage: CSV locales -> Snowflake, capa RAW.

Momento 2 del módulo "Tendencias emergentes en desarrollo de software" (SI6010-5979).
Equipo 5 · RutaSegura (Cobertura Vehicular).

Es la segunda mitad del pipeline de ingesta. La primera —extraer de Neon hacia CSV—
la hace `momento2/extraer_neon_a_csv.py`. Este script toma esos CSV y los mete en
Snowflake:

    PUT (sube y comprime) -> Internal Stage -> COPY INTO -> tabla en RAW

¿Por qué un script y no un .sql que se pegue en Snowsight? Porque `PUT` es un comando
de CLIENTE, no de servidor: sube un archivo desde el disco local, así que necesita un
proceso corriendo en esta máquina. Un Worksheet de Snowsight no tiene acceso al disco
y no puede ejecutarlo.

Uso:
    uv run carga/cargar.py                   # las 7 tablas
    uv run carga/cargar.py --tabla policy    # solo una
    uv run carga/cargar.py --listar-stage    # qué hay en el stage, sin cargar nada

Requisitos previos (en este orden):
    1. momento2/setup_snowflake.sql          base, schema RAW, warehouse, rol
    2. momento2/bitacora_carga.sql           schema CONTROL + BITACORA_CARGA
    3. momento2/carga/01_file_format_y_stage.sql
    4. momento2/carga/02_raw_tables.sql
    5. uv run extraer_neon_a_csv.py          para que existan los CSV

Variables de entorno: ver momento2/.env.example.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from snowflake.connector.errors import Error as SnowflakeError

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_CSV = RAIZ / "data_extraida"

# conexiones.py vive en momento2/, un nivel arriba de este archivo. Se agrega esa
# carpeta al path para poder importarlo sin convertir el proyecto en un paquete
# instalable — que para dos scripts sería más ceremonia que beneficio.
sys.path.insert(0, str(RAIZ))
from conexiones import conectar_snowflake  # noqa: E402

# Las 7 tablas del modelo, en orden de dependencia (padres antes que hijas). En RAW
# no hay foreign keys que lo exijan, pero el orden importa igual: si la carga se
# interrumpe a la mitad, un DW con las tablas padre cargadas y las hijas vacías es
# más fácil de interpretar que el revés.
#
# VEHICLE está en esta lista aunque `extraer_neon_a_csv.py` todavía no la extraiga:
# es una de las 7 tablas del modelo (la creó la migración V202608081500). Si su CSV
# no existe, este script lo reporta como fallo en la bitácora en vez de callárselo.
TABLAS = [
    "coverage",
    "policy",
    "vehicle",
    "policy_edit_log",
    "bill",
    "policy_coverage",
    "vehicle_coverage",
]

STAGE = "STAGE_NEON"
FORMATO = "FF_CSV_NEON"
TABLA_BITACORA = "CONTROL.BITACORA_CARGA"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("carga")


# ---------------------------------------------------------------------------
# PUT — subir el archivo al Internal Stage
# ---------------------------------------------------------------------------

def subir_al_stage(cursor, ruta_csv: Path) -> str:
    """Sube un CSV al stage, comprimido. Devuelve el nombre del archivo ya en el stage."""
    # Snowflake espera una URI file:// con barras normales, también en Windows.
    # as_posix() convierte C:\\Users\\... en C:/Users/..., y las comillas simples
    # protegen la ruta por si alguna carpeta tiene espacios.
    uri = f"file://{ruta_csv.as_posix()}"

    # AUTO_COMPRESS = TRUE: el archivo viaja gzipped y aterriza en el stage como
    # <tabla>.csv.gz. Se comprime en el cliente, así que lo que cruza la red es una
    # fracción del CSV plano, y el COPY INTO descomprime del lado del servidor sin
    # configuración extra (el FILE FORMAT tiene COMPRESSION = AUTO).
    #
    # OVERWRITE = TRUE: cada ejecución regenera los CSV desde Neon, así que el
    # archivo del stage siempre debe ser el de esta corrida. Sin esta opción
    # Snowflake conserva el archivo viejo y el COPY cargaría datos rancios — un
    # fallo silencioso de los peores, porque el pipeline reporta éxito.
    cursor.execute(f"PUT '{uri}' @{STAGE} AUTO_COMPRESS = TRUE OVERWRITE = TRUE")
    resultado = cursor.fetchone()
    # El resultado del PUT trae (source, target, source_size, target_size,
    # source_compression, target_compression, status, message).
    destino, tam_origen, tam_destino, estado = (
        resultado[1], resultado[2], resultado[3], resultado[6],
    )
    log.info("  PUT  %s -> @%s/%s (%s B -> %s B, %s)",
             ruta_csv.name, STAGE, destino, tam_origen, tam_destino, estado)
    return destino


# ---------------------------------------------------------------------------
# COPY INTO — cargar del stage a la tabla
# ---------------------------------------------------------------------------

def construir_copy(tabla: str, archivo_en_stage: str) -> str:
    """Arma el COPY INTO de una tabla. Función pura: se puede leer y revisar sin conexión."""
    # MATCH_BY_COLUMN_NAME empareja las columnas del CSV con las de la tabla POR
    # NOMBRE, leyendo el header (por eso el FILE FORMAT tiene PARSE_HEADER = TRUE).
    # La alternativa clásica —SKIP_HEADER = 1 y un SELECT $1, $2, $3... con las
    # columnas en orden— funciona igual de bien hasta el día en que alguien agrega
    # una columna en medio del modelo: ahí el COPY posicional sigue "funcionando" y
    # mete cada dato en la columna equivocada, sin error. Con emparejamiento por
    # nombre eso no puede pasar; y si el CSV trae una columna que la tabla no tiene,
    # el COPY falla ruidosamente — que es exactamente la detección de schema drift
    # que se quiere.
    #
    # CASE_INSENSITIVE porque el extractor escribe los headers en minúscula (como
    # los devuelve Postgres) y Snowflake guarda los identificadores en mayúscula.
    #
    # ON_ERROR = ABORT_STATEMENT: si una sola fila no parsea, se aborta la tabla
    # entera y no se carga nada. Es explícito aunque coincida con el default de
    # Snowflake, porque es una decisión, no una omisión. El dominio es una
    # aseguradora: una fila de BILL mal parseada es plata mal contada, y una carga
    # parcial que nadie note es peor que una carga que falla. Las alternativas se
    # descartaron a conciencia: CONTINUE (ignora las filas malas) tendría sentido en
    # logs de alto volumen donde perder tres filas de un millón da igual, y
    # SKIP_FILE en cargas particionadas en muchos archivos por tabla — aquí es un
    # archivo por tabla, así que SKIP_FILE y ABORT_STATEMENT harían lo mismo salvo
    # por el mensaje de error.
    #
    # FORCE = TRUE: Snowflake recuerda por 64 días qué archivos ya cargó en cada
    # tabla y por defecto los salta. Eso PARECE idempotencia gratis, pero es una
    # ilusión frágil: depende del nombre del archivo, caduca sola, y si el CSV
    # cambia de contenido conservando el nombre, la carga se salta en silencio y el
    # DW queda desactualizado sin que nada lo reporte. Preferimos desactivar ese
    # comportamiento implícito y hacer la idempotencia explícita y visible en el
    # código: DELETE + COPY dentro de una transacción (ver cargar_tabla).
    return f"""
        COPY INTO {tabla.upper()}
        FROM @{STAGE}
        FILES = ('{archivo_en_stage}')
        FILE_FORMAT = (FORMAT_NAME = {FORMATO})
        MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
        ON_ERROR = ABORT_STATEMENT
        FORCE = TRUE
    """


def cargar_tabla(cursor, tabla: str, archivo_en_stage: str) -> list[dict]:
    """Borra y recarga una tabla dentro de una transacción. Devuelve el reporte del COPY."""
    # ¿Por qué DELETE y no TRUNCATE? Porque en Snowflake TRUNCATE es DDL, y todo DDL
    # hace COMMIT implícito de la transacción abierta. O sea: TRUNCATE + COPY no se
    # pueden hacer atómicos — si el COPY falla, la tabla ya quedó vacía y el DW pierde
    # los datos de la corrida anterior sin haber ganado los nuevos. DELETE es DML y sí
    # participa de la transacción, así que un fallo hace ROLLBACK y la tabla queda
    # exactamente como estaba.
    #
    # En tablas grandes TRUNCATE sería mucho más barato (no toca fila por fila). Con
    # los miles de filas de RutaSegura la diferencia es irrelevante, y la atomicidad
    # vale más.
    cursor.execute("BEGIN")
    try:
        cursor.execute(f"DELETE FROM {tabla.upper()}")
        borradas = cursor.rowcount
        cursor.execute(construir_copy(tabla, archivo_en_stage))
        columnas = [c[0].lower() for c in cursor.description]
        reporte = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
        cursor.execute("COMMIT")
    except Exception:
        cursor.execute("ROLLBACK")
        raise
    cargadas = sum(fila.get("rows_loaded") or 0 for fila in reporte)
    log.info("  COPY %s · %s filas borradas, %s cargadas", tabla.upper(), borradas, cargadas)
    return reporte


# ---------------------------------------------------------------------------
# Bitácora
# ---------------------------------------------------------------------------

def registrar(cursor, tabla: str, archivo: str | None, filas: int | None,
              estado: str, error: str | None) -> None:
    """Escribe una fila en CONTROL.BITACORA_CARGA.

    Se hace desde Python y no con el patrón RESULT_SCAN(LAST_QUERY_ID()) de
    `registrar_bitacora.sql` por una razón concreta: RESULT_SCAN necesita que la
    query anterior HAYA PRODUCIDO un resultado. Cuando el COPY INTO falla como
    comando completo —el archivo no existe, el schema no coincide, ON_ERROR aborta—
    no hay resultado que leer, y ese es justamente el caso que más interesa registrar.
    El propio registrar_bitacora.sql lo anota como limitación pendiente. Atrapando la
    excepción acá, las ejecuciones fallidas quedan en la bitácora igual que las
    exitosas.
    """
    cursor.execute(
        f"""
        INSERT INTO {TABLA_BITACORA}
            (tabla_cargada, archivo, filas_cargadas, estado, mensaje_error)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (tabla.upper(), archivo, filas, estado, (error or None)),
    )


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------

def procesar_tabla(cursor, tabla: str) -> bool:
    """Sube y carga una tabla. Devuelve True si terminó en LOADED. Nunca lanza."""
    log.info("[%s]", tabla)
    ruta_csv = CARPETA_CSV / f"{tabla}.csv"

    if not ruta_csv.exists():
        mensaje = (f"No existe {ruta_csv.relative_to(RAIZ)}. "
                   f"Corre primero: uv run extraer_neon_a_csv.py")
        log.error("  %s", mensaje)
        registrar(cursor, tabla, None, 0, "LOAD_FAILED", mensaje)
        return False

    try:
        archivo = subir_al_stage(cursor, ruta_csv)
        reporte = cargar_tabla(cursor, tabla, archivo)
    except SnowflakeError as error:
        # str(error) del conector trae el mensaje de Snowflake completo, que suele
        # decir exactamente qué columna o qué fila rompió. Va entero a la bitácora:
        # el valor de la bitácora está en poder diagnosticar sin volver a correr nada.
        log.error("  FALLÓ: %s", error)
        registrar(cursor, tabla, f"{tabla}.csv.gz", 0, "LOAD_FAILED", str(error))
        return False

    if not reporte or "status" not in reporte[0]:
        # Pasa cuando el COPY no encuentra archivos que procesar. Snowflake no lo
        # considera un error, pero para el pipeline sí lo es: se pidió cargar y no
        # se cargó nada.
        mensaje = "El COPY INTO no procesó ningún archivo."
        log.error("  %s", mensaje)
        registrar(cursor, tabla, f"{tabla}.csv.gz", 0, "LOAD_FAILED", mensaje)
        return False

    todo_ok = True
    for fila in reporte:
        estado = fila.get("status", "LOAD_FAILED")
        registrar(cursor, tabla, fila.get("file"), fila.get("rows_loaded"),
                  estado, fila.get("first_error"))
        if estado != "LOADED":
            todo_ok = False
            log.warning("  estado %s · %s", estado, fila.get("first_error"))
    return todo_ok


def listar_stage(cursor) -> None:
    cursor.execute(f"LIST @{STAGE}")
    filas = cursor.fetchall()
    if not filas:
        log.info("El stage @%s está vacío.", STAGE)
        return
    log.info("Archivos en @%s:", STAGE)
    for nombre, tamano, _md5, ultima_modificacion in filas:
        log.info("  %-40s %10s B   %s", nombre, tamano, ultima_modificacion)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Carga los CSV extraídos de Neon hacia la capa RAW de Snowflake, "
                     "vía Internal Stage.")
    )
    parser.add_argument("--tabla", choices=TABLAS, help="Procesar solo esta tabla.")
    parser.add_argument("--listar-stage", action="store_true",
                        help="Mostrar el contenido del stage y salir, sin cargar nada.")
    argumentos = parser.parse_args()

    load_dotenv(RAIZ / ".env")
    conexion = conectar_snowflake()
    try:
        with conexion.cursor() as cursor:
            if argumentos.listar_stage:
                listar_stage(cursor)
                return 0

            tablas = [argumentos.tabla] if argumentos.tabla else TABLAS
            resultados = {tabla: procesar_tabla(cursor, tabla) for tabla in tablas}

        fallidas = [tabla for tabla, ok in resultados.items() if not ok]
        log.info("-" * 60)
        log.info("Resumen: %s/%s tablas cargadas.",
                 len(resultados) - len(fallidas), len(resultados))
        if fallidas:
            log.error("Fallaron: %s", ", ".join(fallidas))
            log.error("Detalle en %s (una fila por archivo procesado).", TABLA_BITACORA)
        # Código de salida distinto de cero cuando algo falló: es lo que permite que
        # un pipeline de CI detecte el fallo. Un script que reporta el error solo por
        # pantalla y devuelve 0 se ve bien en un log automatizado y no lo está.
        return 1 if fallidas else 0
    finally:
        conexion.close()


if __name__ == "__main__":
    sys.exit(main())
