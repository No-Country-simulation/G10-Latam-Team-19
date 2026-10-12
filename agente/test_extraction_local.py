# PRUEBAS AUTOMÁTICAS: validación Pydantic y fallback de extracción.
# Se conservan como regresión; el proveedor se simula y no necesita credenciales.
import unittest
from unittest.mock import Mock, patch

from nodes import extraction_node
from schemas import DatosExtraidos, ViaAdministracion


class ExtractionTests(unittest.TestCase):
    def test_new_schema_preserved_in_both_routes(self):
        for unit in ("años", "meses", "dias"):
            for fallback in (False, True):
                with self.subTest(unit=unit, fallback=fallback):
                    data = DatosExtraidos(
                        paciente={"nombre": "Ana", "edad": 0, "unidad_edad": unit,
                                  "sexo": "F", "documento_identidad": "ABC123456"},
                        medicamentos=[{"nombre": "A", "via": "Oral", "dosis": "10 mg", "frecuencia_diaria": "una vez al día"},
                                      {"nombre": "B", "via": None, "dosis": None}],
                        signos_vitales={"temperatura": 37.5, "frecuencia_cardiaca": 110,
                                        "frecuencia_respiratoria": 24, "presion_arterial": "120/80",
                                        "saturacion_oxigeno": 95},
                    )
                    llm = Mock()
                    llm.max_tokens = 2048
                    llm.with_structured_output.return_value.invoke.return_value = data.model_dump()
                    if fallback:
                        llm.with_structured_output.side_effect = RuntimeError("unsupported")
                        llm.invoke.return_value.content = data.model_dump_json()
                    with patch("llm_provider.get_llm", return_value=llm):
                        result = extraction_node({"document_text": "Documento ficticio"})
                    self.assertEqual(result["extracted_data"].model_dump(), data.model_dump())
                    self.assertEqual(result["missing_critical_fields"], [])
                    self.assertEqual(llm.max_tokens, 2048)

    def test_via_preserved_in_both_routes(self):
        import json
        for via in [None, *(route.value for route in ViaAdministracion)]:
            for fallback in (False, True):
                with self.subTest(via=via, fallback=fallback):
                    medication = {"nombre": "A", "dosis": "10 mg"}
                    if via is not None:
                        medication["via"] = via
                    payload = {"paciente": {"edad": 42}, "medicamentos": [medication]}
                    llm = Mock()
                    llm.with_structured_output.return_value.invoke.return_value = payload
                    if fallback:
                        llm.with_structured_output.side_effect = RuntimeError("unsupported")
                        llm.invoke.return_value.content = json.dumps(payload)
                    with patch("llm_provider.get_llm", return_value=llm):
                        result = extraction_node({"document_text": "Documento ficticio"})
                    actual = result["extracted_data"].model_dump(mode="json")["medicamentos"][0]
                    self.assertEqual(actual["via"], via)
                    self.assertEqual(list(actual), ["nombre", "via", "dosis", "frecuencia_diaria"])
                    if fallback:
                        llm.invoke.assert_called_once()
                    else:
                        llm.invoke.assert_not_called()

    def test_invalid_new_fields_fail_both_routes(self):
        import json
        invalid_cases = [
            {"medicamentos": ["A"]},
            {"medicamentos": [{"nombre": "A", "via": "inventada"}]},
            {"medicamentos": [{"nombre": "A", "via": ["Oral"]}]},
            {"medicamentos": [{"nombre": "A", "dosis": ["10 mg"]}]},
            {"signos_vitales": {"saturacion_oxigeno": 101}},
            {"signos_vitales": {"presion_arterial": "incorrecta"}},
            {"paciente": {"nombre": "Ana", "unidad_edad": "semanas"}},
            {"paciente": {"nombre": "Ana", "documento_identidad": "!"}},
        ]
        for invalid in invalid_cases:
            with self.subTest(invalid=invalid):
                payload = {"paciente": {"nombre": "Ana", "edad": 35}, **invalid}
                llm = Mock()
                llm.with_structured_output.return_value.invoke.return_value = payload
                llm.invoke.return_value.content = json.dumps(payload)
                with patch("llm_provider.get_llm", return_value=llm):
                    with self.assertRaises(RuntimeError):
                        extraction_node({"document_text": "Documento ficticio"})

    def test_nombre_ausente_no_es_critico(self):
        llm = Mock()
        llm.with_structured_output.return_value.invoke.return_value = (
            DatosExtraidos(
                paciente={"nombre": None, "edad": 42}
            )
        )

        with patch("llm_provider.get_llm", return_value=llm):
            result = extraction_node({
                "document_text": "Paciente de 42 años. Nombre no consignado."
            })

        self.assertIsInstance(result["extracted_data"], DatosExtraidos)
        self.assertEqual(result["missing_critical_fields"], [])

        # El nombre ausente no genera penalización.
        self.assertEqual(result["missing_critical_fields"], [])

        # Los descuentos corresponden al diagnóstico y al sexo.
        self.assertEqual(
            result["missing_relevant_fields"],
            ["diagnostico_o_cie10", "paciente.sexo"]
        )

        # 1.0 - 0.15 - 0.05 = 0.80
        self.assertEqual(result["extraction_confidence_score"], 0.8)

    def test_nombre_presente_con_fallback(self):
        llm = Mock()
        llm.with_structured_output.return_value.invoke.side_effect = (
            RuntimeError("Respuesta estructurada no disponible")
        )
        llm.invoke.return_value.content = (
            '{"paciente": {"nombre": "Persona de Prueba", "edad": 42}}'
        )

        with patch("llm_provider.get_llm", return_value=llm):
            result = extraction_node({
                "document_text": "Paciente: Persona de Prueba. Edad: 42 años."
            })

        self.assertEqual(
            result["extracted_data"].paciente.nombre,
            "Persona de Prueba",
        )
        self.assertEqual(result["missing_critical_fields"], [])

    def test_respuesta_invalida_genera_error(self):
        llm = Mock()
        llm.with_structured_output.return_value.invoke.return_value = {}

        # El fallback también debe devolver datos inválidos.
        llm.invoke.return_value.content = '{"paciente": {"edad": -1}}'

        with patch("llm_provider.get_llm", return_value=llm):
            with self.assertRaises(RuntimeError):
                extraction_node({
                    "document_text": "Paciente de 42 años."
                })


if __name__ == "__main__":
    unittest.main(verbosity=2)
