"""Apoyo LLM al Nodo 2; errores de ambas rutas se propagan explícitamente."""
import json

from confidence import is_missing
from prompts import build_priority_support_prompt
from schemas import ApoyoPrioridad


def evaluate_clinical_support(diagnosis: str | None, study: str | None) -> ApoyoPrioridad:
    if is_missing(diagnosis) and is_missing(study):
        return ApoyoPrioridad(nivel_prioridad=None, justificacion="Sin diagnóstico ni estudio que aporten evidencia clínica.")

    from llm_provider import get_llm
    from nodes import _message_content_to_text

    llm = get_llm()
    messages = build_priority_support_prompt(diagnosis, study)
    try:
        result = llm.with_structured_output(ApoyoPrioridad).invoke(messages)
        return ApoyoPrioridad.model_validate(result)
    except Exception as structured_error:
        structured_type = type(structured_error).__name__

    try:
        response = llm.invoke(messages)
        text = _message_content_to_text(response.content).strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return ApoyoPrioridad.model_validate(json.loads(text))
    except Exception as fallback_error:
        raise RuntimeError(
            "priority_support: fallaron respuesta estructurada y fallback JSON. "
            f"Tipos de error: {structured_type} y {type(fallback_error).__name__}. "
            "No se generó una prioridad de reemplazo."
        ) from fallback_error
