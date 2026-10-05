# PRUEBA MANUAL: corre el grafo completo (con LLM real) contra los 5 casos
# de prueba del PDF de Datos compartido por Michelle.
# No es parte de la suite automática (usa LLM real, no es determinístico
# al 100% porque depende de lo que devuelva el proveedor) y consume llamadas.
#
# Uso:
#   python test_integration_real.py            -> corre los 5 casos
#   python test_integration_real.py caso_2      -> corre solo uno

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from graph import build_graph


CASOS = {
    "caso_1_rutina": {
        "descripcion": "Atención de Rutina (Confianza Alta)",
        "texto": (
            "Paciente femenino, 34 años. Acude para control de salud anual "
            "exigido por su empresa. Paciente asintomática, refiere sentirse "
            "bien. Signos vitales: Frecuencia cardíaca 72 lpm, frecuencia "
            "respiratoria 16 rpm, presión arterial 110/70 mmHg, SpO2 98%, "
            "temperatura 36.6°C. Diagnóstico (CIE-10 Z00.0): Control de salud "
            "normal. Tratamiento: Sin indicaciones farmacológicas."
        ),
        "esperado": {
            "nivel_prioridad": "Rutina",
            "destino_final": "Historia_Clinica_Electronica",
            "requires_human_review": False,
        },
    },
    "caso_2_emergencia": {
        "descripcion": "Emergencia Vital (Secuestro de Flujo)",
        "texto": (
            "Paciente masculino, 68 años. Ingresa en silla de ruedas por "
            "dolor opresivo en el pecho de 40 minutos de evolución, "
            "irradiado a mandíbula, con sudoración fría. Signos vitales: "
            "Frecuencia cardíaca 135 lpm, frecuencia respiratoria 32 rpm, "
            "presión arterial 85/50 mmHg, SpO2 88%, temperatura 35.8°C. "
            "Diagnóstico (CIE-10 I21.9): Infarto Agudo de Miocardio (IAM). "
            "Tratamiento: Traslado inmediato a reanimación."
        ),
        "esperado": {
            "nivel_prioridad": "Urgente",
            "destino_final": "Cola_Emergencia_Medica",
            "requires_human_review": False,
        },
    },
    "caso_3_alto_riesgo": {
        "descripcion": "Medicamento de Alto Riesgo (Desvío de Seguridad)",
        "texto": (
            "Paciente femenino, 75 años. Paciente en cuidados paliativos "
            "oncológicos. Refiere exacerbación del dolor basal crónico. "
            "Signos vitales: Frecuencia cardíaca 88 lpm, frecuencia "
            "respiratoria 18 rpm, presión arterial 130/80 mmHg, SpO2 96%, "
            "temperatura 36.8°C. Tratamiento prescripto: Fentanilo parche "
            "50 mcg/h, aplicación tópica continua, recambio cada 72 horas."
        ),
        "esperado": {
            # Conocido: priority.py no detecta "dolor severo activo" como
            # Prioritario (ver _pendiente_michelle en priority_config.json).
            # Lo que SÍ debe cumplirse siempre es el desvío por medicamento.
            "destino_final": "Auditoria_Autorizaciones",
            "requires_human_review": True,
        },
    },
    "caso_4_score_bajo": {
        "descripcion": "Violación de Seguridad por OCR Ilegible (Score Bajo)",
        "texto": (
            "Paciente masculino, 5 años. Diagnóstico: Faringoamigdalitis "
            "aguda. Tratamiento prescripto: Amoxicilina cada 8 horas por 7 "
            "días. [Nota: el médico no especificó la dosis en miligramos ni "
            "la vía de administración en la receta, o el escáner no logró "
            "leerlas]. Signos vitales: No registrados."
        ),
        "esperado": {
            "destino_final": "Cola_Revision_Humana",
            "requires_human_review": True,
        },
    },
    "caso_5_pediatrico": {
        "descripcion": "Pediátrico Seguro (Enrutamiento Directo)",
        "texto": (
            "Paciente masculino, 11 meses de edad. Madre consulta por "
            "síndrome febril agudo de 12 horas de evolución. Signos "
            "vitales: Frecuencia cardíaca 150 lpm, frecuencia respiratoria "
            "42 rpm, SpO2 97%, temperatura 38.9°C. Diagnóstico: Infección "
            "viral no especificada. Tratamiento prescripto: Paracetamol "
            "gotas 100mg/ml. Dosis: 15 gotas. Vía: Oral. Frecuencia: Cada "
            "6 horas en caso de fiebre."
        ),
        "esperado": {
            # Conocido: la regla de lactantes (>38.0°C -> Urgente) contradice
            # el "Prioritario" que espera este caso en el PDF (ver
            # _pendiente_michelle). Puede dar Urgente -> Cola_Emergencia_Medica
            # en vez de Farmacia_Hospitalaria hasta que Michelle lo resuelva.
            "destino_final": "Farmacia_Hospitalaria",
            "requires_human_review": False,
        },
    },
}


def run_case(nombre: str, caso: dict, graph) -> bool:
    print(f"\n{'=' * 70}")
    print(f"{nombre}: {caso['descripcion']}")
    print("=" * 70)

    result = graph.invoke({
        "document_id": f"TEST-{nombre}",
        "document_text": caso["texto"],
        "origin_channel": "Test_Integracion",
    })

    print("Score final:      ", result.get("final_confidence_score"))
    print("Nivel prioridad:  ", result.get("nivel_prioridad"))
    print("Destino final:    ", result.get("destino_final"))
    print("Auditoría humana: ", result.get("requires_human_review"))
    print("Justificación:    ", result.get("justificacion_enrutamiento"))

    ok = True
    for campo, valor_esperado in caso["esperado"].items():
        valor_real = result.get(campo)
        match = valor_real == valor_esperado
        ok = ok and match
        marca = "✅" if match else "❌"
        print(f"{marca} {campo}: esperado={valor_esperado!r} / real={valor_real!r}")

    return ok


def main():
    parser = argparse.ArgumentParser(
        description="Corre el grafo completo contra los casos de prueba de Datos."
    )
    parser.add_argument("caso", nargs="?", choices=CASOS.keys(), default=None)
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
    graph = build_graph()

    casos_a_correr = {args.caso: CASOS[args.caso]} if args.caso else CASOS

    resultados = {
        nombre: run_case(nombre, caso, graph)
        for nombre, caso in casos_a_correr.items()
    }

    print(f"\n{'=' * 70}")
    print("RESUMEN")
    print("=" * 70)
    for nombre, ok in resultados.items():
        print(f"{'✅' if ok else '❌'} {nombre}")

    if not all(resultados.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()