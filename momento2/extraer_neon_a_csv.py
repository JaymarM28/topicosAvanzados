"""
Extracción — modelo propio (equipo 5) desde Neon hacia CSV planos.

Momento 2 del módulo "Tendencias emergentes en desarrollo de software" (SI6010-5979).

Extrae las 6 tablas del modelo transaccional de RutaSegura (Cobertura Vehicular,
diseñado en el Momento 1 — ver momento1/inyeccion_semilla_equipo_5.py) desde la branch
`dev` de Neon, y las escribe sin transformar en archivos CSV dentro de data_extraida/.

Esta es la mitad "extracción" del pipeline de ingesta hacia Snowflake. La carga
(creación del stage, `PUT` y `COPY INTO`) es un paso aparte, a cargo de otro
compañero del equipo — estos CSV quedan versionados en el repo como su insumo.

Uso:
    uv run extraer_neon_a_csv.py                  # extrae las 6 tablas
    uv run extraer_neon_a_csv.py --tabla policy    # solo una tabla

Variable de entorno requerida (ver momento2/.env.example):
    NEON_DEV_DATABASE_URL   Connection string de la branch `dev` de Neon.

Notas para quien arme el FILE FORMAT del COPY INTO, a partir de cómo se escriben
estos CSV:
    - Encoding UTF-8, delimitador coma, quoting mínimo (QUOTE_MINIMAL) — solo se
      encierran entre comillas los campos que traen coma, comilla o salto de línea
      (p. ej. policy.additional_info).
    - La primera fila es el encabezado con los nombres de columna -> usar
      SKIP_HEADER = 1.
    - Los NULL se escriben como campo vacío -> usar NULL_IF = ('').
    - Los booleanos se escriben como TRUE / FALSE en mayúscula.
    - Fechas en ISO (YYYY-MM-DD) y timestamps en ISO con espacio en vez de "T"
      (YYYY-MM-DD HH:MI:SS) — el formato por defecto de Snowflake para TIMESTAMP
      los reconoce sin configurar TIMESTAMP_FORMAT aparte.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent

import psycopg2
from dotenv import load_dotenv

TABLAS = [
    "coverage",
    "policy",
    "policy_edit_log",
    "bill",
    "policy_coverage",
    "vehicle_coverage",
]

CARPETA_SALIDA = RAIZ / "data_extraida"


def conectar_neon() -> psycopg2.extensions.connection:
    url = os.getenv("NEON_DEV_DATABASE_URL")
    if not url:
        print(
            "ERROR: falta NEON_DEV_DATABASE_URL.\n"
            "       Copia momento2/.env.example a momento2/.env y complétalo.",
            file=sys.stderr,
        )
        sys.exit(1)
    return psycopg2.connect(url)


def extraer_tabla(conexion, tabla: str) -> tuple[list[str], list[tuple]]:
    # SELECT * (no una lista explícita de columnas): la extracción no debe saber nada
    # del negocio, y así sobrevive sin cambios si el modelo evoluciona con una nueva
    # migración de Flyway — mismo principio que el script de la Sesión 4.
    with conexion.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {tabla}")
        columnas = [c.name for c in cursor.description]
        filas = cursor.fetchall()
    return columnas, filas


def formatear_valor(valor: Any) -> Any:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    return valor


def escribir_csv(tabla: str, columnas: list[str], filas: list[tuple]) -> Path:
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA_SALIDA / f"{tabla}.csv"
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo, quoting=csv.QUOTE_MINIMAL)
        escritor.writerow(columnas)
        for fila in filas:
            escritor.writerow(formatear_valor(valor) for valor in fila)
    return ruta


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrae el modelo propio (equipo 5) desde Neon hacia CSV planos."
    )
    parser.add_argument("--tabla", choices=TABLAS, help="Extraer solo esta tabla.")
    argumentos = parser.parse_args()

    load_dotenv()
    tablas = [argumentos.tabla] if argumentos.tabla else TABLAS

    conexion = conectar_neon()
    try:
        for tabla in tablas:
            print(f"Extrayendo {tabla} desde Neon...")
            columnas, filas = extraer_tabla(conexion, tabla)
            ruta = escribir_csv(tabla, columnas, filas)
            print(f"  {len(filas)} filas -> {ruta.relative_to(RAIZ.parent)}")
        return 0
    finally:
        conexion.close()


if __name__ == "__main__":
    sys.exit(main())
