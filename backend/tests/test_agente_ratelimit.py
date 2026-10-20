"""Tests de regresión P3: Detección y respuesta HTTP 429 para límites de uso del LLM."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.agente import AgenteError, _es_error_limite_llm


def test_es_error_limite_llm_por_status_code():
    class DummyHttpError(Exception):
        status_code = 429

    assert _es_error_limite_llm(DummyHttpError("Too Many Requests")) is True


def test_es_error_limite_llm_por_nombre_clase():
    class RateLimitError(Exception):
        pass

    class ResourceExhausted(Exception):
        pass

    assert _es_error_limite_llm(RateLimitError("Límite alcanzado")) is True
    assert _es_error_limite_llm(ResourceExhausted("Quota exceeded")) is True


def test_es_error_limite_llm_en_cadena_causa():
    class RateLimitError(Exception):
        pass

    causa = RateLimitError("429 error")
    err = RuntimeError("Fallo en ejecución del grafo")
    err.__cause__ = causa

    assert _es_error_limite_llm(err) is True


def test_es_error_limite_llm_mensaje_especifico_groq():
    # Mensaje exacto observado en el reporte P3
    msg = (
        "groq.RateLimitError: Error code: 429 - Rate limit reached for model "
        "`qwen/qwen3.8-27b` on output tokens per minute (OTPM): Limit 1000, Used 759, Requested 296."
    )
    assert _es_error_limite_llm(RuntimeError(msg)) is True


def test_es_error_limite_llm_mensaje_wrapped_en_nodes():
    # Mensaje generado en extraction_node cuando falla fallback
    msg = (
        "extraction_node: fallaron la respuesta estructurada y el parseo JSON alternativo. "
        "Tipos de error: BadRequestError y RateLimitError. No se generaron datos de reemplazo."
    )
    assert _es_error_limite_llm(RuntimeError(msg)) is True


def test_es_error_limite_llm_no_falsos_positivos():
    assert _es_error_limite_llm(ValueError("DNI debe tener 8 dígitos")) is False
    assert _es_error_limite_llm(ConnectionError("Error de conexión a la base de datos")) is False
    assert _es_error_limite_llm(KeyError("paciente")) is False


def test_endpoint_triage_responde_429_con_retry_after(monkeypatch):
    client = TestClient(app)

    def fake_ejecutar_agente(doc):
        raise AgenteError(
            "Servicio ocupado por límite de uso del proveedor de IA. Por favor, intentá en un minuto.",
            status_code=429,
            headers={"Retry-After": "60"},
        )

    monkeypatch.setattr("app.main.ejecutar_agente", fake_ejecutar_agente)

    payload = {
        "documento_id": "TEST-RATE-LIMIT-1",
        "tipo_archivo": "TEXTO",
        "documento_texto": "Paciente de 45 años consulta por dolor precordial.",
        "canal_origen": "Guardia_Emergencias",
    }

    res = client.post("/triage", json=payload)
    assert res.status_code == 429
    assert res.headers.get("retry-after") == "60"
    data = res.json()
    assert "Servicio ocupado por límite de uso del proveedor de IA" in data["detail"]
    assert "intentá en un minuto" in data["detail"]


def test_ejecutar_agente_mapea_rate_limit_a_429(monkeypatch):
    from app.schemas import DocumentoClinicoRequest, TipoArchivo
    from app.services.agente import ejecutar_agente

    class FakeGrafo:
        def invoke(self, state):
            raise RuntimeError(
                "extraction_node: fallaron la respuesta estructurada y el parseo JSON alternativo. "
                "Tipos de error: BadRequestError y RateLimitError."
            )

    monkeypatch.setattr("app.services.agente._cargar_grafo", lambda: FakeGrafo())

    doc = DocumentoClinicoRequest(
        documento_id="DOC-TEST-123",
        tipo_archivo=TipoArchivo.TEXTO,
        documento_texto="Texto clínico de prueba con suficiente longitud",
        canal_origen="Guardia_Emergencias",
    )

    with pytest.raises(AgenteError) as exc_info:
        ejecutar_agente(doc)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "60"}
    assert "Servicio ocupado por límite de uso del proveedor de IA" in exc_info.value.detalle


def test_ejecutar_agente_mapea_error_comun_a_502(monkeypatch):
    from app.schemas import DocumentoClinicoRequest, TipoArchivo
    from app.services.agente import ejecutar_agente

    class FakeGrafo:
        def invoke(self, state):
            raise RuntimeError("Fallo inesperado de base de datos o lógica")

    monkeypatch.setattr("app.services.agente._cargar_grafo", lambda: FakeGrafo())

    doc = DocumentoClinicoRequest(
        documento_id="DOC-TEST-456",
        tipo_archivo=TipoArchivo.TEXTO,
        documento_texto="Texto clínico de prueba con suficiente longitud",
        canal_origen="Guardia_Emergencias",
    )

    with pytest.raises(AgenteError) as exc_info:
        ejecutar_agente(doc)

    assert exc_info.value.status_code == 502
    assert exc_info.value.headers is None
    assert "El agente no pudo procesar el documento" in exc_info.value.detalle

