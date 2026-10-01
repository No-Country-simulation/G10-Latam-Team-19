# PRUEBAS AUTOMÁTICAS: se conservan para detectar regresiones de la extracción.
# Usan datos ficticios y un LLM simulado; no consumen API ni prueban el nodo final.
# Pesos del PDF de Datos, páginas 10-11; condiciones temporales documentadas.
import unittest
from unittest.mock import Mock, patch

from confidence import confidence_score, missing_relevant_fields
from nodes import extraction_node
from schemas import Clasificacion, DatosExtraidos, TipoDocumento


def complete_data(**patient):
    return DatosExtraidos(
        paciente={"nombre": "Ana Ejemplo", "edad": 35, "sexo": "F", **patient},
        medico_solicitante={"nombre": "Dra. Prueba"},
        diagnostico_principal="Diagnóstico ficticio",
        estudio_realizado="Estudio ficticio",
        medicamentos=[{"nombre": "Medicamento ficticio", "dosis": "10 mg", "frecuencia_diaria": "una vez al día"}],
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
            ({"nombre": "Desconocido"}, 0.70, ["paciente.nombre"]),
            ({"edad": None}, 0.85, ["paciente.edad"]),
            ({"nombre": "Desconocido", "edad": None}, 0.55,
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
                self.assertEqual(confidence_score(complete_data(nombre=name, edad=0)), 0.70)
        self.assertEqual(confidence_score(complete_data(edad=0)), 1.0)

    def test_pdf_weights(self):
        from confidence import MISSING_FIELD_PENALTIES
        self.assertEqual(dict(MISSING_FIELD_PENALTIES), {
            "paciente.nombre": .30, "medicamentos_o_dosis": .30,
            "paciente.unidad_edad": .30, "diagnostico_o_cie10": .15,
            "paciente.edad": .15, "signos_vitales": .10,
            "paciente.sexo": .05, "frecuencia_diaria": .05,
        })

    def test_diagnosis_or_code_is_sufficient(self):
        data = complete_data()
        data.diagnostico_principal = None
        self.assertEqual(confidence_score(data), .85)
        data.cie10_sugerido = "J30.4"
        self.assertEqual(confidence_score(data), 1.0)

    def test_doctor_and_study_no_longer_penalize(self):
        data = complete_data()
        data.medico_solicitante = None
        data.estudio_realizado = None
        for kind in TipoDocumento:
            self.assertEqual(confidence_score(data, kind), 1.0)

    def test_prescription_group_penalty_once(self):
        for meds in (None, [], [{"nombre": "Desconocido", "dosis": None}],
                     [{"nombre": "A"}, {"nombre": "B"}]):
            with self.subTest(meds=meds):
                data = DatosExtraidos.model_validate({**complete_data().model_dump(), "medicamentos": meds})
                self.assertEqual(confidence_score(data, TipoDocumento.RECETA_MEDICA), .65)
                self.assertEqual(missing_relevant_fields(data, TipoDocumento.RECETA_MEDICA),
                                 ["medicamentos_o_dosis", "frecuencia_diaria"])
                self.assertEqual(confidence_score(data, TipoDocumento.EPICRISIS), 1.0)
                self.assertEqual(confidence_score(data), 1.0)

    def test_missing_dose_and_frequency_are_separate_categories(self):
        data = complete_data()
        data.medicamentos[0].dosis = None
        self.assertEqual(confidence_score(data, TipoDocumento.RECETA_MEDICA), .70)
        data.medicamentos[0].dosis = "10 mg"
        data.medicamentos[0].frecuencia_diaria = None
        self.assertEqual(confidence_score(data, TipoDocumento.RECETA_MEDICA), .95)

    def test_partial_medication_list_is_not_hidden_by_complete_entry(self):
        data = DatosExtraidos.model_validate({**complete_data().model_dump(), "medicamentos": [
            {"nombre": "A", "dosis": "10 mg", "frecuencia_diaria": "diaria"},
            {"nombre": "B", "dosis": "No consignado", "frecuencia_diaria": "diaria"},
        ]})
        self.assertEqual(confidence_score(data, TipoDocumento.RECETA_MEDICA), .70)

    def test_vital_sign_completeness(self):
        from schemas import SignosVitales
        data = complete_data()
        self.assertEqual(confidence_score(data), 1.0)  # Aplicabilidad desconocida.
        data.signos_vitales = SignosVitales()
        self.assertEqual(confidence_score(data), .90)
        data.signos_vitales = SignosVitales(temperatura=37, frecuencia_cardiaca=80,
            frecuencia_respiratoria=16, presion_arterial="120/80", saturacion_oxigeno=98)
        self.assertEqual(confidence_score(data), 1.0)
        data.signos_vitales.presion_arterial = None
        self.assertEqual(confidence_score(data), .90)

    def test_missing_sex_uses_only_table_baseline(self):
        self.assertEqual(confidence_score(complete_data(sexo=None)), .95)

    def test_pending_identity_and_pediatric_conditions(self):
        data = complete_data(unidad_edad=None, documento_identidad=None)
        self.assertEqual(confidence_score(data), 1.0)
        data.paciente.nombre = "Desconocido"
        data.paciente.documento_identidad = "ABC123456"
        self.assertEqual(confidence_score(data), .70)  # Mantener regla acordada de nombre.

    def test_cumulative_penalties_clamp_at_zero(self):
        data = DatosExtraidos(paciente={"nombre": "Desconocido"}, signos_vitales={})
        self.assertEqual(confidence_score(data, TipoDocumento.RECETA_MEDICA), 0.0)

    def test_extraction_without_classification(self):
        data = complete_data(nombre="Desconocido", edad=None)
        llm = Mock()
        llm.with_structured_output.return_value.invoke.return_value = data
        with patch("llm_provider.get_llm", return_value=llm):
            result = extraction_node({"document_text": "Documento ficticio"})
        self.assertEqual(result["extraction_confidence_score"], 0.55)
        self.assertEqual(result["missing_critical_fields"], ["paciente.nombre", "paciente.edad"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
