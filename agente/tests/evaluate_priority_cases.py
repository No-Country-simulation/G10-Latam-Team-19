"""Casos ficticios adicionales del apoyo al Nodo 2; consume llamadas reales al LLM."""
import argparse
import json
import time
from pathlib import Path

from priority import evaluate_priority, load_config
from priority_support import evaluate_clinical_support

CASES = {
    "diagnostico_negado": {"diagnosis": "Se descarta infarto agudo de miocardio. Control de salud normal.", "study": None, "support": [None, "Rutina"], "final": "Rutina"},
    "antecedente_remoto": {"diagnosis": "Antecedente de infarto hace 10 años. Actualmente asintomático, control rutinario.", "study": None, "support": [None, "Rutina"], "final": "Rutina"},
    "estudio_sin_diagnostico": {"diagnosis": None, "study": "Radiografía de tórax", "support": [None], "final": "Rutina"},
    "diagnostico_incierto": {"diagnosis": "Diagnóstico por confirmar; estudio en curso.", "study": "Ecografía abdominal", "support": [None], "final": "Rutina"},
    "exacerbacion_activa": {"diagnosis": "Exacerbación activa del dolor basal crónico.", "study": None, "support": ["Prioritario"], "final": "Prioritario"},
    "diagnostico_urgente_actual": {"diagnosis": "Infarto agudo de miocardio actual.", "study": None, "support": ["Urgente"], "final": "Urgente"},
}


def run_case(name, case):
    # Contexto fijo del evaluador, no enviado al LLM. Aísla apoyo vs palabras clave.
    data = {
        "paciente": {"edad": 34, "unidad_edad": "años"},
        "diagnostico_principal": case["diagnosis"], "estudio_realizado": case["study"],
        "signos_vitales": {"temperatura": 36.7, "frecuencia_cardiaca": 82,
            "frecuencia_respiratoria": 17, "presion_arterial": "118/76", "saturacion_oxigeno": 99},
    }
    config = load_config()
    baseline = evaluate_priority(data, config)
    support = evaluate_clinical_support(case["diagnosis"], case["study"])
    level = support.nivel_prioridad.value if support.nivel_prioridad else None
    final = evaluate_priority(data, config, level)
    return {
        "caso": name, "entrada_llm": {"diagnostico_principal": case["diagnosis"], "estudio_realizado": case["study"]},
        "prioridad_apoyo": level, "justificacion": support.justificacion,
        "prioridad_reglas": baseline["nivel_prioridad"], "prioridad_final": final["nivel_prioridad"],
        "destino": final["destino_principal"], "apoyo_esperado": case["support"],
        "final_esperado": case["final"], "apoyo_cumple": level in case["support"],
        "final_cumple": final["nivel_prioridad"] == case["final"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--interval", type=float, default=20)
    args = parser.parse_args()
    if args.repetitions < 1 or args.interval < 0:
        parser.error("repetitions debe ser >=1 e interval >=0")
    results = []
    total = len(CASES) * args.repetitions
    for repetition in range(1, args.repetitions + 1):
        for name, case in CASES.items():
            try:
                result = run_case(name, case)
            except Exception as error:
                result = {"caso": name, "error_tipo": type(error).__name__, "causa_tipo": type(error.__cause__).__name__ if error.__cause__ else None}
            result["repeticion"] = repetition
            results.append(result)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(name, repetition, "apoyo:", result.get("prioridad_apoyo"), "final:", result.get("prioridad_final"), "error:", result.get("causa_tipo"), flush=True)
            if len(results) < total:
                time.sleep(args.interval)
    raise SystemExit(int(any("error_tipo" in r or not r["apoyo_cumple"] or not r["final_cumple"] for r in results)))


if __name__ == "__main__":
    main()
