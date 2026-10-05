from state import AgentState


def _message_content_to_text(content: object) -> str:
    """Por si el LLM devuelve el contenido en bloques en lugar de string."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                text_parts.append(block["text"])
        text = "".join(text_parts)
        if text:
            return text

    raise ValueError("La respuesta del LLM no contiene texto utilizable.")


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
        text = _message_content_to_text(response.content).strip()
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
    # Respetar la configuración del proveedor: el contrato anidado puede
    # superar el antiguo límite temporal de 450 tokens.

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

            text = _message_content_to_text(response.content).strip()
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
    # Pesos del PDF de Datos; condiciones pendientes en PESOS_PENDIENTES.md.
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
    Nodo 1 (filtro de confianza): el score que decide el gate NO es el que
    "inventa" el LLM en Clasificación, es el score determinístico que ya
    calculó Extracción (extraction_confidence_score), restando los pesos
    de Datos según qué campos faltan. Acá solo se promueve a
    final_confidence_score, que es el que usa la arista condicional.
    """
    score = state["extraction_confidence_score"]
    return {
        "final_confidence_score": score,
        # Banda Media (0.75-0.89) ya requiere auditoría por score; en banda
        # Alta esto puede pisarse después en el nodo final si el Nodo 2
        # detecta un medicamento restringido.
        "requires_human_review": score < 0.90,
    }


def corte_revision_humana_node(state: AgentState) -> dict:
    """
    Se activa solo cuando final_confidence_score < 0.75 (banda Baja).
    Corta el flujo automático: no se evalúa el Nodo 2, va directo a
    revisión humana.
    """
    score = state["final_confidence_score"]
    return {
        "requires_human_review": True,
        "destino_final": "Cola_Revision_Humana",
        "justificacion_enrutamiento": (
            f"Score de confianza bajo ({score:.2f} < 0.75): datos críticos "
            "faltantes, se detiene el procesamiento automático antes del Nodo 2."
        ),
    }


def priority_node(state: AgentState) -> dict:
    """
    Nodo 2 (Natalia): envuelve priority.evaluate_priority. Trabaja sobre
    datos_extraidos ya estructurado, no sobre documento_texto crudo, para
    evitar falsos positivos por negaciones (ej. "se descarta TEP").

    Nota: evaluate_priority no recibe el score ni lo necesita, según
    priority_config.json ("_decisiones_provisorias"). La regla de que
    Farmacia exige score >= 0.90 queda a cargo del nodo final, no de este.
    """
    from priority import evaluate_priority, load_config

    extracted_data = state["extracted_data"]
    config = load_config()
    result = evaluate_priority(extracted_data.model_dump(), config)

    return {
        "nivel_prioridad": result["nivel_prioridad"],
        "destino_sugerido_nodo2": result["destino_principal"],
        "disparar_alerta": result["disparar_alerta"],
        "forzar_auditoria": result["forzar_auditoria"],
        "datos_faltantes_nodo2": result["datos_faltantes"],
    }


def enrutamiento_final_node(state: AgentState) -> dict:
    """
    Arma la decisión definitiva combinando:
    - final_confidence_score (banda de confianza)
    - destino_sugerido_nodo2 (ya resuelve Urgente/Auditoría/Farmacia/Historia,
      pero asumiendo score alto)
    - forzar_auditoria (medicamento restringido -> puede pisar aunque el
      score sea perfecto)
    """
    from schemas import (
        DecisionEnrutamiento,
        DestinoEnrutamiento,
        NotificacionGenerada,
    )

    score = state["final_confidence_score"]
    destino_sugerido = state["destino_sugerido_nodo2"]
    forzar_auditoria = state.get("forzar_auditoria", False)
    disparar_alerta = state.get("disparar_alerta", False)
    nivel_prioridad = state["nivel_prioridad"]

    # Regla documentada por Natalia: Farmacia exige score Alto (>= 0.90).
    if destino_sugerido == DestinoEnrutamiento.FARMACIA_HOSPITALARIA.value and score < 0.90:
        destino_final = DestinoEnrutamiento.AUDITORIA_AUTORIZACIONES.value
    else:
        destino_final = destino_sugerido

    requiere_auditoria_final = (score < 0.90) or forzar_auditoria

    notificacion = None
    if disparar_alerta:
        notificacion = NotificacionGenerada(
            canal="Alerta_Guardia_Medica",
            mensaje=f"ALERTA: caso {nivel_prioridad} detectado, score {score:.2f}.",
        )

    justificacion = f"Score {score:.2f}, prioridad {nivel_prioridad}"
    if forzar_auditoria:
        justificacion += ", medicamento restringido detectado"
    if destino_final != destino_sugerido:
        justificacion += f" (Nodo 2 sugirió {destino_sugerido}, redirigido por score < 0.90 a Farmacia)"

    decision = DecisionEnrutamiento(
        destino_principal=DestinoEnrutamiento(destino_final),
        requiere_auditoria_humana=requiere_auditoria_final,
        justificacion_enrutamiento=justificacion,
        notificacion_generada=notificacion,
    )

    return {
        "destino_final": destino_final,
        "requires_human_review": requiere_auditoria_final,
        "justificacion_enrutamiento": justificacion,
        "decision_enrutamiento": decision,
    }
