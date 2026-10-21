"""
Tests de POST /ocr. No necesitan claves, red ni buckets.

Correr desde la carpeta backend/:
    python -m unittest discover -s tests
"""

import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1]
AGENTE = BACKEND.parent / "agente"
os.environ["AGENTE_DIR"] = str(AGENTE)  # ruta absoluta: no depende de desde dónde se corra
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(AGENTE))  # para poder reemplazar llm_provider.get_llm en los tests

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

import app.main as main  # noqa: E402
from app.services.agente import AgenteError, TranscripcionArchivo  # noqa: E402

client = TestClient(main.app)


def _png_bytes() -> bytes:
    salida = io.BytesIO()
    Image.new("RGB", (200, 120), (255, 255, 255)).save(salida, format="PNG")
    return salida.getvalue()


def _subir(nombre="receta.png", contenido=None, tipo="image/png"):
    contenido = _png_bytes() if contenido is None else contenido
    return client.post("/ocr", files={"archivo": (nombre, contenido, tipo)})


class _Respuesta:
    def __init__(self, content):
        self.content = content


class LlmFalso:
    def __init__(self, texto="Paracetamol 500 mg cada 8 h", error=None):
        self.texto, self.error = texto, error
        self.max_tokens, self.request_timeout = 800, 30.0

    def invoke(self, _mensajes):
        if self.error:
            raise self.error
        return _Respuesta(self.texto)


class ValidacionDeEntradaTests(unittest.TestCase):
    def test_formato_no_soportado(self):
        r = _subir("notas.txt", b"hola", "text/plain")
        self.assertEqual(r.status_code, 415)
        self.assertIn("JPG", r.json()["detail"])

    def test_archivo_vacio(self):
        r = _subir(contenido=b"")
        self.assertEqual(r.status_code, 422)

    def test_archivo_demasiado_grande(self):
        with patch.object(main, "MAX_ARCHIVO_BYTES", 100):
            r = _subir(contenido=b"x" * 500)
        self.assertEqual(r.status_code, 413)

    def test_acepta_por_extension_si_el_navegador_no_informa_el_tipo(self):
        with patch.object(main, "transcribir_archivo", return_value=TranscripcionArchivo("ok", 1, 1)):
            r = _subir("foto.jpg", _png_bytes(), "application/octet-stream")
        self.assertEqual(r.status_code, 200)


class RespuestaTests(unittest.TestCase):
    def test_devuelve_texto_y_paginas(self):
        resultado = TranscripcionArchivo(texto="Dx: asma", paginas=2, paginas_totales=5)
        with patch.object(main, "transcribir_archivo", return_value=resultado):
            r = _subir()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"texto": "Dx: asma", "paginas": 2, "paginas_totales": 5})

    def test_el_error_del_agente_conserva_codigo_y_mensaje(self):
        with patch.object(main, "transcribir_archivo", side_effect=AgenteError("sin clave", 503)):
            r = _subir()
        self.assertEqual((r.status_code, r.json()["detail"]), (503, "sin clave"))

    def test_no_guarda_nada_ni_toca_el_almacenamiento(self):
        with patch.object(main, "_obtener_storage_service", side_effect=AssertionError("no debe usarse")):
            with patch.object(main, "transcribir_archivo", return_value=TranscripcionArchivo("ok", 1, 1)):
                self.assertEqual(_subir().status_code, 200)


class CaminoRealConLlmFalsoTests(unittest.TestCase):
    """Endpoint -> adaptador -> agente/ocr.py -> Pillow/PyMuPDF, solo con el LLM reemplazado."""

    def _con_llm(self, llm):
        return patch("llm_provider.get_llm", return_value=llm)

    def test_imagen(self):
        with self._con_llm(LlmFalso("Receta\nIbuprofeno 400 mg")):
            r = _subir()
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["texto"], "Receta\nIbuprofeno 400 mg")

    def test_pdf_escaneado(self):
        import pymupdf

        doc = pymupdf.open()
        for _ in range(4):
            doc.new_page()
        pdf = doc.tobytes()
        doc.close()
        with self._con_llm(LlmFalso("contenido")):
            r = _subir("informe.pdf", pdf, "application/pdf")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["paginas"], r.json()["paginas_totales"]), (3, 4))

    def test_archivo_dañado_es_422(self):
        with self._con_llm(LlmFalso()):
            r = _subir("rota.png", b"no soy una imagen", "image/png")
        self.assertEqual(r.status_code, 422)

    def test_sin_texto_es_422(self):
        with self._con_llm(LlmFalso("SIN_TEXTO")):
            r = _subir()
        self.assertEqual(r.status_code, 422)
        self.assertIn("legible", r.json()["detail"])

    def test_fallo_del_proveedor_es_502(self):
        with self._con_llm(LlmFalso(error=RuntimeError("rate limit"))):
            r = _subir()
        self.assertEqual(r.status_code, 502)

    def test_falta_la_api_key_es_503(self):
        with patch("llm_provider.get_llm", side_effect=ValueError("Falta GROQ_API_KEY en el .env")):
            r = _subir()
        self.assertEqual(r.status_code, 503)
        self.assertIn("GROQ_API_KEY", r.json()["detail"])

    def test_cohere_es_503(self):
        class ChatCohere(LlmFalso):
            pass

        with self._con_llm(ChatCohere()):
            r = _subir()
        self.assertEqual(r.status_code, 503)


if __name__ == "__main__":
    unittest.main()
