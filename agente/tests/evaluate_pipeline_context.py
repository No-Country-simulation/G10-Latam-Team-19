"""Cuatro casos ficticios de contexto por el grafo completo; consume llamadas reales."""
import argparse
import json
import re
import time
from pathlib import Path
from graph import build_graph

BASE = "INFORME CLÍNICO FICTICIO PARA VALIDACIÓN. Paciente femenino, 34 años. "
NORMAL = "Signos vitales: FC 82 lpm, FR 17 rpm, PA 118/76 mmHg, SpO2 99%, temperatura 36.7°C. Sin indicaciones farmacológicas."
CRITICAL = "Signos vitales: FC 82 lpm, FR 17 rpm, PA 118/76 mmHg, SpO2 88%, temperatura 36.7°C. Sin indicaciones farmacológicas."
CASES = {
    "infarto_descartado": {"text": BASE + "Se descarta infarto agudo de miocardio. Diagnóstico principal: control de salud normal. " + NORMAL, "priority": "Rutina", "destination": "Historia_Clinica_Electronica", "diagnosis_terms": ["control"], "spo2": 99},
    "antecedente_remoto": {"text": BASE + "Antecedente de infarto hace 10 años. Actualmente asintomática. Diagnóstico principal: control de salud normal. " + NORMAL, "priority": "Rutina", "destination": "Historia_Clinica_Electronica", "diagnosis_terms": ["control"], "spo2": 99},
    "antecedente_y_infarto_actual": {"text": BASE + "Antecedente de infarto hace 10 años. En esta consulta se documenta un nuevo episodio. Diagnóstico principal: infarto agudo de miocardio actual. " + NORMAL, "priority": "Urgente", "destination": "Cola_Emergencia_Medica", "diagnosis_terms": ["infarto", "iam"], "spo2": 99},
    "infarto_descartado_signo_critico": {"text": BASE + "Se descarta infarto. Diagnóstico principal: control de salud normal. " + CRITICAL, "priority": "Urgente", "destination": "Cola_Emergencia_Medica", "diagnosis_terms": ["control"], "spo2": 88},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", nargs="+", choices=CASES)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=65)
    args = parser.parse_args()
    if args.interval < 0:
        parser.error("interval debe ser >=0")
    graph = build_graph()
    reports = []
    selected = [(name, CASES[name]) for name in (args.case or CASES)]
    for index, (name, case) in enumerate(selected):
        try:
            result = graph.invoke({"document_text": case["text"], "document_id": name, "origin_channel": "Validacion_ficticia"})
            data = result["extracted_data"].model_dump(mode="json")
            expected = {
                "nivel_prioridad": case["priority"], "destino_final": case["destination"],
                "requires_human_review": False, "final_confidence_score": 1.0,
            }
            differences = [{"campo": key, "esperado": value, "obtenido": result.get(key)} for key, value in expected.items() if result.get(key) != value]
            diagnosis = (data.get("diagnostico_principal") or "").casefold()
            if not any(term in diagnosis for term in case["diagnosis_terms"]):
                differences.append({"campo": "diagnostico_principal", "esperado": case["diagnosis_terms"], "obtenido": diagnosis})
            if case["priority"] == "Rutina" and ("infarto" in diagnosis or "iam" in diagnosis):
                differences.append({"campo": "diagnostico_principal.contexto", "esperado": "Sin infarto negado/histórico como diagnóstico actual", "obtenido": diagnosis})
            vitals = data.get("signos_vitales") or {}
            if vitals.get("saturacion_oxigeno") != case["spo2"]:
                differences.append({"campo": "saturacion_oxigeno", "esperado": case["spo2"], "obtenido": vitals.get("saturacion_oxigeno")})
            report = {"caso": name, "texto": case["text"], "datos": data,
                "clasificacion": result["classification"].model_dump(mode="json"),
                "prioridad_apoyo": result.get("nivel_prioridad_apoyo"), "motivo_apoyo": result.get("justificacion_apoyo"),
                "prioridad_final": result.get("nivel_prioridad"), "destino": result.get("destino_final"),
                "score": result.get("final_confidence_score"), "diferencias": differences}
        except Exception as error:
            report = {"caso": name, "error_tipo": type(error).__name__, "causa_tipo": type(error.__cause__).__name__ if error.__cause__ else None}
            cause = error.__cause__ or error
            body = getattr(cause, "body", {})
            if type(cause).__name__ == "RateLimitError" and isinstance(body, dict):
                detail = body.get("error", body)
                if isinstance(detail, dict):
                    report["limite_proveedor"] = re.sub(r"organization `[^`]+`", "organization [oculta]", detail.get("message", ""))[:700]
        reports.append(report)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
        print(name, "ERROR" if "error_tipo" in report else ("OK" if not report["diferencias"] else "REVISAR"), flush=True)
        if index < len(selected) - 1:
            time.sleep(args.interval)
    raise SystemExit(int(any("error_tipo" in r or r.get("diferencias") for r in reports)))


if __name__ == "__main__":
    main()
