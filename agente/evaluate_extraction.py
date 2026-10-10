"""Evalúa extracción real de los cinco casos ficticios; consume llamadas al proveedor."""
import argparse
import json
import re
from pathlib import Path

from nodes import extraction_node
from test_integration import CASOS

# Expectativas de datos explícitos, independientes de prioridad/enrutamiento.
EXPECTED = {
    "caso_1_rutina": {"paciente.edad": 34, "paciente.unidad_edad": "años", "paciente.sexo": "F", "cie10_sugerido": "Z00.0", "medicamentos": None},
    "caso_2_emergencia": {"paciente.edad": 68, "paciente.unidad_edad": "años", "paciente.sexo": "M", "cie10_sugerido": "I21.9", "medicamentos": None},
    "caso_3_alto_riesgo": {"paciente.edad": 75, "paciente.unidad_edad": "años", "paciente.sexo": "F", "cie10_sugerido": None, "medicamentos.0.nombre": "Fentanilo", "medicamentos.0.via": "Topica", "medicamentos.0.dosis": "50 mcg/h"},
    "caso_4_score_bajo": {"paciente.edad": 5, "paciente.unidad_edad": "años", "paciente.sexo": "M", "cie10_sugerido": None, "signos_vitales": None, "medicamentos.0.nombre": "Amoxicilina", "medicamentos.0.via": None, "medicamentos.0.dosis": None},
    "caso_5_pediatrico": {"paciente.edad": 11, "paciente.unidad_edad": "meses", "paciente.sexo": "M", "cie10_sugerido": None, "medicamentos.0.nombre": "Paracetamol", "medicamentos.0.via": "Oral", "medicamentos.0.dosis": "15 gotas"},
}
NAME_VARIANTS = {
    "caso_3_alto_riesgo": {"fentanilo", "fentanilo parche"},
    "caso_4_score_bajo": {"amoxicilina"},
    "caso_5_pediatrico": {"paracetamol", "paracetamol gotas"},
}
FREQUENCIES = {
    "caso_3_alto_riesgo": {"recambio cada 72 horas", "cada 72 horas"},
    "caso_4_score_bajo": {"cada 8 horas", "cada 8 horas por 7 días"},
    "caso_5_pediatrico": {"cada 6 horas en caso de fiebre"},
}

def normalize_text(value):
    return " ".join(value.casefold().split())

VITALS = {
    "caso_1_rutina": [36.6, 72, 16, "110/70", 98],
    "caso_2_emergencia": [35.8, 135, 32, "85/50", 88],
    "caso_3_alto_riesgo": [36.8, 88, 18, "130/80", 96],
    "caso_5_pediatrico": [38.9, 150, 42, None, 97],
}
for name, values in VITALS.items():
    for field, value in zip(["temperatura", "frecuencia_cardiaca", "frecuencia_respiratoria", "presion_arterial", "saturacion_oxigeno"], values):
        EXPECTED[name]["signos_vitales." + field] = value
for fields in EXPECTED.values():
    fields.update({"paciente.nombre": None, "paciente.documento_identidad": None, "medico_solicitante": None, "estudio_realizado": None})


def get_path(data, path):
    try:
        for part in path.split("."):
            data = data[int(part)] if isinstance(data, list) else data[part]
        return data
    except (KeyError, IndexError, TypeError, ValueError):
        return "<campo ausente>"


def compare(name, data):
    failures = []
    for path, expected in EXPECTED[name].items():
        actual = get_path(data, path)
        match = actual.strip().casefold() == expected.strip().casefold() if isinstance(actual, str) and isinstance(expected, str) else actual == expected
        if path == "medicamentos.0.nombre" and isinstance(actual, str):
            match = normalize_text(actual) in NAME_VARIANTS[name]
        if path == "medicamentos.0.dosis" and isinstance(actual, str) and isinstance(expected, str):
            match = re.sub(r"\s+", "", actual.casefold()) == re.sub(r"\s+", "", expected.casefold())
        if not match:
            failures.append({"campo": path, "esperado": expected, "obtenido": actual})
    if name in FREQUENCIES:
        actual = get_path(data, "medicamentos.0.frecuencia_diaria")
        if not isinstance(actual, str) or normalize_text(actual) not in FREQUENCIES[name]:
            failures.append({"campo": "medicamentos.0.frecuencia_diaria", "esperado": sorted(FREQUENCIES[name]), "obtenido": actual})
    expected_count = 1 if name in ("caso_3_alto_riesgo", "caso_4_score_bajo", "caso_5_pediatrico") else 0
    if len(data.get("medicamentos") or []) != expected_count:
        failures.append({"campo": "cantidad_medicamentos", "esperado": expected_count, "obtenido": len(data.get("medicamentos") or [])})
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("caso", nargs="?", choices=CASOS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = []
    for name in ([args.caso] if args.caso else CASOS):
        try:
            result = extraction_node({"document_text": CASOS[name]["texto"]})
            data = result["extracted_data"].model_dump(mode="json")
            failures = compare(name, data)
            reports.append({"caso": name, "datos": data, "diferencias": failures,
                            "score": result["extraction_confidence_score"],
                            "revision_manual": ["diagnostico_principal"]})
            print(name, "OK en campos comparados" if not failures else f"{len(failures)} diferencias")
        except Exception as error:
            reports.append({"caso": name, "error_tipo": type(error).__name__, "causa_tipo": type(error.__cause__).__name__ if error.__cause__ else None})
            print(name, "ERROR", type(error).__name__)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    raise SystemExit(int(any(r.get("diferencias") or "error_tipo" in r for r in reports)))


if __name__ == "__main__":
    main()
