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
    """Extrae y valida datos clínicos, y registra campos críticos ausentes."""
    import json

    from schemas import DatosExtraidos
    from llm_provider import get_llm
    from prompts import build_extraction_prompt

    document_text = state["document_text"]
    messages = build_extraction_prompt(document_text=document_text)
    llm = get_llm()
    # TEMPORAL: límite usado en pruebas con Groq; hoy se aplica a cualquier proveedor.
    # Revisarlo antes de usar documentos largos: puede truncar el JSON de respuesta.
    llm.max_tokens = 450

    # EXTRACCIÓN: ruta principal; Pydantic valida el contrato antes de calcular completitud.
    # Capa 1: respuesta estructurada.
    try:
        structured_llm = llm.with_structured_output(DatosExtraidos)
        result = structured_llm.invoke(messages)
        extracted_data = DatosExtraidos.model_validate(result)

    except Exception as structured_error:
        # EXTRACCIÓN: respaldo funcional, no una prueba temporal.
        # Permite validar JSON cuando falla o no se admite la respuesta estructurada.
        # Capa 2: respuesta JSON y validación manual.
        try:
            response = llm.invoke(messages)

            if not isinstance(response.content, str):
                raise ValueError("La respuesta del LLM no es texto.")

            text = response.content.strip()
            text = (
                text.removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )

            data = json.loads(text)
            extracted_data = DatosExtraidos.model_validate(data)

        except Exception as fallback_error:
            raise RuntimeError(
                "extraction_node: fallaron la respuesta estructurada "
                "y el parseo JSON alternativo. "
                f"Tipos de error: {type(structured_error).__name__} "
                f"y {type(fallback_error).__name__}. "
                "No se generaron datos de reemplazo."
            ) from fallback_error

    # EXTRACCIÓN / regla de Michelle: ausencias reducen la confianza de extracción.
    # Se aplica tras ambas rutas, sin cambiar DatosExtraidos ni exigir datos opcionales.
    # Los pesos son provisionales; el score final y la revisión humana son de otro nodo.
    # La misma regla determinista se aplica a ambas rutas de extracción.
    from confidence import confidence_score, missing_relevant_fields

    # Solo se consulta el tipo ya disponible; no se ejecuta ni modifica la clasificación.
    classification = state.get("classification")
    document_type = classification.tipo_documento if classification else None
    missing_fields = missing_relevant_fields(extracted_data, document_type)
    return {
        "extracted_data": extracted_data,
        "missing_critical_fields": [
            field for field in missing_fields
            if field in ("paciente.nombre", "paciente.edad")
        ],
        "missing_relevant_fields": missing_fields,
        "extraction_confidence_score": confidence_score(extracted_data, document_type),
    }


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
