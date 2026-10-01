from typing import Optional, TypedDict

from schemas import Clasificacion, DatosExtraidos

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

    # ---- Manejo de errores (para no romper el grafo si un nodo falla)
    error: Optional[str]
