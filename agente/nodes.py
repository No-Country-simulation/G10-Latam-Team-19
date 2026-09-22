from state import AgentState

def classification_node(state: AgentState) -> dict:
    """
    Clasifica el documento: tipo_documento, especialidad, nivel_prioridad
    y score_confianza_clasificacion.

    TODO (Jairo): Armar el prompt real, llamar get_llm(), parsear la respuesta y validarla contra 'Clasificacion' de schemas.py
    """

    document_text = state["document_text"]

    raise NotImplementedError(
        "TODO (Jairo): implementar classification_node con la llamada real al LLM"
    )

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
