from state import AgentState

def classification_node(state: AgentState) -> dict:
    """
    Clasifica el documento: tipo_documento, especialidad, nivel_prioridad
    y score_confianza_clasificacion.

    Estrategia de dos capas:
    1. Structured output nativo (llm.with_structured_output): el proveedor fuerza la respuesta
       al hacer match con el modelo Clasificacion vía tool-calling.
       Es más confiable, y nos ahorra más parseo manual.

    2. Fallback: Si structured output no está soportado por el proveedor o la llamada falla, se
       reintenta con invoke() plano + parseo manual de JSON + validación Pydantic explícita.

    Si ambas capas fallan, NO se inventa una clasificación por defecto, sino que se levanta un error explícito
    para que el caso termine en revisión humana en vez de avanzar con datos falsos.
    """
    import json
    import re

    from schemas import Clasificacion
    from llm_provider import get_llm
    from prompts import build_classification_prompt
    
    document_text = state["document_text"]
    messages = build_classification_prompt(document_text=document_text)
    llm = get_llm()

    # Capa 1: Structured output nativo
    try:
        structured_llm = llm.with_structured_output(Clasificacion)
        classification = structured_llm.invoke(messages)
        return {"classification": classification}
    except Exception as structured_error:
        fallback_reason = f"structured_output falló: {structured_error}"

    # Capa 2: invoke plano + parseo manual
    try:
        response = llm.invoke(messages)
        text = response.content.strip()
        # Por si el modelo envuelve el JSON en un FencedCodeBlock de todas formas.
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        classification = Clasificacion.model_validate(data)
        return {"classification": classification}
    except Exception as fallback_error:
        raise RuntimeError(
            "classification_node: fallaron structured output y el fallback manual. "
            f"Motivo structured: {fallback_reason}. "
            f"Motivo fallback: {fallback_error}. "
            "No se generó una clasificación por defecto a propósito. "
            "Este caso debería derivarse a revisión humana, no seguir con datos falsos."
        ) from fallback_error

def extraction_node(state: AgentState) -> dict:
    """
    Extrae los datos clínicos estructurados (paciente, médico, diagnóstico, CIE-10, etcétera),
    validados contra el modelo 'DatosExtraidos' de schemas.py

    TODO (Seylin): Armar el prompt real, llamar get_llm(), parsear y validar.
    """

    document_text = state["document_text"]
    classification = state.get("classification")

    raise NotImplementedError(
        "TODO (Seylin): implementar extraction_node con la llamada real al LLM"
    )

def confidence_node(state: AgentState) -> dict:
    """
    Calcula el score de confianza final y si el caso requiere revisión humana.
    Modo de cálculo a definir con el equipo de Datos.

    TODO (Natalia): Este nodo NO se implementa hasta tener la matriz de decisión definitiva
                    de datos (umbral de score, reglas de urgencia automática, mapeo score+prioridad -> destino).
    """
    classification = state.get("classification")
    extracted_data = state.get("extracted_data")

    raise NotImplementedError(
        "TODO (Ilana): pendiente de la matriz de decisión del equipo de Datos."
    )
