# PRUEBAS AUTOMÁTICAS: validación Pydantic, nombre ausente y fallback de extracción.
# Se conservan como regresión; el proveedor se simula y no necesita credenciales.
import unittest
from unittest.mock import Mock, patch

from nodes import extraction_node
from schemas import DatosExtraidos


class ExtractionTests(unittest.TestCase):
    def test_nombre_ausente(self):
        llm = Mock()
        llm.with_structured_output.return_value.invoke.return_value = (
            DatosExtraidos(
                paciente={"nombre": "Desconocido", "edad": 42}
            )
        )

        with patch("llm_provider.get_llm", return_value=llm):
            result = extraction_node({
                "document_text": "Paciente de 42 años. Nombre no consignado."
            })

        self.assertIsInstance(result["extracted_data"], DatosExtraidos)
        self.assertEqual(
            result["missing_critical_fields"],
            ["paciente.nombre"],
        )

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
        llm.invoke.return_value.content = '{"paciente": {"edad": 42}}'

        with patch("llm_provider.get_llm", return_value=llm):
            with self.assertRaises(RuntimeError):
                extraction_node({
                    "document_text": "Paciente de 42 años."
                })


if __name__ == "__main__":
    unittest.main(verbosity=2)