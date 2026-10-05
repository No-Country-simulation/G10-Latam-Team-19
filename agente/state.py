from typing import Optional, TypedDict

from schemas import Clasificacion, DatosExtraidos, DecisionEnrutamiento

class AgentState(TypedDict, total=False):
    # ---- Input (desde el endpoint de Backend)
    document_id: str
    document_text: str
    origin_channel: str

    # ---- Completado en el nodo de Clasificación
    classification: Optional[Clasificacion]

    # --- Completado en el nodo Extracción
    extracted_data: Optional[DatosExtraidos]
    # EXTRACCIÓN: nombre y edad ausentes, destacados por la instrucción de Michelle.
    missing_critical_fields: Optional[list[str]]
    # EXTRACCIÓN: detalle de todos los campos que explican los descuentos aplicados.
    missing_relevant_fields: Optional[list[str]]
    # PROVISIONAL: completitud de extracción; no sustituye final_confidence_score.
    extraction_confidence_score: Optional[float]

    # ---- Completado en el nodo de score de confianza / urgencia
    final_confidence_score: Optional[float]
    requires_human_review: Optional[bool]

    # ---- Completado en el Nodo 2 (priority.evaluate_priority)
    nivel_prioridad: Optional[str]
    destino_sugerido_nodo2: Optional[str]  # antes de aplicar la regla de score >= 0.90
    disparar_alerta: Optional[bool]
    forzar_auditoria: Optional[bool]
    datos_faltantes_nodo2: Optional[list[str]]

    # ---- Completado en el nodo de enrutamiento final
    destino_final: Optional[str]
    justificacion_enrutamiento: Optional[str]
    decision_enrutamiento: Optional[DecisionEnrutamiento]  # listo para TriageResponse

    # ---- Manejo de errores (para no romper el grafo si un nodo falla)
    error: Optional[str]
