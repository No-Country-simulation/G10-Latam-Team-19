import unittest

from priority import (
    age_group,
    classify_value,
    contains_term,
    evaluate_keywords,
    evaluate_medications,
    evaluate_priority,
    evaluate_vitals,
    load_config,
    normalize,
    value_matches,
)

CONFIG = load_config()


class NormalizeTests(unittest.TestCase):
    def test_removes_accents_and_case(self):
        self.assertEqual(normalize("  Asintomático "), "asintomatico")

    def test_term_matches_whole_word_only(self):
        self.assertTrue(contains_term("Tromboembolismo Pulmonar Agudo (TEP)", "tep"))
        self.assertFalse(contains_term("septeprueba", "tep"))


class EvaluateMedicationsTests(unittest.TestCase):
    def test_restricted_drug_forces_audit(self):
        result = evaluate_medications(["Enoxaparina"], CONFIG)
        self.assertTrue(result["force_audit"])
        self.assertEqual(result["restricted_found"][0]["familia"], "anticoagulantes")

    def test_one_example_per_family(self):
        examples = ["Fentanilo", "Heparina", "Meropenem", "Insulina", "Diazepam", "Quimioterapia"]
        for name in examples:
            with self.subTest(name=name):
                self.assertTrue(evaluate_medications([name], CONFIG)["force_audit"])

    def test_any_insulin_variant_is_restricted(self):
        self.assertTrue(evaluate_medications(["Insulina glargina 100 UI"], CONFIG)["force_audit"])

    def test_common_drug_is_not_restricted(self):
        result = evaluate_medications(["Paracetamol", "Ibuprofeno"], CONFIG)
        self.assertFalse(result["force_audit"])
        self.assertEqual(result["restricted_found"], [])

    def test_matching_ignores_case_and_accents(self):
        self.assertTrue(evaluate_medications(["MORFINA 10 mg"], CONFIG)["force_audit"])
        self.assertTrue(evaluate_medications(["tramadol"], CONFIG)["force_audit"])

    def test_no_medications_does_not_force_audit(self):
        self.assertFalse(evaluate_medications(None, CONFIG)["force_audit"])
        self.assertFalse(evaluate_medications([], CONFIG)["force_audit"])

    def test_one_restricted_among_common_forces_audit(self):
        result = evaluate_medications(["Paracetamol", "Warfarina"], CONFIG)
        self.assertTrue(result["force_audit"])
        self.assertEqual([m["medicamento"] for m in result["restricted_found"]], ["Warfarina"])

    def test_is_pure_same_input_same_output(self):
        names = ["Enoxaparina"]
        self.assertEqual(evaluate_medications(names, CONFIG), evaluate_medications(names, CONFIG))
        self.assertEqual(names, ["Enoxaparina"])


class EvaluateKeywordsTests(unittest.TestCase):
    def level(self, diagnosis):
        return evaluate_keywords(diagnosis, CONFIG)["level"]

    def test_one_example_per_level(self):
        self.assertEqual(self.level("Tromboembolismo Pulmonar Agudo (TEP)"), "Urgente")
        self.assertEqual(self.level("Fractura cerrada de radio"), "Prioritario")
        self.assertEqual(self.level("Control de hipertensión"), "Rutina")

    def test_matched_terms_are_reported(self):
        result = evaluate_keywords("Sepsis de foco urinario", CONFIG)
        self.assertEqual(result["matched"], ["sepsis"])

    def test_most_severe_level_wins(self):
        self.assertEqual(self.level("Control posterior a infarto"), "Urgente")
        self.assertEqual(self.level("Chequeo por dolor agudo"), "Prioritario")

    def test_matching_ignores_case_and_accents(self):
        self.assertEqual(self.level("PACIENTE ASINTOMÁTICO"), "Rutina")
        self.assertEqual(self.level("Cólico renal"), "Prioritario")

    def test_multi_word_term(self):
        self.assertEqual(self.level("Presenta hemorragia masiva"), "Urgente")

    def test_term_inside_another_word_does_not_match(self):
        self.assertIsNone(self.level("Septeprueba de laboratorio"))

    def test_no_match_returns_none(self):
        self.assertEqual(
            evaluate_keywords("Cefalea tensional", CONFIG), {"level": None, "matched": []}
        )

    def test_missing_diagnosis_returns_none(self):
        self.assertIsNone(self.level(None))
        self.assertIsNone(self.level(""))

    def test_negation_is_not_detected_yet(self):
        # Comportamiento provisorio: 'sin infarto' sube a Urgente (falso positivo, lado seguro).
        self.assertEqual(self.level("Sin infarto"), "Urgente")


class ValueMatchesTests(unittest.TestCase):
    def test_lt_is_strict(self):
        self.assertTrue(value_matches(89, {"lt": 90}))
        self.assertFalse(value_matches(90, {"lt": 90}))

    def test_gt_is_strict(self):
        self.assertTrue(value_matches(131, {"gt": 130}))
        self.assertFalse(value_matches(130, {"gt": 130}))

    def test_between_is_inclusive(self):
        self.assertTrue(value_matches(90, {"between": [90, 94]}))
        self.assertTrue(value_matches(94, {"between": [90, 94]}))
        self.assertFalse(value_matches(95, {"between": [90, 94]}))

    def test_unknown_operator_fails_loudly(self):
        with self.assertRaises(ValueError):
            value_matches(1, {"eq": 1})


class ClassifyValueTests(unittest.TestCase):
    SPO2 = CONFIG["signos_vitales"]["saturacion_oxigeno"]["adulto"]
    HEART_RATE = CONFIG["signos_vitales"]["frecuencia_cardiaca"]["adulto"]

    def test_spo2_bands(self):
        self.assertEqual(classify_value(88, self.SPO2), "Urgente")
        self.assertEqual(classify_value(92, self.SPO2), "Prioritario")
        self.assertIsNone(classify_value(97, self.SPO2))

    def test_spo2_borders(self):
        self.assertEqual(classify_value(89, self.SPO2), "Urgente")
        self.assertEqual(classify_value(90, self.SPO2), "Prioritario")
        self.assertEqual(classify_value(94, self.SPO2), "Prioritario")
        self.assertIsNone(classify_value(95, self.SPO2))

    def test_heart_rate_has_two_urgent_conditions(self):
        self.assertEqual(classify_value(135, self.HEART_RATE), "Urgente")
        self.assertEqual(classify_value(35, self.HEART_RATE), "Urgente")
        self.assertEqual(classify_value(115, self.HEART_RATE), "Prioritario")

    def test_overlap_in_pdf_resolves_to_more_severe_band(self):
        # Pendiente Michelle: FR adulto 20 figura en Prioritario (20-30) y en Rutina (12-20).
        resp_rate = CONFIG["signos_vitales"]["frecuencia_respiratoria"]["adulto"]
        self.assertEqual(classify_value(20, resp_rate), "Prioritario")
        self.assertEqual(classify_value(30, resp_rate), "Prioritario")
        self.assertEqual(classify_value(31, resp_rate), "Urgente")

    def test_gap_in_pdf_does_not_add_severity(self):
        # Pendiente Michelle: FC adulto 100-110 no tiene banda.
        self.assertIsNone(classify_value(105, self.HEART_RATE))


class AgeGroupTests(unittest.TestCase):
    def group(self, age, unit):
        return age_group(age, unit, CONFIG)

    def test_months_and_days_are_infants(self):
        self.assertEqual(self.group(None, "meses"), "pediatrico_meses_dias")
        self.assertEqual(self.group(11, "dias"), "pediatrico_meses_dias")

    def test_years_up_to_12_are_pediatric(self):
        self.assertEqual(self.group(1, "años"), "pediatrico_anos")
        self.assertEqual(self.group(12, "años"), "pediatrico_anos")

    def test_zero_years_is_pediatric(self):
        # Decisión provisoria: edad 0 con unidad 'años' usa los rangos de 1 a 12 años.
        self.assertEqual(self.group(0, "años"), "pediatrico_anos")

    def test_13_years_and_over_are_adults(self):
        self.assertEqual(self.group(13, "años"), "adulto")
        self.assertEqual(self.group(68, "años"), "adulto")

    def test_missing_data_has_no_group(self):
        self.assertIsNone(self.group(None, "años"))
        self.assertIsNone(self.group(40, None))


class EvaluateVitalsTests(unittest.TestCase):
    NORMAL = {
        "saturacion_oxigeno": 98,
        "frecuencia_cardiaca": 80,
        "frecuencia_respiratoria": 16,
        "temperatura": 36.8,
        "presion_arterial": "120/80",
    }

    def evaluate(self, vitals, age=40, age_unit="años"):
        return evaluate_vitals(vitals, age, age_unit, CONFIG)

    def test_pdf_example_case(self):
        vitals = {
            "temperatura": 37.5,
            "frecuencia_cardiaca": 115,
            "frecuencia_respiratoria": 28,
            "presion_arterial": "140/90",
            "saturacion_oxigeno": 88,
        }
        result = self.evaluate(vitals, age=52)
        self.assertEqual(result["level"], "Urgente")
        self.assertEqual(
            [(t["signo"], t["nivel"]) for t in result["triggered"]],
            [
                ("saturacion_oxigeno", "Urgente"),
                ("frecuencia_cardiaca", "Prioritario"),
                ("frecuencia_respiratoria", "Prioritario"),
            ],
        )
        self.assertEqual(result["missing"], [])

    def test_normal_adult_adds_no_severity(self):
        result = self.evaluate(self.NORMAL)
        self.assertIsNone(result["level"])
        self.assertEqual(result["triggered"], [])

    def test_heart_rate_150_depends_on_age_group(self):
        vitals = {"frecuencia_cardiaca": 150}
        self.assertEqual(self.evaluate(vitals, age=40)["level"], "Urgente")
        self.assertEqual(self.evaluate(vitals, age=8)["level"], "Prioritario")
        self.assertIsNone(self.evaluate(vitals, age=None, age_unit="meses")["level"])

    def test_respiratory_rate_14_depends_on_age_group(self):
        vitals = {"frecuencia_respiratoria": 14}
        self.assertIsNone(self.evaluate(vitals, age=40)["level"])
        self.assertEqual(self.evaluate(vitals, age=8)["level"], "Urgente")

    def test_temperature_38_5_depends_on_age_group(self):
        vitals = {"temperatura": 38.5}
        self.assertEqual(self.evaluate(vitals, age=40)["level"], "Prioritario")
        self.assertEqual(self.evaluate(vitals, age=8)["level"], "Prioritario")
        self.assertEqual(self.evaluate(vitals, age=None, age_unit="dias")["level"], "Urgente")

    def test_most_severe_sign_wins(self):
        vitals = {**self.NORMAL, "saturacion_oxigeno": 92, "frecuencia_cardiaca": 135}
        self.assertEqual(self.evaluate(vitals)["level"], "Urgente")

    def test_missing_vitals_is_recorded_without_severity(self):
        result = self.evaluate(None)
        self.assertEqual(result, {"level": None, "triggered": [], "missing": ["signos_vitales"]})

    def test_missing_age_unit_adds_no_severity(self):
        result = self.evaluate({**self.NORMAL, "saturacion_oxigeno": 85}, age_unit=None)
        self.assertIsNone(result["level"])
        self.assertEqual(result["missing"], ["paciente.unidad_edad"])

    def test_missing_age_in_years_adds_no_severity(self):
        result = self.evaluate({**self.NORMAL, "saturacion_oxigeno": 85}, age=None)
        self.assertIsNone(result["level"])
        self.assertEqual(result["missing"], ["paciente.edad"])

    def test_missing_vitals_and_age_unit_are_both_recorded(self):
        result = self.evaluate(None, age=None, age_unit=None)
        self.assertEqual(result["missing"], ["signos_vitales", "paciente.unidad_edad"])

    def test_missing_single_sign_is_recorded_and_others_still_evaluated(self):
        result = self.evaluate({"saturacion_oxigeno": 88})
        self.assertEqual(result["level"], "Urgente")
        self.assertEqual(
            result["missing"],
            [
                "signos_vitales.frecuencia_cardiaca",
                "signos_vitales.frecuencia_respiratoria",
                "signos_vitales.temperatura",
                "signos_vitales.presion_arterial",
            ],
        )

    def test_blood_pressure_systolic_or_diastolic_triggers(self):
        self.assertEqual(self.evaluate({**self.NORMAL, "presion_arterial": "185/80"})["level"], "Prioritario")
        self.assertEqual(self.evaluate({**self.NORMAL, "presion_arterial": "120/115"})["level"], "Prioritario")
        self.assertIsNone(self.evaluate({**self.NORMAL, "presion_arterial": "180/110"})["level"])

    def test_malformed_blood_pressure_fails_loudly(self):
        with self.assertRaises(ValueError):
            self.evaluate({**self.NORMAL, "presion_arterial": "alta"})

    def test_does_not_modify_input(self):
        vitals = {**self.NORMAL, "saturacion_oxigeno": 88}
        copy = dict(vitals)
        self.evaluate(vitals)
        self.assertEqual(vitals, copy)


class EvaluatePriorityTests(unittest.TestCase):
    NORMAL_VITALS = {
        "saturacion_oxigeno": 98,
        "frecuencia_cardiaca": 80,
        "frecuencia_respiratoria": 16,
        "temperatura": 36.8,
        "presion_arterial": "120/80",
    }

    def evaluate(self, diagnosis=None, vitals=None, medications=None, age=40, age_unit="años"):
        data = {
            "paciente": {"nombre": "Test", "edad": age, "unidad_edad": age_unit},
            "diagnostico_principal": diagnosis,
            "signos_vitales": vitals,
            "medicamentos": [{"nombre": name} for name in medications] if medications else None,
        }
        return evaluate_priority(data, CONFIG)

    def test_pdf_example_case_urgency_wins_over_restricted_drug(self):
        vitals = {
            "temperatura": 37.5,
            "frecuencia_cardiaca": 115,
            "frecuencia_respiratoria": 28,
            "presion_arterial": "140/90",
            "saturacion_oxigeno": 88,
        }
        result = self.evaluate("Tromboembolismo Pulmonar Agudo (TEP)", vitals, ["Enoxaparina"], age=52)
        self.assertEqual(
            result,
            {
                "nivel_prioridad": "Urgente",
                "destino_principal": "Cola_Emergencia_Medica",
                "disparar_alerta": True,
                "forzar_auditoria": True,
                "datos_faltantes": [],
            },
        )

    def test_priority_with_common_drugs_goes_to_pharmacy(self):
        result = self.evaluate("Fractura cerrada", self.NORMAL_VITALS, ["Paracetamol"])
        self.assertEqual(result["nivel_prioridad"], "Prioritario")
        self.assertEqual(result["destino_principal"], "Farmacia_Hospitalaria")
        self.assertFalse(result["disparar_alerta"])
        self.assertFalse(result["forzar_auditoria"])

    def test_priority_with_restricted_drug_goes_to_audit(self):
        result = self.evaluate("Dolor agudo", self.NORMAL_VITALS, ["Morfina"])
        self.assertEqual(result["destino_principal"], "Auditoria_Autorizaciones")
        self.assertTrue(result["forzar_auditoria"])

    def test_priority_without_medications_goes_to_clinical_history(self):
        result = self.evaluate("Fractura cerrada", self.NORMAL_VITALS)
        self.assertEqual(result["nivel_prioridad"], "Prioritario")
        self.assertEqual(result["destino_principal"], "Historia_Clinica_Electronica")

    def test_routine_goes_to_clinical_history(self):
        result = self.evaluate("Control", self.NORMAL_VITALS)
        self.assertEqual(result["nivel_prioridad"], "Rutina")
        self.assertEqual(result["destino_principal"], "Historia_Clinica_Electronica")
        self.assertFalse(result["disparar_alerta"])

    def test_restricted_drug_forces_audit_even_in_routine(self):
        result = self.evaluate("Control", self.NORMAL_VITALS, ["Insulina"])
        self.assertEqual(result["nivel_prioridad"], "Rutina")
        self.assertEqual(result["destino_principal"], "Auditoria_Autorizaciones")
        self.assertTrue(result["forzar_auditoria"])

    def test_most_severe_rule_wins_over_routine_keyword(self):
        vitals = {**self.NORMAL_VITALS, "saturacion_oxigeno": 88}
        result = self.evaluate("Control de rutina", vitals)
        self.assertEqual(result["nivel_prioridad"], "Urgente")
        self.assertTrue(result["disparar_alerta"])

    def test_no_signal_defaults_to_routine_and_records_missing(self):
        result = self.evaluate()
        self.assertEqual(result["nivel_prioridad"], "Rutina")
        self.assertEqual(result["datos_faltantes"], ["signos_vitales"])

    def test_missing_age_unit_keeps_keyword_severity_and_records_gap(self):
        result = self.evaluate("Sepsis", self.NORMAL_VITALS, age_unit=None)
        self.assertEqual(result["nivel_prioridad"], "Urgente")
        self.assertEqual(result["datos_faltantes"], ["paciente.unidad_edad"])

    def test_does_not_modify_input(self):
        data = {
            "paciente": {"edad": 40, "unidad_edad": "años"},
            "diagnostico_principal": "Sepsis",
            "signos_vitales": dict(self.NORMAL_VITALS),
            "medicamentos": [{"nombre": "Morfina"}],
        }
        copy = {**data, "signos_vitales": dict(self.NORMAL_VITALS), "medicamentos": [{"nombre": "Morfina"}]}
        evaluate_priority(data, CONFIG)
        self.assertEqual(data, copy)


class MichelleTestCases(unittest.TestCase):
    """Casos de prueba del PDF de Datos (Nodo 2). Los fallos esperados quedan como
    preguntas abiertas en _pendiente_michelle de priority_config.json."""

    def evaluate(self, age, age_unit, diagnosis, vitals, medications=None):
        data = {
            "paciente": {"edad": age, "unidad_edad": age_unit},
            "diagnostico_principal": diagnosis,
            "signos_vitales": vitals,
            "medicamentos": [{"nombre": name} for name in medications or []] or None,
        }
        return evaluate_priority(data, CONFIG)

    def test_case_1_routine(self):
        vitals = {"frecuencia_cardiaca": 72, "frecuencia_respiratoria": 16,
                  "presion_arterial": "110/70", "saturacion_oxigeno": 98, "temperatura": 36.6}
        result = self.evaluate(34, "años", "Control de salud normal (Z00.0)", vitals)
        self.assertEqual(result["nivel_prioridad"], "Rutina")
        self.assertEqual(result["destino_principal"], "Historia_Clinica_Electronica")
        self.assertFalse(result["disparar_alerta"])
        self.assertFalse(result["forzar_auditoria"])

    def test_case_2_vital_emergency(self):
        vitals = {"frecuencia_cardiaca": 135, "frecuencia_respiratoria": 32,
                  "presion_arterial": "85/50", "saturacion_oxigeno": 88, "temperatura": 35.8}
        result = self.evaluate(68, "años", "Infarto Agudo de Miocardio (IAM)", vitals)
        self.assertEqual(result["nivel_prioridad"], "Urgente")
        self.assertEqual(result["destino_principal"], "Cola_Emergencia_Medica")
        self.assertTrue(result["disparar_alerta"])

    CASE_3_VITALS = {"frecuencia_cardiaca": 88, "frecuencia_respiratoria": 18,
                     "presion_arterial": "130/80", "saturacion_oxigeno": 96, "temperatura": 36.8}

    def case_3(self):
        return self.evaluate(
            75, "años", "Dolor oncologico cronico en cuidados paliativos",
            self.CASE_3_VITALS, ["Fentanilo parche 50 mcg/h"],
        )

    def test_case_3_restricted_drug_goes_to_audit(self):
        result = self.case_3()
        self.assertEqual(result["destino_principal"], "Auditoria_Autorizaciones")
        self.assertTrue(result["forzar_auditoria"])

    @unittest.expectedFailure
    def test_case_3_expected_priority_level(self):
        # Pendiente Michelle: ninguna regla detecta el 'dolor severo activo'.
        self.assertEqual(self.case_3()["nivel_prioridad"], "Prioritario")

    @unittest.expectedFailure
    def test_case_5_infant_expected_priority(self):
        # Pendiente Michelle: la regla de lactantes (> 38.0 °C) da Urgente, el caso espera Prioritario.
        vitals = {"frecuencia_cardiaca": 150, "frecuencia_respiratoria": 42,
                  "saturacion_oxigeno": 97, "temperatura": 38.9}
        result = self.evaluate(11, "meses", "Infección viral no especificada", vitals, ["Paracetamol gotas"])
        self.assertEqual(result["nivel_prioridad"], "Prioritario")
        self.assertEqual(result["destino_principal"], "Farmacia_Hospitalaria")


if __name__ == "__main__":
    unittest.main()
