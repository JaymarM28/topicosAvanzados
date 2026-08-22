"""
Genera la fuente semi-estructurada mock del equipo 5: exports del call center de
siniestros de RutaSegura.

Momento 2 — punto 3 del alcance (ingesta semi-estructurada). La fuente es INVENTADA
a propósito: el enunciado lo permite explícitamente ("inventada por el equipo si hace
falta"), y el dominio la pide sola — una aseguradora vehicular sin siniestros no es
una aseguradora. Simula lo que un proveedor de call center exportaría cada semana:
JSON con estructura variable, no filas de una tabla.

Por qué esta fuente y no otra:
  - Referencia el modelo relacional del Momento 1 (policy_number y vin reales), así
    que el DW puede cruzar ambos mundos — eso es lo que hace "pertinente al dominio"
    a la fuente, como pide la rúbrica.
  - Trae un array anidado real (involved_parties: las personas involucradas en cada
    siniestro) que obliga a usar LATERAL FLATTEN — un siniestro tiene 1..3
    involucrados, no un número fijo.
  - Trae PII de verdad (teléfono y dirección de terceros) que justifica la Masking
    Policy de la parte de gobernanza.
  - Los exports evolucionan: los archivos de semanas posteriores traen campos que el
    primero no tiene (email del involucrado, taller asignado) — el mismo
    schema-on-read que se vio en clase con social_media_handle.

Determinista (semilla fija): correrlo dos veces produce exactamente los mismos
archivos, así que el mock es reproducible como todo lo demás.

Uso:
    uv run json/generar_siniestros_mock.py
Escribe 3 archivos JSON (uno por semana) en json/datos_mock/.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = Path(__file__).resolve().parent / "datos_mock"

rng = random.Random(5)  # equipo 5

NOMBRES = [
    "Carlos Restrepo", "María Fernanda López", "Andrés Gutiérrez", "Luisa Cárdenas",
    "Jorge Iván Mejía", "Paula Andrea Ríos", "Santiago Herrera", "Valentina Ortiz",
    "Ricardo Palacio", "Camila Zapata", "Felipe Arango", "Daniela Montoya",
]
DIRECCIONES = [
    "Cra 43A #18-95, Medellín", "Cl 10 #42-28, El Poblado", "Av 33 #74-12, Laureles",
    "Cra 80 #45-60, Robledo", "Cl 51 #70-15, Centro", "Cra 65 #30-44, Belén",
    "Diag 75B #2A-120, Envigado", "Cl 37 Sur #45-21, Sabaneta",
]
TIPOS = ["collision", "theft", "vandalism", "roadside_assist", "glass_damage"]
ROLES_PARTE = ["driver", "third_party", "passenger", "witness"]
TALLERES = ["Taller Andino S.A.S.", "AutoExpertos Medellín", "CDA La Estrella"]


def llaves_reales() -> tuple[list[str], list[str]]:
    """Lee policy_number y vin reales de la extracción, para que el JSON cruce
    con el modelo relacional (y las validaciones puedan verificarlo)."""
    with (RAIZ / "data_extraida" / "policy.csv").open(encoding="utf-8") as f:
        polizas = [fila["policy_number"] for fila in csv.DictReader(f)]
    with (RAIZ / "data_extraida" / "vehicle.csv").open(encoding="utf-8") as f:
        vins = [fila["vin"] for fila in csv.DictReader(f)]
    return polizas, vins


def telefono() -> str:
    return f"+57-30{rng.randint(0, 4)}-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}"


def parte(semana: int) -> dict:
    p = {
        "name": rng.choice(NOMBRES),
        "role": rng.choice(ROLES_PARTE),
        "phone": telefono(),
        "personal_address": rng.choice(DIRECCIONES),
    }
    # Los exports de la semana 2 en adelante agregan el email — el campo NO existe en
    # la semana 1. Es el mismo drift semi-estructurado del taller de clase: la query
    # con :email debe devolver NULL para las filas viejas, no fallar.
    if semana >= 2 and rng.random() < 0.7:
        nombre_corto = p["name"].split()[0].lower()
        p["email"] = f"{nombre_corto}{rng.randint(1, 99)}@example.com"
    return p


def siniestro(numero: int, semana: int, polizas: list[str], vins: list[str]) -> dict:
    s = {
        "claim_id": f"CLM-2026-{numero:04d}",
        "policy_number": rng.choice(polizas),
        "vin": rng.choice(vins),
        "reported_at": f"2026-08-{7 + semana * 7:02d}T{rng.randint(7, 20):02d}:{rng.randint(0, 59):02d}:00",
        "incident_type": rng.choice(TIPOS),
        "estimated_damage_usd": round(rng.uniform(180, 8500), 2),
        "involved_parties": [parte(semana) for _ in range(rng.randint(1, 3))],
    }
    # Y la semana 3 agrega el taller asignado — segundo caso de evolución del export.
    if semana >= 3:
        s["assigned_workshop"] = rng.choice(TALLERES)
    return s


def main() -> None:
    polizas, vins = llaves_reales()
    SALIDA.mkdir(exist_ok=True)
    numero = 0
    for semana in (1, 2, 3):
        lote = []
        for _ in range(rng.randint(3, 5)):
            numero += 1
            lote.append(siniestro(numero, semana, polizas, vins))
        ruta = SALIDA / f"siniestros_semana_{semana}.json"
        # El archivo es un ARRAY de objetos — igual que los exports del curso. Por eso
        # el FILE FORMAT necesita STRIP_OUTER_ARRAY = TRUE: sin él, cada archivo
        # cargaría como una sola fila VARIANT gigante.
        ruta.write_text(json.dumps(lote, indent=2, ensure_ascii=False), encoding="utf-8")
        total_partes = sum(len(s["involved_parties"]) for s in lote)
        print(f"{ruta.name}: {len(lote)} siniestros, {total_partes} involucrados")


if __name__ == "__main__":
    main()
