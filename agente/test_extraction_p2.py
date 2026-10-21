"""Regression fixture transcribed from the frontend P2 report (synthetic case)."""
import unittest
from unittest.mock import Mock, patch

from nodes import extraction_node

TEXT = (
    "INFORME DE GUARDIA - Hospital Central. Paciente: Laura Benitez, 34 años, sexo F, "
    "DNI 30111222. Consulta por dolor torácico opresivo de 2 horas de evolución irradiado "
    "a brazo izquierdo, con sudoración. Signos vitales: TA 150/95, FC 112 lpm, FR 22 rpm, "
    "SpO2 93%, temperatura 36.8. ECG con supradesnivel del ST en derivaciones inferiores. "
    "Diagnóstico presuntivo: Infarto agudo de miocardio (IAM). Se indica Aspirina "
    "300 mg vía oral dosis única. Médico: Dr. Martín Ríos, matrícula 55821."
)
EXPECTED = {
    "paciente": {"nombre": "Laura Benitez", "edad": 34, "unidad_edad": "años",
                 "sexo": "F", "documento_identidad": "30111222"},
    "medico_solicitante": {"nombre": "Dr. Martín Ríos", "matricula": "55821"},
    "estudio_realizado": "ECG",
    "diagnostico_principal": "Diagnóstico presuntivo: Infarto agudo de miocardio (IAM)",
    "cie10_sugerido": None,
    "medicamentos": [{"nombre": "Aspirina", "via": "Oral", "dosis": "300 mg",
                      "frecuencia_diaria": "dosis única"}],
    "signos_vitales": {"temperatura": 36.8, "frecuencia_cardiaca": 112,
                       "frecuencia_respiratoria": 22, "presion_arterial": "150/95",
                       "saturacion_oxigeno": 93},
}


class P2ContractTests(unittest.TestCase):
    def test_evaluator_detects_reported_omissions(self):
        from evaluate_extraction_p2 import differences
        from copy import deepcopy
        incomplete = deepcopy(EXPECTED)
        incomplete["paciente"]["sexo"] = None
        incomplete["paciente"]["documento_identidad"] = None
        incomplete["signos_vitales"] = None
        incomplete["medicamentos"][0]["dosis"] = None
        incomplete["medico_solicitante"]["matricula"] = None
        failures = differences(incomplete)
        self.assertIn("paciente.sexo", failures)
        self.assertIn("paciente.documento_identidad", failures)
        self.assertIn("signos_vitales.frecuencia_cardiaca", failures)
        self.assertIn("medicamentos.0.dosis", failures)
        self.assertIn("medico_solicitante.matricula", failures)
        self.assertNotIn("cie10_sugerido", failures)
        self.assertEqual(differences(EXPECTED), [])

    def test_diagnostics_do_not_log_error_body(self):
        from evaluate_extraction_p2 import safe_error
        error = RuntimeError("sensitive provider response")
        error.status_code = 400
        error.body = {"error": {"code": "tool_use_failed", "message": "sensitive"}}
        self.assertEqual(safe_error(error), {
            "type": "RuntimeError", "status": 400, "code": "tool_use_failed",
        })

    def test_p2_fields_survive_both_routes(self):
        import json
        for fallback in (False, True):
            with self.subTest(fallback=fallback):
                llm = Mock()
                llm.with_structured_output.return_value.invoke.return_value = EXPECTED
                if fallback:
                    llm.with_structured_output.side_effect = NotImplementedError()
                    llm.invoke.return_value.content = json.dumps(EXPECTED)
                with patch("llm_provider.get_llm", return_value=llm):
                    result = extraction_node({"document_text": TEXT})
                self.assertEqual(result["extracted_data"].model_dump(mode="json"), EXPECTED)
                self.assertEqual(result["extraction_confidence_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
