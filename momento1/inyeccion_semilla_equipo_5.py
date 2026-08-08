"""
Inyección del estado base — Cobertura Vehicular (equipo 5).

Variante de `inyeccion_semilla.py` (Sesión 1) que carga un dominio de negocio distinto al
de Parch & Posey: pólizas de seguro vehicular, sus coberturas y su facturación. El modelo
transaccional sigue el diagrama ER `Vehicle-coverage-ERD-Example-Graphic-2.png`.

Este script construye el ESTADO BASE transaccional del equipo 5: crea el schema en una
base de datos PostgreSQL (Neon) y carga los datos semilla desde los archivos JSON de
`data/equipo_5/`.

Uso:
    uv run inyeccion_semilla_equipo_5.py                  # carga contra la branch dev
    uv run inyeccion_semilla_equipo_5.py --solo-verificar  # no escribe; solo reporta el estado
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

# Misma razón que en `inyeccion_semilla.py`: anclamos la búsqueda en la raíz del
# repositorio (marcada por `.git/` y `data/`) para que el script funcione igual sin
# importar desde qué directorio se invoque.
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
# `coverage` y `policy` no dependen de nadie; `policy_edit_log` y `bill` dependen de
# `policy`; `policy_coverage` depende de `policy` y `coverage`; `vehicle_coverage`
# depende de `coverage` (el ERD no modela una tabla `Vehicle`, así que `vehicle_id`
# queda como identificador suelto, tal como en el diagrama original).
ORDEN_DE_CARGA = [
    "coverage",
    "policy",
    "policy_edit_log",
    "bill",
    "policy_coverage",
    "vehicle_coverage",
]


# ---------------------------------------------------------------------------
# DDL — el schema del estado base
# ---------------------------------------------------------------------------

DDL = """
DROP TABLE IF EXISTS vehicle_coverage CASCADE;
DROP TABLE IF EXISTS policy_coverage CASCADE;
DROP TABLE IF EXISTS bill CASCADE;
DROP TABLE IF EXISTS policy_edit_log CASCADE;
DROP TABLE IF EXISTS policy CASCADE;
DROP TABLE IF EXISTS coverage CASCADE;

CREATE TABLE coverage (
    id                  INTEGER PRIMARY KEY,
    coverage_name       TEXT NOT NULL,
    coverage_group      TEXT,
    code                TEXT,
    is_policy_coverage  BOOLEAN NOT NULL DEFAULT FALSE,
    is_vehicle_coverage BOOLEAN NOT NULL DEFAULT FALSE,
    description         TEXT
);

CREATE TABLE policy (
    id                    INTEGER PRIMARY KEY,
    policy_number         TEXT NOT NULL,
    policy_effective_date DATE NOT NULL,
    policy_expire_date    DATE NOT NULL,
    payment_option        TEXT,
    total_amount          NUMERIC(10, 2),
    active                BOOLEAN NOT NULL DEFAULT TRUE,
    additional_info       TEXT,
    created_date          TIMESTAMP NOT NULL
);

CREATE TABLE policy_edit_log (
    id                INTEGER PRIMARY KEY,
    policy_id         INTEGER NOT NULL REFERENCES policy (id),
    edited_table_name TEXT NOT NULL,
    edited_date       TIMESTAMP NOT NULL,
    additional_info   TEXT,
    edited_by         TEXT NOT NULL
);

CREATE TABLE bill (
    id              INTEGER PRIMARY KEY,
    policy_id       INTEGER NOT NULL REFERENCES policy (id),
    due_date        DATE NOT NULL,
    minimum_payment NUMERIC(10, 2),
    created_date    TIMESTAMP NOT NULL,
    balance         NUMERIC(10, 2),
    status          TEXT
);

CREATE TABLE policy_coverage (
    id           INTEGER PRIMARY KEY,
    policy_id    INTEGER NOT NULL REFERENCES policy (id),
    coverage_id  INTEGER NOT NULL REFERENCES coverage (id),
    active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_date TIMESTAMP NOT NULL
);

CREATE TABLE vehicle_coverage (
    id           INTEGER PRIMARY KEY,
    vehicle_id   INTEGER NOT NULL,
    coverage_id  INTEGER NOT NULL REFERENCES coverage (id),
    active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_date TIMESTAMP NOT NULL
);

CREATE INDEX idx_policy_edit_log_policy_id    ON policy_edit_log (policy_id);
CREATE INDEX idx_bill_policy_id               ON bill (policy_id);
CREATE INDEX idx_policy_coverage_policy_id    ON policy_coverage (policy_id);
CREATE INDEX idx_policy_coverage_coverage_id  ON policy_coverage (coverage_id);
CREATE INDEX idx_vehicle_coverage_vehicle_id  ON vehicle_coverage (vehicle_id);
CREATE INDEX idx_vehicle_coverage_coverage_id ON vehicle_coverage (coverage_id);
"""


# ---------------------------------------------------------------------------
# Conversión de tipos
# ---------------------------------------------------------------------------
# Igual que en `inyeccion_semilla.py`: los JSON semilla traen todo como string, así que
# cada columna declara explícitamente cómo debe convertirse. Ver el comentario homólogo
# en el script original para la justificación completa.

def _timestamp(valor: str) -> datetime:
    return datetime.fromisoformat(valor[:26])


def _fecha(valor: str) -> date:
    return date.fromisoformat(valor[:10])


def _entero(valor: str | None) -> int | None:
    return int(valor) if valor not in (None, "") else None


def _decimal(valor: str | None) -> Decimal | None:
    return Decimal(valor) if valor not in (None, "") else None


def _texto(valor: str | None) -> str | None:
    return valor if valor not in (None, "") else None


def _booleano(valor: str | None) -> bool | None:
    if valor in (None, ""):
        return None
    return str(valor).strip().lower() in ("true", "1", "t", "yes")


# Cada entrada define: columnas de la tabla y cómo convertir cada campo del JSON.
ESPECIFICACIONES: dict[str, tuple[tuple[str, ...], object]] = {
    "coverage": (
        (
            "id", "coverage_name", "coverage_group", "code",
            "is_policy_coverage", "is_vehicle_coverage", "description",
        ),
        lambda r: (
            _entero(r["id"]),
            _texto(r["coverage_name"]),
            _texto(r["coverage_group"]),
            _texto(r["code"]),
            _booleano(r["is_policy_coverage"]),
            _booleano(r["is_vehicle_coverage"]),
            _texto(r["description"]),
        ),
    ),
    "policy": (
        (
            "id", "policy_number", "policy_effective_date", "policy_expire_date",
            "payment_option", "total_amount", "active", "additional_info", "created_date",
        ),
        lambda r: (
            _entero(r["id"]),
            _texto(r["policy_number"]),
            _fecha(r["policy_effective_date"]),
            _fecha(r["policy_expire_date"]),
            _texto(r["payment_option"]),
            _decimal(r["total_amount"]),
            _booleano(r["active"]),
            _texto(r["additional_info"]),
            _timestamp(r["created_date"]),
        ),
    ),
    "policy_edit_log": (
        ("id", "policy_id", "edited_table_name", "edited_date", "additional_info", "edited_by"),
        lambda r: (
            _entero(r["id"]),
            _entero(r["policy_id"]),
            _texto(r["edited_table_name"]),
            _timestamp(r["edited_date"]),
            _texto(r["additional_info"]),
            _texto(r["edited_by"]),
        ),
    ),
    "bill": (
        ("id", "policy_id", "due_date", "minimum_payment", "created_date", "balance", "status"),
        lambda r: (
            _entero(r["id"]),
            _entero(r["policy_id"]),
            _fecha(r["due_date"]),
            _decimal(r["minimum_payment"]),
            _timestamp(r["created_date"]),
            _decimal(r["balance"]),
            _texto(r["status"]),
        ),
    ),
    "policy_coverage": (
        ("id", "policy_id", "coverage_id", "active", "created_date"),
        lambda r: (
            _entero(r["id"]),
            _entero(r["policy_id"]),
            _entero(r["coverage_id"]),
            _booleano(r["active"]),
            _timestamp(r["created_date"]),
        ),
    ),
    "vehicle_coverage": (
        ("id", "vehicle_id", "coverage_id", "active", "created_date"),
        lambda r: (
            _entero(r["id"]),
            _entero(r["vehicle_id"]),
            _entero(r["coverage_id"]),
            _booleano(r["active"]),
            _timestamp(r["created_date"]),
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

    # Mismo guardrail que en el script original: nunca correr un DROP TABLE contra main.
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

            execute_values(
                cursor,
                f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES %s",
                filas,
                page_size=1000,
            )
            cargadas[tabla] = len(filas)
            print(f"  {tabla:<16} {len(filas):>6} filas")

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
    parser = argparse.ArgumentParser(
        description="Inyecta el estado base de Cobertura Vehicular (equipo 5)."
    )
    parser.add_argument(
        "--solo-verificar",
        action="store_true",
        help="No escribe nada; solo reporta qué tablas existen y cuántas filas tienen.",
    )
    argumentos = parser.parse_args()

    url = obtener_url_conexion()
    print(f"Datos semilla: {DIRECTORIO_DATOS}")

    conexion = psycopg2.connect(url)
    conexion.autocommit = False
    try:
        if argumentos.solo_verificar:
            conteos = verificar(conexion)
            print("\nEstado actual de la base:")
            for tabla, n in conteos.items():
                print(f"  {tabla:<16} {'(no existe)' if n < 0 else f'{n:>6} filas'}")
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
            print(f"  {'OK ' if ok else 'FAIL'} {tabla:<16} esperado={esperado:>6} real={real:>6}")

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
