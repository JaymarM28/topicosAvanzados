"""
Validaciones post-carga sobre la capa RAW de Snowflake.

Momento 2 del módulo "Tendencias emergentes en desarrollo de software" (SI6010-5979).
Equipo 5 · RutaSegura (Cobertura Vehicular).

Corre después de `carga/cargar.py` y responde una sola pregunta: **¿los datos que
quedaron en el DW son creíbles?** Un pipeline que termina sin excepciones no prueba
nada — puede haber cargado la mitad de las filas, o haberlas cargado dos veces, o
haber dejado facturas que apuntan a pólizas inexistentes. Eso es lo que se verifica
acá.

Uso:
    uv run validaciones/validar_carga.py
    uv run validaciones/validar_carga.py --sin-neon    # omite la comparación con el origen

Código de salida: 0 si todas las validaciones pasan, 1 si alguna falla. Ese código es
lo que permitiría que un pipeline de CI corte el despliegue cuando los datos están
mal — sin él, un job automatizado daría "verde" sobre datos rotos.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent

# conexiones.py vive en momento2/, un nivel arriba de este archivo. Se agrega esa
# carpeta al path para poder importarlo sin convertir el proyecto en un paquete
# instalable — que para dos scripts sería más ceremonia que beneficio.
sys.path.insert(0, str(RAIZ))
from conexiones import conectar_neon, conectar_snowflake  # noqa: E402

TABLAS = [
    "coverage",
    "policy",
    "vehicle",
    "policy_edit_log",
    "bill",
    "policy_coverage",
    "vehicle_coverage",
]

# Relaciones del modelo: (tabla_hija, columna_fk, tabla_padre, columna_pk).
# Salen del ERD de docs/dominio_de_negocio.md y de las foreign keys reales que
# declaran las migraciones del Momento 1.
RELACIONES = [
    ("bill", "policy_id", "policy", "id"),
    ("policy_edit_log", "policy_id", "policy", "id"),
    ("policy_coverage", "policy_id", "policy", "id"),
    ("policy_coverage", "coverage_id", "coverage", "id"),
    ("vehicle_coverage", "vehicle_id", "vehicle", "id"),
    ("vehicle_coverage", "coverage_id", "coverage", "id"),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("validaciones")


# ---------------------------------------------------------------------------
# El patrón: una validación es una query que devuelve lo que NO debería existir
# ---------------------------------------------------------------------------
#
# Todas las validaciones de este archivo (salvo la comparación con el origen, que
# necesita las dos bases a la vez) siguen la misma forma: una consulta que selecciona
# las filas que violan la regla. Cero filas = la regla se cumple.
#
# Esa inversión es lo que las hace útiles. Una validación escrita como "cuenta las
# filas correctas y compárala con lo esperado" solo dice que algo está mal; una que
# devuelve las filas ofensoras dice QUÉ está mal, y se puede pegar en un worksheet
# para investigar. Además, agregar una validación nueva es escribir una consulta y
# agregarla a la lista — no tocar código.

def construir_validaciones() -> list[dict]:
    """Arma la lista de validaciones. Función pura: se puede revisar sin conexión."""
    validaciones = []

    # 1. Llaves primarias sin valor. En Postgres `id` es PRIMARY KEY y por lo tanto
    #    NOT NULL, pero la capa RAW no replica esa restricción a propósito (ver
    #    carga/02_raw_tables.sql): si el CSV trajera una fila corrupta, se quiere que
    #    entre y quede detectada acá, no que reviente el COPY sin dejar rastro.
    for tabla in TABLAS:
        validaciones.append({
            "nombre": f"pk_no_nula[{tabla}]",
            "descripcion": f"{tabla}.id no debe ser NULL",
            "sql": f"SELECT * FROM RAW.{tabla.upper()} WHERE ID IS NULL",
        })

    # 2. Llaves primarias duplicadas. Es la validación que detectaría un fallo de
    #    idempotencia: si la segunda ejecución del pipeline insertara en vez de
    #    reemplazar, cada id aparecería dos veces y esta consulta lo mostraría.
    for tabla in TABLAS:
        validaciones.append({
            "nombre": f"pk_unica[{tabla}]",
            "descripcion": f"{tabla}.id no debe repetirse",
            "sql": (f"SELECT ID, COUNT(*) AS VECES FROM RAW.{tabla.upper()} "
                    f"GROUP BY ID HAVING COUNT(*) > 1"),
        })

    # 3. Integridad referencial. Snowflake acepta la sintaxis de FOREIGN KEY pero no
    #    la hace cumplir, así que la única forma de saber si hay huérfanos es
    #    buscarlos. Se ignoran los FK nulos: un NULL significa "sin relación", que es
    #    distinto de "apunta a algo que no existe".
    for hija, fk, padre, pk in RELACIONES:
        validaciones.append({
            "nombre": f"sin_huerfanos[{hija}.{fk}]",
            "descripcion": f"{hija}.{fk} debe existir en {padre}.{pk}",
            "sql": f"""
                SELECT h.ID, h.{fk.upper()}
                FROM RAW.{hija.upper()} h
                LEFT JOIN RAW.{padre.upper()} p ON h.{fk.upper()} = p.{pk.upper()}
                WHERE h.{fk.upper()} IS NOT NULL AND p.{pk.upper()} IS NULL
            """,
        })

    # 4. Coherencia de fechas. Una póliza que expira antes de entrar en vigencia no es
    #    un error de carga sino de datos, y es justamente el tipo de cosa que un
    #    reporte agregado esconde: el promedio de duración sale raro y nadie sabe por
    #    qué hasta que alguien busca los casos individuales.
    validaciones.append({
        "nombre": "vigencia_coherente[policy]",
        "descripcion": "policy_expire_date no debe ser anterior a policy_effective_date",
        "sql": """
            SELECT ID, POLICY_NUMBER, POLICY_EFFECTIVE_DATE, POLICY_EXPIRE_DATE
            FROM RAW.POLICY
            WHERE POLICY_EXPIRE_DATE < POLICY_EFFECTIVE_DATE
        """,
    })

    # 5. Regla de negocio del dominio. Una factura marcada como pagada con saldo
    #    pendiente es una contradicción: o el estado miente o el saldo no se
    #    actualizó. sp_register_payment (R__sp_register_payment.sql) escribe las dos
    #    columnas a la vez, así que si divergen algo pasó por fuera del procedimiento.
    validaciones.append({
        "nombre": "pagadas_sin_saldo[bill]",
        "descripcion": "una factura con status 'Paid' debe tener balance en cero",
        "sql": """
            SELECT ID, POLICY_ID, STATUS, BALANCE
            FROM RAW.BILL
            WHERE UPPER(STATUS) = 'PAID' AND COALESCE(BALANCE, 0) <> 0
        """,
    })

    # 6. Tablas vacías. Es la red de seguridad más tonta y la que más veces salva:
    #    detecta el caso en que el pipeline "corrió bien" pero no cargó nada.
    for tabla in TABLAS:
        validaciones.append({
            "nombre": f"no_vacia[{tabla}]",
            "descripcion": f"{tabla} debe tener al menos una fila",
            "sql": (f"SELECT 'tabla vacia' AS PROBLEMA "
                    f"WHERE (SELECT COUNT(*) FROM RAW.{tabla.upper()}) = 0"),
        })

    return validaciones


# ---------------------------------------------------------------------------
# Comparación origen vs. destino
# ---------------------------------------------------------------------------

def validar_conteos(cursor_sf, conexion_pg) -> list[dict]:
    """Compara el conteo de filas de cada tabla entre Neon y Snowflake.

    Es la única validación que necesita las dos bases a la vez, y la más importante:
    todas las demás verifican que lo que llegó sea coherente consigo mismo, pero solo
    esta verifica que haya llegado TODO. Un pipeline puede producir datos
    perfectamente consistentes y aun así haber perdido la mitad de las filas.
    """
    resultados = []
    with conexion_pg.cursor() as cursor_pg:
        for tabla in TABLAS:
            cursor_pg.execute(f"SELECT COUNT(*) FROM {tabla}")
            en_neon = cursor_pg.fetchone()[0]
            cursor_sf.execute(f"SELECT COUNT(*) FROM RAW.{tabla.upper()}")
            en_snowflake = cursor_sf.fetchone()[0]
            resultados.append({
                "nombre": f"conteo_origen_destino[{tabla}]",
                "ok": en_neon == en_snowflake,
                "detalle": f"Neon {en_neon} vs Snowflake {en_snowflake}",
            })
    return resultados


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------

def ejecutar(cursor_sf, validacion: dict) -> dict:
    """Corre una validación. Pasa si la consulta no devuelve ninguna fila."""
    cursor_sf.execute(validacion["sql"])
    ofensoras = cursor_sf.fetchall()
    detalle = "sin problemas"
    if ofensoras:
        muestra = ", ".join(str(f) for f in ofensoras[:3])
        detalle = f"{len(ofensoras)} fila(s) — ej.: {muestra}"
    return {"nombre": validacion["nombre"], "ok": not ofensoras, "detalle": detalle}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida la capa RAW de Snowflake después de una carga."
    )
    parser.add_argument("--sin-neon", action="store_true",
                        help="Omite la comparación de conteos contra el origen.")
    argumentos = parser.parse_args()

    load_dotenv(RAIZ / ".env")
    conexion_sf = conectar_snowflake()
    resultados = []
    try:
        with conexion_sf.cursor() as cursor_sf:
            if not argumentos.sin_neon:
                conexion_pg = conectar_neon()
                try:
                    resultados += validar_conteos(cursor_sf, conexion_pg)
                finally:
                    conexion_pg.close()
            resultados += [ejecutar(cursor_sf, v) for v in construir_validaciones()]
    finally:
        conexion_sf.close()

    fallidas = [r for r in resultados if not r["ok"]]

    print()
    print(f"{'validación':<38} {'estado':<8} detalle")
    print("-" * 100)
    for resultado in resultados:
        estado = "OK" if resultado["ok"] else "FALLA"
        print(f"{resultado['nombre']:<38} {estado:<8} {resultado['detalle']}")
    print("-" * 100)
    print(f"{len(resultados) - len(fallidas)}/{len(resultados)} validaciones pasaron.")
    print()

    if fallidas:
        log.error("Fallaron %s validación(es): %s",
                  len(fallidas), ", ".join(r["nombre"] for r in fallidas))
        return 1
    log.info("Todas las validaciones pasaron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
