"""
Genera el mock de la fuente semi-estructurada del Momento 2: siniestros
(claims) reportados por el TPA (Third-Party Administrator) que gestiona las
reparaciones de RutaSegura.

Por qué esta fuente y no otra: el modelo relacional del Momento 1 (policy,
coverage, bill, vehicle...) no tiene NADA de siniestralidad — solo pólizas,
coberturas y facturación. En la vida real, la liquidación de un siniestro la
hace un tercero (un TPA o el propio taller) y llega como un export, no como
una tabla más de la base transaccional. Es exactamente el caso de uso que pide
el Momento 2: una segunda fuente, más desordenada, que también importa.

Cada claim trae un array anidado real (`repair_line_items`, uno por parte
dañada) que justifica LATERAL FLATTEN — no es una tabla plana disfrazada de
JSON. Algunos claims traen el array vacío (siniestro reportado, aún sin
diagnóstico del taller) y algunos adjusters no traen `agency` (freelance) —
a propósito, para que el FLATTEN tenga que lidiar con claves ausentes/arrays
vacíos, no solo con el camino feliz.

Salida: un archivo JSON por mes (array con STRIP_OUTER_ARRAY en mente, igual
que el patrón de la Sesión 5), en esta misma carpeta. Referencia policy_number
reales de momento2/data_extraida/policy.csv para que el dato se sienta anclado
al dominio del equipo, no inventado desde cero.

Uso:
    python3 generar_siniestros.py
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
POLICY_CSV = RAIZ.parent / "data_extraida" / "policy.csv"
SALIDA = RAIZ

random.seed(20260821)  # reproducible: correr el script dos veces da el mismo mock

# Los nombres de taller son razón social real (no un identificador del schema),
# se dejan tal cual — igual que "RutaSegura" no se tradujo al nombrar el proyecto.
TALLERES = [
    ("Taller Andino Motors", "andino.motors@tpa-siniestros.co"),
    ("Carrocerías del Valle", "contacto@carroceriasdelvalle.co"),
    ("AutoRescate 24/7", "operaciones@autorescate.co"),
    (None, "freelance.perito@gmail.com"),  # perito independiente, sin agency
]

# Claves y vocabulario controlado en inglés a propósito: el modelo relacional
# del Momento 1 (policy_number, total_amount, is_vehicle_coverage...) nombra
# todo en inglés, solo los comentarios y la documentación están en español. El
# JSON sigue esa misma convención para no introducir una fuente con un
# estándar de nombres distinto al resto del schema.
CLAIM_TYPES = ["collision", "partial_theft", "vandalism", "weather", "roadside_assistance"]

PARTS = [
    ("Front bumper", 350, 900),
    ("Rear bumper", 300, 850),
    ("Front left door", 400, 1100),
    ("Right side mirror", 60, 180),
    ("Windshield", 250, 700),
    ("Front right headlight", 150, 420),
    ("Rear fender", 200, 600),
    ("Front right tire", 120, 300),
    ("Hood", 500, 1400),
]

DAMAGE_SEVERITIES = ["minor", "moderate", "severe"]

STATUSES = ["under_review", "approved", "denied", "paid"]


def cargar_policy_numbers() -> list[str]:
    with POLICY_CSV.open(newline="", encoding="utf-8") as f:
        return [fila["policy_number"] for fila in csv.DictReader(f)]


def generar_line_items(forzar_vacio: bool = False) -> list[dict]:
    # Algunos claims llegan sin diagnóstico todavía (recién reportados): el
    # array queda vacío a propósito, para que el FLATTEN también se pruebe
    # contra el caso "cero filas hijas", no solo contra el camino feliz.
    # `forzar_vacio` garantiza al menos un caso real por archivo — dejarlo
    # solo al azar (~12%) podía dar una corrida sin ningún caso que mostrar.
    if forzar_vacio or random.random() < 0.12:
        return []
    cuantas_partes = random.randint(1, 3)
    partes = random.sample(PARTS, cuantas_partes)
    return [
        {
            "part": nombre,
            "damage_severity": random.choice(DAMAGE_SEVERITIES),
            "labor_hours": round(random.uniform(0.5, 6.0), 1),
            "estimated_cost": round(random.uniform(minimo, maximo), 2),
        }
        for nombre, minimo, maximo in partes
    ]


def generar_claim(numero: int, policy_number: str, anio: int, mes: int,
                   forzar_vacio: bool = False) -> dict:
    dia = random.randint(1, 27)
    taller, email_perito = random.choice(TALLERES)
    line_items = generar_line_items(forzar_vacio)
    costo_total = round(sum(item["estimated_cost"] for item in line_items), 2)

    adjuster = {"email": email_perito}
    if taller:  # los peritos freelance no tienen agency — clave ausente a propósito
        adjuster["agency"] = taller

    claim = {
        "claim_id": f"CLM-{anio}-{numero:06d}",
        "policy_number": policy_number,
        "reported_at": f"{anio:04d}-{mes:02d}-{dia:02d}T{random.randint(6,20):02d}:{random.randint(0,59):02d}:00Z",
        "claim_type": random.choice(CLAIM_TYPES),
        "status": random.choice(STATUSES) if line_items else "under_review",
        "adjuster": adjuster,
        "estimated_total_cost": costo_total,
        "repair_line_items": line_items,
    }
    return claim


def generar_mes(anio: int, mes: int, cantidad: int, policy_numbers: list[str],
                 contador_inicial: int) -> tuple[list[dict], int]:
    claims = []
    contador = contador_inicial
    for indice in range(cantidad):
        contador += 1
        policy_number = random.choice(policy_numbers)
        # El primer claim de cada archivo siempre queda sin diagnóstico (array
        # vacío) — así el caso está garantizado y no depende de la suerte del
        # random al regenerar el mock.
        claims.append(generar_claim(contador, policy_number, anio, mes,
                                     forzar_vacio=(indice == 0)))
    return claims, contador


def main() -> None:
    policy_numbers = cargar_policy_numbers()
    SALIDA.mkdir(exist_ok=True)

    lotes = [(2026, 6, 8), (2026, 7, 9), (2026, 8, 7)]  # (año, mes, cuantos claims)
    contador = 0
    for anio, mes, cantidad in lotes:
        claims, contador = generar_mes(anio, mes, cantidad, policy_numbers, contador)
        ruta = SALIDA / f"siniestros_{anio:04d}-{mes:02d}.json"
        ruta.write_text(json.dumps(claims, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{ruta.relative_to(RAIZ.parent.parent)} · {len(claims)} claims")

    print(f"\nTotal: {contador} claims en {len(lotes)} archivos.")


if __name__ == "__main__":
    main()
