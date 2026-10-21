"""
Tests de ocr.py. No necesitan claves ni red: el LLM se reemplaza por uno falso que
registra lo que se le envía. Cubren lo que sí es nuestro código (normalización de la imagen,
armado del mensaje, limpieza de la respuesta, límite de páginas y mapeo de errores); la
calidad real de la lectura depende del modelo y se prueba a mano con `python ocr.py <archivo>`.

Correr desde la raíz del repo:
    PYTHONPATH=agente:. python -m unittest agente/tests/test_ocr.py
"""

import base64
import io
import unittest
from unittest.mock import patch

from PIL import Image

import ocr
from ocr import OcrError


def _png(ancho=300, alto=200, modo="RGB", color=(255, 255, 255)) -> bytes:
    salida = io.BytesIO()
    Image.new(modo, (ancho, alto), color).save(salida, format="PNG")
    return salida.getvalue()


class _Respuesta:
    def __init__(self, content):
        self.content = content


class LlmFalso:
    """Imita al cliente de LangChain: guarda los mensajes y devuelve respuestas programadas."""

    def __init__(self, respuestas=("Receta médica\nParacetamol 500 mg",), error=None):
        self.respuestas = list(respuestas)
        self.error = error
        self.mensajes = []
        self.max_tokens = 800
        self.request_timeout = 30.0

    def invoke(self, mensajes):
        self.mensajes.append(mensajes)
        if self.error:
            raise self.error
        return _Respuesta(self.respuestas.pop(0) if len(self.respuestas) > 1 else self.respuestas[0])


def _con_llm(llm):
    return patch("llm_provider.get_llm", return_value=llm)


class LimpiarRespuestaTests(unittest.TestCase):
    def test_deja_pasar_texto_normal(self):
        self.assertEqual(ocr._limpiar_respuesta("  Ibuprofeno 400 mg  "), "Ibuprofeno 400 mg")

    def test_quita_el_razonamiento_del_modelo(self):
        crudo = "<think>\nEl usuario quiere...\n</think>\nDx: faringitis"
        self.assertEqual(ocr._limpiar_respuesta(crudo), "Dx: faringitis")

    def test_razonamiento_sin_cerrar_no_deja_transcripcion(self):
        self.assertEqual(ocr._limpiar_respuesta("<think>pensando y pensando…"), "")

    def test_quita_vallas_de_codigo(self):
        self.assertEqual(ocr._limpiar_respuesta("```text\nPaciente: Ana\n```"), "Paciente: Ana")

    def test_no_toca_los_marcadores_de_ilegible(self):
        self.assertEqual(ocr._limpiar_respuesta("Dosis: [ilegible] mg"), "Dosis: [ilegible] mg")


class NormalizarImagenTests(unittest.TestCase):
    def _abrir(self, jpeg):
        return Image.open(io.BytesIO(jpeg))

    def test_devuelve_jpeg_rgb(self):
        imagen = self._abrir(ocr._normalizar_imagen(_png(modo="RGBA", color=(255, 0, 0, 0))))
        self.assertEqual(imagen.format, "JPEG")
        self.assertEqual(imagen.mode, "RGB")

    def test_transparencia_sobre_fondo_blanco(self):
        # Un PNG con texto sobre fondo transparente no debe quedar negro.
        imagen = self._abrir(ocr._normalizar_imagen(_png(modo="RGBA", color=(0, 0, 0, 0))))
        self.assertGreater(min(imagen.getpixel((10, 10))), 240)

    def test_reduce_imagenes_grandes(self):
        imagen = self._abrir(ocr._normalizar_imagen(_png(ancho=5000, alto=3000)))
        self.assertEqual(max(imagen.size), 2048)
        self.assertAlmostEqual(imagen.size[0] / imagen.size[1], 5000 / 3000, delta=0.01)  # conserva la proporción

    def test_respeta_el_limite_configurable(self):
        with patch.dict("os.environ", {"OCR_MAX_LADO_PX": "500"}):
            imagen = self._abrir(ocr._normalizar_imagen(_png(ancho=1000, alto=1000)))
        self.assertEqual(max(imagen.size), 500)

    def test_corrige_la_rotacion_exif_de_las_fotos_de_celular(self):
        # Foto horizontal (300x200) marcada como "girar 90°": al normalizarla queda vertical.
        base = Image.new("RGB", (300, 200), (255, 255, 255))
        exif = base.getexif()
        exif[0x0112] = 6
        salida = io.BytesIO()
        base.save(salida, format="JPEG", exif=exif)
        imagen = self._abrir(ocr._normalizar_imagen(salida.getvalue()))
        self.assertEqual(imagen.size, (200, 300))

    def test_archivo_que_no_es_imagen(self):
        with self.assertRaises(OcrError) as ctx:
            ocr._normalizar_imagen(b"esto no es una imagen")
        self.assertEqual(ctx.exception.tipo, "entrada_invalida")


class TranscribirImagenTests(unittest.TestCase):
    def test_envia_prompt_e_imagen_en_data_url_y_devuelve_el_texto(self):
        llm = LlmFalso(["Receta\nAmoxicilina 500 mg cada 8 h"])
        with _con_llm(llm):
            resultado = ocr.transcribir_imagen(_png())

        self.assertEqual(resultado.texto, "Receta\nAmoxicilina 500 mg cada 8 h")
        self.assertEqual((resultado.paginas, resultado.paginas_totales), (1, 1))

        contenido = llm.mensajes[0][0].content
        self.assertEqual(contenido[0]["type"], "text")
        self.assertIn("[ilegible]", contenido[0]["text"])
        url = contenido[1]["image_url"]["url"]
        self.assertTrue(url.startswith("data:image/jpeg;base64,"))
        jpeg = base64.b64decode(url.split(",", 1)[1])  # es una imagen válida de verdad
        self.assertEqual(Image.open(io.BytesIO(jpeg)).format, "JPEG")

    def test_ajusta_tokens_y_timeout_del_cliente(self):
        llm = LlmFalso()
        with _con_llm(llm):
            ocr.transcribir_imagen(_png())
        self.assertEqual(llm.max_tokens, 3000)
        self.assertEqual(llm.request_timeout, 90)

    def test_acepta_contenido_en_bloques(self):
        llm = LlmFalso([[{"type": "text", "text": "Dx: asma"}]])
        with _con_llm(llm):
            self.assertEqual(ocr.transcribir_imagen(_png()).texto, "Dx: asma")

    def test_sin_texto(self):
        with _con_llm(LlmFalso(["SIN_TEXTO"])):
            with self.assertRaises(OcrError) as ctx:
                ocr.transcribir_imagen(_png())
        self.assertEqual(ctx.exception.tipo, "sin_texto")

    def test_respuesta_vacia_es_sin_texto(self):
        with _con_llm(LlmFalso(["<think>solo pienso</think>"])):
            with self.assertRaises(OcrError) as ctx:
                ocr.transcribir_imagen(_png())
        self.assertEqual(ctx.exception.tipo, "sin_texto")

    def test_fallo_del_proveedor(self):
        with _con_llm(LlmFalso(error=RuntimeError("429 rate limit"))):
            with self.assertRaises(OcrError) as ctx:
                ocr.transcribir_imagen(_png())
        self.assertEqual(ctx.exception.tipo, "proveedor")
        self.assertIn("429", str(ctx.exception))

    def test_cohere_no_sirve_para_imagenes(self):
        class ChatCohere(LlmFalso):
            pass

        with _con_llm(ChatCohere()):
            with self.assertRaises(OcrError) as ctx:
                ocr.transcribir_imagen(_png())
        self.assertEqual(ctx.exception.tipo, "config")

    def test_falta_la_api_key_se_propaga_como_valueerror(self):
        # llm_provider levanta ValueError; el backend lo traduce a 503.
        with patch("llm_provider.get_llm", side_effect=ValueError("Falta GROQ_API_KEY en el .env")):
            with self.assertRaises(ValueError):
                ocr.transcribir_imagen(_png())


def _pdf(paginas: int) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    for n in range(paginas):
        pagina = doc.new_page()
        pagina.insert_text((72, 72), f"Pagina {n + 1}")
    datos = doc.tobytes()
    doc.close()
    return datos


class TranscribirPdfTests(unittest.TestCase):
    def test_lee_solo_las_primeras_paginas(self):
        llm = LlmFalso(["pagina uno", "pagina dos", "pagina tres"])
        with _con_llm(llm):
            resultado = ocr.transcribir_archivo(_pdf(5))
        self.assertEqual(len(llm.mensajes), 3)
        self.assertEqual((resultado.paginas, resultado.paginas_totales), (3, 5))
        self.assertEqual(resultado.texto, "pagina uno\n\npagina dos\n\npagina tres")

    def test_un_pdf_corto_se_lee_entero(self):
        with _con_llm(LlmFalso(["unica pagina"])):
            resultado = ocr.transcribir_archivo(_pdf(1))
        self.assertEqual((resultado.paginas, resultado.paginas_totales), (1, 1))

    def test_una_pagina_en_blanco_no_invalida_el_resto(self):
        llm = LlmFalso(["SIN_TEXTO", "contenido real"])
        with patch.dict("os.environ", {"OCR_MAX_PAGINAS": "2"}), _con_llm(llm):
            resultado = ocr.transcribir_archivo(_pdf(2))
        self.assertEqual(resultado.texto, "contenido real")

    def test_todas_las_paginas_en_blanco(self):
        with _con_llm(LlmFalso(["SIN_TEXTO"])):
            with self.assertRaises(OcrError) as ctx:
                ocr.transcribir_archivo(_pdf(2))
        self.assertEqual(ctx.exception.tipo, "sin_texto")

    def test_pdf_danado(self):
        with _con_llm(LlmFalso()):
            with self.assertRaises(OcrError) as ctx:
                ocr.transcribir_archivo(b"%PDF-1.7 basura que no es un pdf")
        self.assertEqual(ctx.exception.tipo, "entrada_invalida")

    def test_un_error_del_proveedor_en_una_pagina_corta_todo(self):
        with _con_llm(LlmFalso(error=RuntimeError("timeout"))):
            with self.assertRaises(OcrError) as ctx:
                ocr.transcribir_archivo(_pdf(2))
        self.assertEqual(ctx.exception.tipo, "proveedor")


class DeteccionDeTipoTests(unittest.TestCase):
    def test_archivo_vacio(self):
        with self.assertRaises(OcrError) as ctx:
            ocr.transcribir_archivo(b"")
        self.assertEqual(ctx.exception.tipo, "entrada_invalida")

    def test_distingue_pdf_de_imagen_por_el_contenido(self):
        with patch.object(ocr, "transcribir_pdf", return_value="pdf") as pdf, patch.object(
            ocr, "transcribir_imagen", return_value="img"
        ) as img:
            self.assertEqual(ocr.transcribir_archivo(b"%PDF-1.4 ..."), "pdf")
            self.assertEqual(ocr.transcribir_archivo(_png()), "img")
        pdf.assert_called_once()
        img.assert_called_once()


if __name__ == "__main__":
    unittest.main()
