"""
Conexiones a Neon y a Snowflake, compartidas por los scripts del Momento 2.

Vive en la raíz de momento2/ y no dentro de carga/ o validaciones/ porque lo usan
los dos: si cada script tuviera su propia copia, arreglar un detalle de
autenticación en uno dejaría el otro roto sin que nada lo avise.

Toda la configuración entra por variables de entorno (ver .env.example). Este
módulo no contiene ninguna credencial.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import psycopg2
import snowflake.connector

RAIZ = Path(__file__).resolve().parent

log = logging.getLogger("conexiones")


def env(nombre: str, obligatoria: bool = True, defecto: str | None = None) -> str | None:
    """Lee una variable de entorno y le quita los espacios de sobra.

    El .strip() no es paranoia: un `SNOWFLAKE_USER=DAV ` con un espacio al final
    —que es facilísimo de dejar al copiar y pegar— produce un error de
    autenticación que no menciona el espacio por ningún lado.
    """
    valor = os.environ.get(nombre, defecto)
    valor = valor.strip() if isinstance(valor, str) else valor
    if obligatoria and not valor:
        log.error("Falta la variable de entorno %s. Revisa momento2/.env", nombre)
        sys.exit(1)
    return valor


def conectar_neon() -> psycopg2.extensions.connection:
    """Conecta a la branch `dev` de Neon: la base transaccional del proyecto."""
    return psycopg2.connect(env("NEON_DEV_DATABASE_URL"))


def conectar_snowflake(rol: str | None = None) -> snowflake.connector.SnowflakeConnection:
    """Conecta a Snowflake. `rol` permite sobreescribir SNOWFLAKE_ROLE puntualmente."""
    # Warehouse, base, schema y rol se fijan explícitamente en la conexión en vez de
    # depender de los defaults del usuario. Si se dejaran implícitos, el script
    # funcionaría en la cuenta de quien los configuró a mano y fallaría en la de sus
    # compañeros de equipo, sin que cambie una sola línea de código.
    parametros = {
        "account": env("SNOWFLAKE_ACCOUNT"),
        "user": env("SNOWFLAKE_USER"),
        "warehouse": env("SNOWFLAKE_WAREHOUSE"),
        "database": env("SNOWFLAKE_DATABASE"),
        "schema": env("SNOWFLAKE_SCHEMA", obligatoria=False, defecto="RAW"),
        "role": rol or env("SNOWFLAKE_ROLE", obligatoria=False),
    }

    # Autenticación por par de llaves si hay una llave privada configurada; si no,
    # se cae al mecanismo que diga SNOWFLAKE_AUTHENTICATOR.
    #
    # ¿Por qué par de llaves es lo correcto acá y no usuario+contraseña? Porque
    # Snowflake exige MFA para los inicios de sesión con contraseña, y un segundo
    # factor interactivo es incompatible con un proceso automatizado: no hay nadie
    # para teclear el código cuando el pipeline corre solo. Es la misma razón por la
    # que Snowflake documenta el par de llaves como el mecanismo para cuentas de
    # servicio. El beneficio secundario es que la demo en vivo no depende de sacar
    # un TOTP del celular a tiempo.
    #
    # La llave privada vive FUERA del repositorio y solo se referencia por ruta, así
    # que el repo nunca contiene material criptográfico — ni siquiera por accidente
    # en el historial de commits.
    ruta_llave = env("SNOWFLAKE_PRIVATE_KEY_PATH", obligatoria=False)
    if ruta_llave:
        if not Path(ruta_llave).exists():
            log.error("SNOWFLAKE_PRIVATE_KEY_PATH apunta a %s, que no existe.", ruta_llave)
            sys.exit(1)
        parametros["authenticator"] = "SNOWFLAKE_JWT"
        parametros["private_key_file"] = ruta_llave
        # Solo si la llave se generó cifrada (openssl pkcs8 sin -nocrypt).
        passphrase = env("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", obligatoria=False)
        if passphrase:
            parametros["private_key_file_pwd"] = passphrase
        metodo = "par de llaves"
    else:
        autenticador = env("SNOWFLAKE_AUTHENTICATOR", obligatoria=False, defecto="snowflake")
        parametros["authenticator"] = autenticador
        if autenticador != "externalbrowser":
            parametros["password"] = env("SNOWFLAKE_PASSWORD")
        metodo = autenticador

    log.info(
        "Conectando a Snowflake · cuenta=%s usuario=%s rol=%s base=%s.%s auth=%s",
        parametros["account"], parametros["user"], parametros["role"],
        parametros["database"], parametros["schema"], metodo,
    )
    return snowflake.connector.connect(**parametros)
