import json
import unittest
from unittest.mock import Mock, patch

from priority import evaluate_priority, load_config
from priority_support import evaluate_clinical_support
from schemas import DatosExtraidos, ApoyoPrioridad
from nodes import priority_node
from graph import build_graph


class SupportTests(unittest.TestCase):
    def test_structured_and_json_routes(self):
        for fallback in (False, True):
            with self.subTest(fallback=fallback):
                payload = {"nivel_prioridad": "Prioritario", "justificacion": "Dolor activo"}
                llm = Mock()
                llm.with_structured_output.return_value.invoke.return_value = payload
                if fallback:
                    llm.with_structured_output.side_effect = RuntimeError("unsupported")
                    llm.invoke.return_value.content = "```json\n" + json.dumps(payload) + "\n```"
                with patch("llm_provider.get_llm", return_value=llm):
                    result = evaluate_clinical_support("Dolor agudo", "Radiografía")
                self.assertEqual(result.nivel_prioridad.value, "Prioritario")
                messages = (llm.invoke if fallback else llm.with_structured_output.return_value.invoke).call_args.args[0]
                self.assertEqual(json.loads(messages[1].content), {"diagnostico_principal": "Dolor agudo", "estudio_realizado": "Radiografía"})
                if not fallback:
                    llm.invoke.assert_not_called()

    def test_support_does_not_mutate_provider_configuration(self):
        for configured in (800, 128, None):
            with self.subTest(configured=configured):
                llm = Mock()
                llm.max_tokens = configured
                llm.with_structured_output.return_value.invoke.return_value = {"nivel_prioridad": "Rutina", "justificacion": "Control"}
                with patch("llm_provider.get_llm", return_value=llm):
                    evaluate_clinical_support("Control", None)
                self.assertEqual(llm.max_tokens, configured)

    def test_invalid_structured_response_uses_valid_fallback(self):
        llm = Mock()
        llm.with_structured_output.return_value.invoke.return_value = {"nivel_prioridad": "inventada"}
        llm.invoke.return_value.content = json.dumps({"nivel_prioridad": "Urgente", "justificacion": "IAM"})
        with patch("llm_provider.get_llm", return_value=llm):
            self.assertEqual(evaluate_clinical_support("IAM", None).nivel_prioridad.value, "Urgente")
        llm.invoke.assert_called_once()

    def test_both_routes_failing_raise_explicit_error(self):
        for content in ('{}', 'not json', '{"nivel_prioridad":"inventada","justificacion":"x"}'):
            with self.subTest(content=content):
                llm = Mock()
                llm.with_structured_output.side_effect = RuntimeError("unsupported")
                llm.invoke.return_value.content = content
                with patch("llm_provider.get_llm", return_value=llm):
                    with self.assertRaisesRegex(RuntimeError, "priority_support"):
                        evaluate_clinical_support("IAM", None)

    def test_no_clinical_fields_does_not_call_provider(self):
        with patch("llm_provider.get_llm") as get:
            result = evaluate_clinical_support(None, "No consignado")
        get.assert_not_called()
        self.assertIsNone(result.nivel_prioridad)

    def test_null_support_retains_vital_severity(self):
        config = load_config()
        data = {"paciente": {"edad": 34, "unidad_edad": "años"}, "signos_vitales": {"saturacion_oxigeno": 88}}
        self.assertEqual(evaluate_priority(data, config, None)["nivel_prioridad"], "Urgente")

    def test_maximum_severity_and_recomputed_destination(self):
        config = load_config()
        for deterministic, saturation in [("Rutina", 98), ("Prioritario", 92), ("Urgente", 88)]:
            for support in config["orden_gravedad"]:
                with self.subTest(deterministic=deterministic, support=support):
                    data = {"paciente": {"edad": 34, "unidad_edad": "años"}, "signos_vitales": {"saturacion_oxigeno": saturation}, "medicamentos": [{"nombre": "Paracetamol"}]}
                    result = evaluate_priority(data, config, support)
                    expected = max((deterministic, support), key=config["orden_gravedad"].index)
                    self.assertEqual(result["nivel_prioridad"], expected)
                    self.assertEqual(result["disparar_alerta"], expected == "Urgente")
                    self.assertEqual(result["destino_principal"], {"Rutina": "Historia_Clinica_Electronica", "Prioritario": "Farmacia_Hospitalaria", "Urgente": "Cola_Emergencia_Medica"}[expected])

    def test_support_does_not_remove_medication_audit(self):
        data = DatosExtraidos(paciente={"edad": 75}, diagnostico_principal="Dolor activo", medicamentos=[{"nombre": "Fentanilo"}])
        with patch("priority_support.evaluate_clinical_support", return_value=ApoyoPrioridad(nivel_prioridad="Prioritario", justificacion="Dolor activo")):
            result = priority_node({"extracted_data": data})
        self.assertEqual(result["nivel_prioridad"], "Prioritario")
        self.assertEqual(result["destino_sugerido_nodo2"], "Auditoria_Autorizaciones")
        self.assertTrue(result["forzar_auditoria"])

    def test_support_failure_propagates_from_node(self):
        with patch("priority_support.evaluate_clinical_support", side_effect=RuntimeError("priority_support failed")):
            with self.assertRaises(RuntimeError):
                priority_node({"extracted_data": DatosExtraidos(paciente={}, diagnostico_principal="IAM")})


class GraphSupportFallbackTests(unittest.TestCase):
    def test_support_json_fallback_reaches_final_routing(self):
        from schemas import Clasificacion
        classification = Clasificacion(tipo_documento="Receta Medica", especialidad="General", nivel_prioridad="Rutina", score_confianza_clasificacion=0.99)
        data = DatosExtraidos(paciente={"edad": 42, "sexo": "F"}, diagnostico_principal="Dolor activo", medicamentos=[{"nombre": "Paracetamol", "via": "Oral", "dosis": "10 mg", "frecuencia_diaria": "diaria"}])
        llm = Mock()
        llm.with_structured_output.return_value.invoke.side_effect = [classification, data, RuntimeError("unsupported")]
        llm.invoke.return_value.content = '{"nivel_prioridad":"Prioritario","justificacion":"Dolor activo"}'
        with patch("llm_provider.get_llm", return_value=llm):
            result = build_graph().invoke({"document_text": "Documento ficticio"})
        self.assertEqual(result["nivel_prioridad"], "Prioritario")
        self.assertEqual(result["destino_final"], "Farmacia_Hospitalaria")
        self.assertFalse(result["requires_human_review"])
        llm.invoke.assert_called_once()
