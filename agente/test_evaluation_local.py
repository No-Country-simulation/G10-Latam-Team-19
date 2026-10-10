"""Verifica que el evaluador detecta errores materiales sin llamadas al proveedor."""
import copy
import unittest
from evaluate_extraction import compare

PEDIATRIC = {
    "paciente": {"nombre": None, "documento_identidad": None, "edad": 11, "unidad_edad": "meses", "sexo": "M"},
    "medico_solicitante": None, "estudio_realizado": None, "cie10_sugerido": None,
    "diagnostico_principal": "Infección viral no especificada",
    "medicamentos": [{"nombre": "Paracetamol gotas", "via": "Oral", "dosis": "15 gotas", "frecuencia_diaria": "Cada 6 horas en caso de fiebre"}],
    "signos_vitales": {"temperatura": 38.9, "frecuencia_cardiaca": 150, "frecuencia_respiratoria": 42, "presion_arterial": None, "saturacion_oxigeno": 97},
}

class EvaluationTests(unittest.TestCase):
    def test_documented_presentation_is_accepted(self):
        self.assertEqual(compare("caso_5_pediatrico", PEDIATRIC), [])

    def test_material_medication_errors_are_detected(self):
        for field, wrong in [("nombre", "Paracetamol con ibuprofeno"), ("via", None), ("dosis", "100mg/ml"), ("dosis", "15 mg"), ("frecuencia_diaria", "Cada 6 horas")]:
            with self.subTest(field=field, wrong=wrong):
                data = copy.deepcopy(PEDIATRIC)
                data["medicamentos"][0][field] = wrong
                failures = compare("caso_5_pediatrico", data)
                self.assertIn("medicamentos.0." + field, [item["campo"] for item in failures])

    def test_missing_fields_are_not_equivalent_to_explicit_null(self):
        data = copy.deepcopy(PEDIATRIC)
        del data["signos_vitales"]["presion_arterial"]
        self.assertIn("signos_vitales.presion_arterial", [item["campo"] for item in compare("caso_5_pediatrico", data)])
