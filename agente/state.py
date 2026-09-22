from typing import Optional, TypedDict

from schemas import Clasificacion, DatosExtraidos

class AgentState(TypedDict, total=False):
    # ---- Input (desde el endpoint de Backend)
    document_id: str
    document_text: str
    origin_channel: str

    # ---- Completado en el nodo de Clasificación
    classification: Optional[Clasificacion]

    # ---- Completado en el nodo de Extracción
    extracted_data: Optional[DatosExtraidos]

    # ---- Completado en el nodo de score de confianza / urgencia
    final_confidence_score: Optional[float]
    requires_human_review: Optional[bool]

    # ---- Manejo de errores (para no romper el grafo si un nodo falla)
    error: Optional[str]
