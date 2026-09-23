# PRUEBAS AUTOMÁTICAS: se conservan para detectar regresiones de la extracción.
# Usan datos ficticios y un LLM simulado; no consumen API ni prueban el nodo final.
# Las expectativas numéricas deberán actualizarse cuando Datos confirme los pesos.
import unittest
from unittest.mock import Mock, patch

from confidence import confidence_score, missing_relevant_fields
from nodes import extraction_node
from schemas import Clasificacion, DatosExtraidos, TipoDocumento


def complete_data(**patient):
    return DatosExtraidos(
        paciente={"nombre": "Ana Ejemplo", "edad": 35, **patient},
        medico_solicitante={"nombre": "Dra. Prueba"},
        diagnostico_principal="Diagnóstico ficticio",
        estudio_realizado="Estudio ficticio",
        medicamentos=["Medicamento ficticio"],
        dosis=["Dosis ficticia"],
    )


def classification(score=0.95, kind=TipoDocumento.RECETA_MEDICA):
    return Clasificacion(
        tipo_documento=kind, especialidad="General",
        nivel_prioridad="Rutina", score_confianza_clasificacion=score,
    )


class ConfidenceTests(unittest.TestCase):
    def test_four_cases_in_both_extraction_routes(self):
        # Regla de Michelle: completo, sin nombre, sin edad y sin ambos.
        # Cada caso se comprueba tanto por respuesta estructurada como por fallback.
        cases = [
            ({}, 1.0, []),
            ({"nombre": "Desconocido"}, 0.85, ["paciente.nombre"]),
            ({"edad": None}, 0.90, ["paciente.edad"]),
            ({"nombre": "Desconocido", "edad": None}, 0.75,
             ["paciente.nombre", "paciente.edad"]),
        ]
        for patient, extraction_score, missing in cases:
            for fallback in (False, True):
                with self.subTest(patient=patient, fallback=fallback):
                    data = complete_data(**patient)
                    llm = Mock()
                    llm.with_structured_output.return_value.invoke.return_value = data.model_dump()
                    if fallback:
                        llm.with_structured_output.side_effect = RuntimeError("unsupported")
                        llm.invoke.return_value.content = '```json\n' + data.model_dump_json() + '\n```'
                    state = {"document_text": "Documento ficticio", "classification": classification()}
                    with patch("llm_provider.get_llm", return_value=llm):
                        result = extraction_node(state)
                    self.assertEqual(result["missing_critical_fields"], missing)
                    self.assertEqual(result["extraction_confidence_score"], extraction_score)
                    self.assertIsInstance(result["extracted_data"], DatosExtraidos)
                    self.assertNotIn("final_confidence_score", result)
                    self.assertNotIn("requires_human_review", result)
                    with patch("llm_provider.get_llm", return_value=llm):
                        repeated = extraction_node({**state, **result})
                    self.assertEqual(repeated["extraction_confidence_score"], extraction_score)

    def test_missing_text_markers_and_newborn_age(self):
        for name in ("", "  ", " DESCONOCIDO ", "null", "No consignado"):
            with self.subTest(name=name):
                self.assertEqual(confidence_score(complete_data(nombre=name, edad=0)), 0.85)
        self.assertEqual(confidence_score(complete_data(edad=0)), 1.0)

    def test_clinical_fields_accumulate_and_optional_fields_stay_optional(self):
        data = DatosExtraidos(paciente={"nombre": "Ana", "edad": 35})
        self.assertEqual(confidence_score(data), 0.70)
        self.assertEqual(missing_relevant_fields(data), [
            "medico_solicitante.nombre", "diagnostico_principal",
        ])
        self.assertEqual(confidence_score(data, TipoDocumento.RECETA_MEDICA), 0.55)
        for kind in (TipoDocumento.INFORME_ESTUDIO, TipoDocumento.INFORME_LABORATORIO):
            self.assertEqual(confidence_score(data, kind), 0.60)
        self.assertEqual(confidence_score(data, TipoDocumento.EPICRISIS), 0.70)

    def test_empty_lists_do_not_count_as_medication_or_dose(self):
        for empty in (None, [], ["  ", "Desconocido"]):
            data = complete_data()
            data.medicamentos = empty
            data.dosis = empty
            self.assertEqual(confidence_score(data, TipoDocumento.RECETA_MEDICA), 0.85)

    def test_doses_expected_when_medication_present(self):
        data = complete_data()
        data.dosis = None
        self.assertEqual(confidence_score(data, TipoDocumento.EPICRISIS), 0.95)

    def test_empty_doctor_name_is_missing(self):
        data = complete_data()
        data.medico_solicitante.nombre = "  "
        self.assertEqual(confidence_score(data), 0.90)

    def test_extraction_without_classification(self):
        data = complete_data(nombre="Desconocido", edad=None)
        llm = Mock()
        llm.with_structured_output.return_value.invoke.return_value = data
        with patch("llm_provider.get_llm", return_value=llm):
            result = extraction_node({"document_text": "Documento ficticio"})
        self.assertEqual(result["extraction_confidence_score"], 0.75)
        self.assertEqual(result["missing_critical_fields"], ["paciente.nombre", "paciente.edad"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
