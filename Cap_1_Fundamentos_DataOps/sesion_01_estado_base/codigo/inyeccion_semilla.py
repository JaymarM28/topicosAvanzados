"""
Inyección del estado base — Parch & Posey.

Sesión 1 del módulo "Tendencias emergentes en desarrollo de software" (SI6010-5979).

Este script construye el ESTADO BASE transaccional del curso: crea el schema de Parch &
Posey en una base de datos PostgreSQL (Neon) y carga los datos semilla desde los archivos
JSON de `data/`.

Es el punto de partida de todo el pipeline. A partir de la Sesión 2, ningún cambio de
schema se hará con un script como este: se hará con migraciones Flyway versionadas.

Uso:
    uv run inyeccion_semilla.py                 # carga contra la branch dev
    uv run inyeccion_semilla.py --solo-verificar  # no escribe; solo reporta el estado
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

# ¿Por qué buscamos la carpeta `data/` subiendo por el árbol en vez de escribir
# "../../../data"? Porque una ruta relativa depende de DÓNDE se invoca el script, no de
# dónde vive. Si un estudiante corre `uv run codigo/inyeccion_semilla.py` desde la carpeta
# de la sesión, la ruta fija se rompe. Anclar la búsqueda en la raíz del repositorio hace
# que el script funcione igual desde cualquier directorio — y eso es exactamente lo que
# necesitaremos en la Sesión 2, cuando sea GitHub Actions quien lo ejecute.
def encontrar_raiz_repositorio(inicio: Path) -> Path:
    for candidato in [inicio, *inicio.parents]:
        if (candidato / ".git").exists() and (candidato / "data").is_dir():
            return candidato
    raise RuntimeError(
        "No se encontró la raíz del repositorio (se esperaba un directorio con .git/ y data/). "
        f"Búsqueda iniciada en: {inicio}"
    )


RAIZ = encontrar_raiz_repositorio(Path(__file__).resolve().parent)
DIRECTORIO_DATOS = RAIZ / "data"

# El orden importa: las foreign keys obligan a insertar los padres antes que los hijos.
# `regions` no depende de nadie; `orders` depende de `accounts`, que depende de
# `sales_reps`, que depende de `regions`.
ORDEN_DE_CARGA = ["regions", "sales_reps", "accounts", "orders", "web_events"]


# ---------------------------------------------------------------------------
# DDL — el schema del estado base
# ---------------------------------------------------------------------------

DDL = """
DROP TABLE IF EXISTS web_events CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS sales_reps CASCADE;
DROP TABLE IF EXISTS regions CASCADE;

CREATE TABLE regions (
    id   SMALLINT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE sales_reps (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    region_id SMALLINT NOT NULL REFERENCES regions (id)
);

CREATE TABLE accounts (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    website      TEXT,
    lat          NUMERIC(11, 8),
    long         NUMERIC(11, 8),
    primary_poc  TEXT,
    sales_rep_id INTEGER NOT NULL REFERENCES sales_reps (id)
);

CREATE TABLE orders (
    id               INTEGER PRIMARY KEY,
    account_id       INTEGER NOT NULL REFERENCES accounts (id),
    occurred_at      TIMESTAMP NOT NULL,
    standard_qty     INTEGER,
    gloss_qty        INTEGER,
    poster_qty       INTEGER,
    total            INTEGER,
    standard_amt_usd NUMERIC(10, 2),
    gloss_amt_usd    NUMERIC(10, 2),
    poster_amt_usd   NUMERIC(10, 2),
    total_amt_usd    NUMERIC(10, 2)
);

CREATE TABLE web_events (
    id          INTEGER PRIMARY KEY,
    account_id  INTEGER NOT NULL REFERENCES accounts (id),
    occurred_at TIMESTAMP NOT NULL,
    channel     TEXT NOT NULL
);

CREATE INDEX idx_orders_account_id  ON orders (account_id);
CREATE INDEX idx_orders_occurred_at ON orders (occurred_at);
CREATE INDEX idx_web_events_account_id ON web_events (account_id);
"""


# ---------------------------------------------------------------------------
# Conversión de tipos
# ---------------------------------------------------------------------------

def _timestamp(valor: str) -> datetime:
    # ¿Por qué recortamos la cadena a 26 caracteres? Los JSON traen 7 dígitos de fracción
    # de segundo ("17:31:14.0000000"), herencia del export original en SQL Server.
    # PostgreSQL almacena microsegundos — 6 dígitos — y `datetime.fromisoformat` rechaza
    # los 7. Truncar aquí, de forma explícita y visible, es preferible a descubrir el
    # error a mitad de una carga de 6912 filas. Regla general de ingeniería de datos:
    # normaliza en el borde de entrada, no en el medio del pipeline.
    return datetime.fromisoformat(valor[:26])


def _entero(valor: str | None) -> int | None:
    return int(valor) if valor not in (None, "") else None


def _decimal(valor: str | None) -> Decimal | None:
    return Decimal(valor) if valor not in (None, "") else None


def _texto(valor: str | None) -> str | None:
    return valor if valor not in (None, "") else None


# Cada entrada define: columnas de la tabla y cómo convertir cada campo del JSON.
# ¿Por qué convertir explícitamente si el JSON ya trae los valores "listos"? Porque no lo
# están: TODO viene como string ("123", "613.77", "2015-10-06T..."). Si los insertáramos
# tal cual, PostgreSQL haría un cast implícito y el schema quedaría lleno de TEXT, o peor,
# fallaría en la fila 4000 con un valor mal formado. Declarar la conversión aquí convierte
# el schema en un contrato explícito: este es el tipo que esperamos, y si el dato no
# cumple, queremos enterarnos ahora.
ESPECIFICACIONES: dict[str, tuple[tuple[str, ...], object]] = {
    "regions": (
        ("id", "name"),
        lambda r: (_entero(r["id"]), _texto(r["name"])),
    ),
    "sales_reps": (
        ("id", "name", "region_id"),
        lambda r: (_entero(r["id"]), _texto(r["name"]), _entero(r["region_id"])),
    ),
    "accounts": (
        ("id", "name", "website", "lat", "long", "primary_poc", "sales_rep_id"),
        lambda r: (
            _entero(r["id"]),
            _texto(r["name"]),
            _texto(r["website"]),
            _decimal(r["lat"]),
            _decimal(r["long"]),
            _texto(r["primary_poc"]),
            _entero(r["sales_rep_id"]),
        ),
    ),
    "orders": (
        (
            "id", "account_id", "occurred_at", "standard_qty", "gloss_qty", "poster_qty",
            "total", "standard_amt_usd", "gloss_amt_usd", "poster_amt_usd", "total_amt_usd",
        ),
        lambda r: (
            _entero(r["id"]),
            _entero(r["account_id"]),
            _timestamp(r["occurred_at"]),
            _entero(r["standard_qty"]),
            _entero(r["gloss_qty"]),
            _entero(r["poster_qty"]),
            _entero(r["total"]),
            _decimal(r["standard_amt_usd"]),
            _decimal(r["gloss_amt_usd"]),
            _decimal(r["poster_amt_usd"]),
            _decimal(r["total_amt_usd"]),
        ),
    ),
    "web_events": (
        ("id", "account_id", "occurred_at", "channel"),
        lambda r: (
            _entero(r["id"]),
            _entero(r["account_id"]),
            _timestamp(r["occurred_at"]),
            _texto(r["channel"]),
        ),
    ),
}


# ---------------------------------------------------------------------------
# Lógica principal
# ---------------------------------------------------------------------------

def obtener_url_conexion() -> str:
    load_dotenv()
    url_dev = os.getenv("NEON_DEV_DATABASE_URL")
    url_main = os.getenv("NEON_MAIN_DATABASE_URL")

    if not url_dev:
        print(
            "ERROR: falta la variable NEON_DEV_DATABASE_URL.\n"
            "       Copia .env.example a .env y pega ahí el connection string de tu branch dev.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ¿Por qué el script se niega a correr si dev y main apuntan al mismo sitio? Porque en
    # DataOps la branch `main` es sagrada: representa el estado que el negocio consume.
    # Este script hace DROP TABLE. Ejecutarlo contra main destruiría producción sin dejar
    # rastro ni forma de revertir. Un guardrail que aborta es más barato que un incidente,
    # y el patrón se repetirá todo el curso: el entorno destino nunca es implícito.
    if url_main and url_dev.strip() == url_main.strip():
        print(
            "ERROR: NEON_DEV_DATABASE_URL y NEON_MAIN_DATABASE_URL apuntan a la misma base.\n"
            "       Este script hace DROP TABLE — nunca debe correr contra main.\n"
            "       Revisa que hayas copiado el connection string de la branch dev.",
            file=sys.stderr,
        )
        sys.exit(1)

    return url_dev


def cargar_json(tabla: str) -> list[dict]:
    ruta = DIRECTORIO_DATOS / f"{tabla}.json"
    if not ruta.exists():
        print(f"ERROR: no se encontró {ruta}", file=sys.stderr)
        sys.exit(1)
    with ruta.open(encoding="utf-8") as archivo:
        return json.load(archivo)


def inyectar(conexion) -> dict[str, int]:
    cargadas: dict[str, int] = {}
    with conexion.cursor() as cursor:
        print("Creando schema...")
        cursor.execute(DDL)

        for tabla in ORDEN_DE_CARGA:
            columnas, convertir = ESPECIFICACIONES[tabla]
            registros = cargar_json(tabla)
            filas = [convertir(registro) for registro in registros]

            # ¿Por qué execute_values y no un INSERT por fila dentro de un bucle? Neon es
            # serverless: cada sentencia es un round-trip de red, y 6912 round-trips
            # tardan minutos. execute_values agrupa las filas en pocas sentencias
            # multi-valor. La lección no es "usa esta función": es que en pipelines de
            # datos el costo dominante casi nunca es el CPU, es la latencia de red.
            execute_values(
                cursor,
                f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES %s",
                filas,
                page_size=1000,
            )
            cargadas[tabla] = len(filas)
            print(f"  {tabla:<12} {len(filas):>6} filas")

    return cargadas


def verificar(conexion) -> dict[str, int]:
    conteos: dict[str, int] = {}
    with conexion.cursor() as cursor:
        for tabla in ORDEN_DE_CARGA:
            cursor.execute(
                "SELECT to_regclass(%s) IS NOT NULL", (f"public.{tabla}",)
            )
            existe = cursor.fetchone()[0]
            if not existe:
                conteos[tabla] = -1
                continue
            cursor.execute(f"SELECT count(*) FROM {tabla}")
            conteos[tabla] = cursor.fetchone()[0]
    return conteos


def main() -> int:
    parser = argparse.ArgumentParser(description="Inyecta el estado base de Parch & Posey.")
    parser.add_argument(
        "--solo-verificar",
        action="store_true",
        help="No escribe nada; solo reporta qué tablas existen y cuántas filas tienen.",
    )
    argumentos = parser.parse_args()

    url = obtener_url_conexion()
    print(f"Datos semilla: {DIRECTORIO_DATOS}")

    # ¿Por qué abrimos la conexión sin autocommit y hacemos un único commit al final? Para
    # que la carga sea atómica: o queda el estado base completo, o no queda nada. Un
    # `DROP TABLE` exitoso seguido de un `INSERT` fallido dejaría la base vacía y al
    # estudiante sin punto de partida. En una transacción, ese escenario simplemente no
    # existe: el rollback devuelve todo al estado anterior.
    conexion = psycopg2.connect(url)
    conexion.autocommit = False
    try:
        if argumentos.solo_verificar:
            conteos = verificar(conexion)
            print("\nEstado actual de la base:")
            for tabla, n in conteos.items():
                print(f"  {tabla:<12} {'(no existe)' if n < 0 else f'{n:>6} filas'}")
            return 0

        cargadas = inyectar(conexion)
        conexion.commit()

        conteos = verificar(conexion)
        print("\nVerificación post-commit:")
        todo_ok = True
        for tabla in ORDEN_DE_CARGA:
            esperado, real = cargadas[tabla], conteos[tabla]
            ok = esperado == real
            todo_ok &= ok
            print(f"  {'OK ' if ok else 'FAIL'} {tabla:<12} esperado={esperado:>6} real={real:>6}")

        if not todo_ok:
            print("\nLa verificación falló: los conteos no coinciden.", file=sys.stderr)
            return 1

        print(f"\nEstado base listo. Total: {sum(conteos.values())} filas en {len(conteos)} tablas.")
        return 0

    except Exception as error:
        conexion.rollback()
        print(f"\nERROR — se revirtió la transacción completa: {error}", file=sys.stderr)
        return 1
    finally:
        conexion.close()


if __name__ == "__main__":
    sys.exit(main())
