"""
services/agente.py — Adaptador entre el Backend y el grafo real del Agente (LangGraph).

Responsabilidades:
    1. Localizar la carpeta del agente y agregarla a sys.path ANTES de importar el grafo
       (el agente usa imports planos: `from nodes import ...`, `from schemas import ...`).
    2. Compilar el grafo una sola vez y reutilizarlo.
    3. Ejecutarlo con un DocumentoClinicoRequest y traducir el estado final a los
       schemas del Backend (app.schemas).

Los modelos del agente y los del backend son clases distintas aunque se llamen igual;
la traducción pasa siempre por JSON (model_dump(mode="json") -> model_validate), así un
desajuste de contrato falla de forma explícita en vez de colarse en silencio.
"""

from __future__ import annotations

import logging
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.schemas import (
    Clasificacion,
    DatosExtraidos,
    DecisionEnrutamiento,
    DestinoEnrutamiento,
    DocumentoClinicoRequest,
    NivelPrioridad,
)

logger = logging.getLogger("mediflow.agente")

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_graph: Any | None = None
_graph_lock = threading.Lock()


class AgenteError(Exception):
    """Fallo al ejecutar el agente. `status_code` es el HTTP que debe devolver el endpoint."""

    def __init__(self, detalle: str, status_code: int = 502) -> None:
        super().__init__(detalle)
        self.detalle = detalle
        self.status_code = status_code


@dataclass
class ResultadoAgente:
    clasificacion: Clasificacion
    datos_extraidos: DatosExtraidos
    decision_enrutamiento: DecisionEnrutamiento
    score_confianza: float | None


def _resolver_dir_agente() -> Path:
    configurado = get_settings().AGENTE_DIR
    if configurado:
        candidatos = [Path(configurado).expanduser()]
    else:
        candidatos = [_BACKEND_ROOT.parent / "agente", _BACKEND_ROOT.parent / "agentes"]

    for candidato in candidatos:
        if (candidato / "graph.py").is_file():
            return candidato.resolve()

    raise AgenteError(
        "No se encontró la carpeta del agente (graph.py). Define AGENTE_DIR en el .env "
        f"del backend. Rutas probadas: {[str(c) for c in candidatos]}",
        status_code=503,
    )


def _cargar_grafo() -> Any:
    global _graph
    if _graph is not None:
        return _graph
    with _graph_lock:
        if _graph is None:
            dir_agente = _resolver_dir_agente()
            # insert(0): el agente necesita que SUS módulos planos (schemas, state, nodes...)
            # ganen sobre cualquier paquete homónimo instalado en site-packages.
            if str(dir_agente) not in sys.path:
                sys.path.insert(0, str(dir_agente))
            try:
                from graph import build_graph  # noqa: PLC0415  (import tardío a propósito)
            except Exception as exc:
                raise AgenteError(f"No se pudo importar el grafo del agente: {exc}", 503) from exc
            _graph = build_graph()
            logger.info("Grafo del agente compilado desde %s", dir_agente)
    return _graph


def _a_dict_json(valor: Any) -> dict[str, Any]:
    """Modelo pydantic del agente (o dict) -> dict JSON-compatible."""
    if hasattr(valor, "model_dump"):
        return valor.model_dump(mode="json")
    return dict(valor)


def _decision_desde_estado(estado: dict[str, Any]) -> DecisionEnrutamiento:
    """
    El nodo `enrutamiento_final` arma `decision_enrutamiento`, pero la rama de corte
    (`corte_revision_humana`, score < 0.75) solo deja destino_final/justificación.
    Si no hay decisión armada, se construye a partir de esos campos, siempre con
    auditoría humana (fail-safe).
    """
    decision = estado.get("decision_enrutamiento")
    if decision is not None:
        return DecisionEnrutamiento.model_validate(_a_dict_json(decision))

    destino = estado.get("destino_final")
    if not destino:
        raise AgenteError("El agente terminó sin una decisión de enrutamiento.")
    return DecisionEnrutamiento(
        destino_principal=DestinoEnrutamiento(destino),
        requiere_auditoria_humana=True,
        justificacion_enrutamiento=estado.get("justificacion_enrutamiento")
        or "Derivado a revisión humana por el agente.",
        notificacion_generada=None,
    )


def ejecutar_agente(documento: DocumentoClinicoRequest) -> ResultadoAgente:
    """Corre el grafo real sobre el documento y devuelve el resultado en schemas del Backend."""
    grafo = _cargar_grafo()

    try:
        estado = grafo.invoke(
            {
                "document_id": documento.documento_id,
                "document_text": documento.documento_texto,
                "origin_channel": documento.canal_origen,
            }
        )
    except ValueError as exc:
        # llm_provider levanta ValueError cuando falta una API key o el proveedor es inválido.
        raise AgenteError(f"Configuración del agente inválida: {exc}", 503) from exc
    except Exception as exc:
        logger.exception("El grafo del agente falló para %s", documento.documento_id)
        raise AgenteError(f"El agente no pudo procesar el documento: {exc}") from exc

    try:
        if estado.get("classification") is None or estado.get("extracted_data") is None:
            raise AgenteError("El agente terminó sin clasificación o sin datos extraídos.")

        clasificacion = Clasificacion.model_validate(_a_dict_json(estado["classification"]))

        datos = _a_dict_json(estado["extracted_data"])
        # Schema del agente: `Paciente.nombre: Optional[str] = None,` (coma sobrante) deja el
        # default como la tupla (None,). Se normaliza a None para no romper el contrato.
        paciente = datos.get("paciente") or {}
        if not isinstance(paciente.get("nombre"), str):
            paciente["nombre"] = None
        datos_extraidos = DatosExtraidos.model_validate(datos)

        decision = _decision_desde_estado(estado)
    except AgenteError:
        raise
    except Exception as exc:
        raise AgenteError(
            f"La salida del agente no coincide con el schema del Backend: {exc}"
        ) from exc

    # La prioridad que manda es la del Nodo 2 (reglas determinísticas), no la del LLM de
    # clasificación; así `clasificacion.nivel_prioridad` es coherente con el destino.
    nivel = estado.get("nivel_prioridad")
    if nivel:
        try:
            clasificacion.nivel_prioridad = NivelPrioridad(nivel)
        except ValueError:
            logger.warning("Nodo 2 devolvió nivel_prioridad desconocido: %r", nivel)

    return ResultadoAgente(
        clasificacion=clasificacion,
        datos_extraidos=datos_extraidos,
        decision_enrutamiento=decision,
        score_confianza=estado.get("final_confidence_score"),
    )
