"""Regression for the raw P2 tool arguments, including real SDK parsing."""
import copy
import json
import unittest
from unittest.mock import Mock, patch

from extraction_validation import validate_extraction
from nodes import extraction_node
from schemas import DatosExtraidos
from test_extraction_p2 import EXPECTED, TEXT


def reported_payload():
    data = copy.deepcopy(EXPECTED)
    for section in ("paciente", "medico_solicitante", "signos_vitales"):
        data[section] = {
            key if key == "nombre" else key + "_": value
            for key, value in data[section].items()
        }
    data["medicamentos"] = [
        {key if key == "nombre" else key + "_": value for key, value in item.items()}
        for item in data["medicamentos"]
    ]
    return data


class ExtractionKeyTests(unittest.TestCase):
    def test_original_validation_silently_loses_reported_values(self):
        result = DatosExtraidos.model_validate(reported_payload())
        self.assertIsNone(result.paciente.edad)
        self.assertEqual(result.paciente.model_fields_set, {"nombre"})

    def test_normalization_restores_all_values_without_mutating_input(self):
        raw = reported_payload()
        before = copy.deepcopy(raw)
        self.assertEqual(validate_extraction(raw).model_dump(mode="json"), EXPECTED)
        self.assertEqual(raw, before)

    def test_canonical_and_absent_fields_remain_valid(self):
        self.assertEqual(validate_extraction(EXPECTED).model_dump(mode="json"), EXPECTED)
        self.assertIsNone(validate_extraction({"paciente": {"nombre": None}}).paciente.edad)

    def test_unknown_keys_and_duplicate_aliases_rejected(self):
        for patient in ({"edad__": 34}, {"age": 34}, {"edad": 34, "edad_": 35},
                        {"edad_": 34, "edad": 34}):
            with self.subTest(patient=patient), self.assertRaises(ValueError):
                validate_extraction({"paciente": patient})

    def test_constraints_and_container_types_still_validated(self):
        for payload in ({"paciente": {"edad_": -1}},
                        {"paciente": {}, "signos_vitales": {"saturacion_oxigeno_": 101}},
                        {"paciente": {}, "medicamentos": {"nombre": "A"}},
                        {"paciente": {}, "signos_vitales": []}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_extraction(payload)

    def test_structured_and_manual_routes_restore_values(self):
        for fallback in (False, True):
            with self.subTest(fallback=fallback):
                llm = Mock()
                llm.with_structured_output.return_value.invoke.return_value = reported_payload()
                if fallback:
                    llm.with_structured_output.side_effect = NotImplementedError()
                    llm.invoke.return_value.content = json.dumps(reported_payload())
                with patch("llm_provider.get_llm", return_value=llm):
                    result = extraction_node({"document_text": TEXT})
                self.assertEqual(result["extracted_data"].model_dump(mode="json"), EXPECTED)
                self.assertEqual(result["extraction_confidence_score"], 1.0)
                if not fallback:
                    llm.invoke.assert_not_called()

    def test_real_groq_parser_preserves_raw_keys_until_normalization(self):
        from langchain_groq import ChatGroq
        from langchain_core.messages import AIMessage
        from langchain_core.runnables import RunnableLambda
        raw = AIMessage(content="", tool_calls=[{
            "name": "DatosExtraidos", "args": reported_payload(), "id": "test-p2",
        }])
        client = ChatGroq(api_key="test-not-a-real-key", model="test",
                          client=Mock(), async_client=Mock())
        # Mock only the network-bound runnable; run the SDK's real output parser.
        with patch.object(ChatGroq, "bind_tools", return_value=RunnableLambda(lambda _: raw)), \
             patch("llm_provider.get_llm", return_value=client):
            result = extraction_node({"document_text": TEXT})
        self.assertEqual(result["extracted_data"].model_dump(mode="json"), EXPECTED)


if __name__ == "__main__":
    unittest.main()
