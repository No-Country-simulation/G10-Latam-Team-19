"""Pruebas del grafo completo con proveedor simulado, sin credenciales."""
import unittest
from unittest.mock import Mock, patch

from graph import build_graph, gate_score_confianza
from schemas import Clasificacion, DatosExtraidos


class GraphTests(unittest.TestCase):
    def run_graph(self, data, support="Rutina"):
        classification = Clasificacion(
            tipo_documento="Receta Medica", especialidad="Medicina general",
            nivel_prioridad="Rutina", score_confianza_clasificacion=0.99,
        )
        llm = Mock()
        llm.with_structured_output.return_value.invoke.side_effect = [classification, data, {"nivel_prioridad": support, "justificacion": "Evidencia clínica documentada"}]
        with patch("llm_provider.get_llm", return_value=llm):
            result = build_graph().invoke({"document_text": "Documento ficticio"})
        llm.invoke.assert_not_called()
        return result

    def test_gate_boundaries(self):
        for score, route in [(0.749999, "corte_revision_humana"), (0.75, "nodo_2"), (0.90, "nodo_2")]:
            with self.subTest(score=score):
                self.assertEqual(gate_score_confianza({"final_confidence_score": score}), route)

    def test_low_score_stops_before_priority(self):
        with patch("priority.evaluate_priority") as evaluate:
            result = self.run_graph(DatosExtraidos(paciente={"edad": 42, "sexo": "F"}))
        evaluate.assert_not_called()
        self.assertEqual(result["destino_final"], "Cola_Revision_Humana")
        self.assertTrue(result["requires_human_review"])
        self.assertNotIn("nivel_prioridad", result)
        self.assertEqual(result["final_confidence_score"], result["extraction_confidence_score"])

    def test_missing_route_stops_before_priority(self):
        data = DatosExtraidos(
            paciente={"edad": 42, "sexo": "F"},
            diagnostico_principal="control",
            medicamentos=[{"nombre": "A", "dosis": "10 mg", "frecuencia_diaria": "diaria"}],
        )
        with patch("priority.evaluate_priority") as evaluate:
            result = self.run_graph(data)
        evaluate.assert_not_called()
        self.assertEqual(result["final_confidence_score"], 0.70)
        self.assertEqual(result["destino_final"], "Cola_Revision_Humana")
        self.assertTrue(result["requires_human_review"])

    def test_medication_route_survives_complete_graph(self):
        data = DatosExtraidos(
            paciente={"edad": 42, "unidad_edad": "años", "sexo": "F"},
            diagnostico_principal="control",
            medicamentos=[{"nombre": "loratadina", "via": "Oral", "dosis": "10 mg", "frecuencia_diaria": "una vez al día"}],
        )
        result = self.run_graph(data)
        self.assertEqual(result["final_confidence_score"], 1.0)
        self.assertEqual(result["extracted_data"].medicamentos[0].via.value, "Oral")
        self.assertEqual(result["destino_final"], "Historia_Clinica_Electronica")
        self.assertFalse(result["requires_human_review"])
        self.assertEqual(result["decision_enrutamiento"].destino_principal.value, result["destino_final"])

    def test_support_urgency_updates_destination_and_alert(self):
        result = self.run_graph(DatosExtraidos(
            paciente={"edad": 42, "sexo": "F"},
            diagnostico_principal="Condición clínica documentada",
            medicamentos=[{"nombre": "loratadina", "via": "Oral", "dosis": "10 mg", "frecuencia_diaria": "diaria"}],
        ), support="Urgente")
        self.assertEqual(result["nivel_prioridad"], "Urgente")
        self.assertEqual(result["nivel_prioridad_apoyo"], "Urgente")
        self.assertEqual(result["destino_final"], "Cola_Emergencia_Medica")
        self.assertIsNotNone(result["decision_enrutamiento"].notificacion_generada)
        self.assertEqual(result["final_confidence_score"], 1.0)

    def test_restricted_drug_keeps_audit_with_high_score(self):
        result = self.run_graph(DatosExtraidos(
            paciente={"edad": 42, "unidad_edad": "años", "sexo": "F"},
            diagnostico_principal="control",
            medicamentos=[{"nombre": "morfina", "via": "Oral", "dosis": "10 mg", "frecuencia_diaria": "una vez al día"}],
        ))
        self.assertEqual(result["final_confidence_score"], 1.0)
        self.assertEqual(result["destino_final"], "Auditoria_Autorizaciones")
        self.assertTrue(result["requires_human_review"])


if __name__ == "__main__":
    unittest.main()
