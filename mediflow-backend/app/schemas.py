from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# -----------------------------
# Enums: valores cerrados para evitar que el LLM invente categorías nuevas
# -----------------------------

class TipoArchivo(str, Enum):
    PDF = "PDF"
    IMAGEN = "IMAGEN"
    TEXTO = "TEXTO"
    JSON = "JSON"

class TipoDocumento(str, Enum):
    RECETA_MEDICA = "Receta Medica"
    INFORME_ESTUDIO = "Informe de Estudio"
    INFORME_LABORATORIO = "Informe de Laboratorio"
    ORDEN_PROCEDIMIENTO = "Orden de Solicitud de Procedimiento"
    EPICRISIS = "Epicrisis / Informe de Alta"
    CERTIFICADO_MEDICO = "Certificado Medico"
    DESCONOCIDO = "Desconocido"

class NivelPrioridad(str, Enum):
    RUTINA = "Rutina"
    PRIORITARIO = "Prioritario"
    URGENTE = "Urgente"

class EstadoDocumento(str, Enum):
    RECIBIDO = "recibidos"
    PROCESADO = "procesados"
    AUDITORIA_HUMANA = "auditoria_humana"
    VALIDADO = "validados"

class DestinoEnrutamiento(str, Enum):
    COLA_URGENCIAS = "Cola_Emergencia_Medica"
    AUDITORIA_AUTORIZACIONES = "Auditoria_Autorizaciones"
    FARMACIA_HOSPITALARIA = "Farmacia_Hospitalaria"
    REVISION_HUMANA = "Cola_Revision_Humana"
    HISTORIA_CLINICA = "Historia_Clinica_Electronica"


# -------------------
# Request: Lo que llega al endpoint
# --------------------

class DocumentoClinicoRequest(BaseModel):
    documento_id: str = Field(..., examples=["DOC-CLIN-2026-8942"])
    tipo_archivo: TipoArchivo
    documento_texto: str = Field(
        ...,
        min_length=10,
        description="Texto del documento",
    )
    canal_origen: str = Field(..., examples=["Guardia_Emergencias"])

    @field_validator("documento_texto")
    @classmethod
    def texto_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("documento_texto no puede estar vacío")
        return v

# --------------------
# Sub-modelos de la respuesta
# --------------------

class Clasificacion(BaseModel):
    tipo_documento: TipoDocumento
    especialidad: str = Field(..., examples=["Radiología / Neumonología"])
    nivel_prioridad: NivelPrioridad
    score_confianza_clasificacion: float = Field(..., ge=0.0, le=1.0)

class Paciente(BaseModel):
    nombre: str
    edad: Optional[int] = Field(None, ge=0, le=130)

class MedicoSolicitante(BaseModel):
    nombre: str
    matricula: Optional[str] = None

class DatosExtraidos(BaseModel):
    paciente: Paciente
    medico_solicitante: Optional[MedicoSolicitante] = None
    estudio_realizado: Optional[str] = None
    diagnostico_principal: Optional[str] = None
    cie10_sugerido: Optional[str] = Field(
        None,
        pattern=r"^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$",
        description="Código CIE-10, ej: I26.9"
    )
    medicamentos: Optional[list[str]] = None
    dosis: Optional[list[str]] = None

class NotificacionGenerada(BaseModel):
    canal: str = Field(..., examples=["Alerta_Guardia_Medica"])
    mensaje: str

class DecisionEnrutamiento(BaseModel):
    destino_principal: DestinoEnrutamiento
    requiere_auditoria_humana: bool
    justificacion_enrutamiento: str
    notificacion_generada: Optional[NotificacionGenerada] = None

class AlmacenamientoOCI(BaseModel):
    bucket: str = Field(default="mediflow-documentos-clinicos")
    ruta_objeto: str
    status_backup: str = Field(default="pendiente")


# --------------------
# Response: lo que devuelve el endpoint (y lo que persiste el agente)
# --------------------

class TriageResponse(BaseModel):
    status: str = Field(default="procesado")
    documento_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    clasificacion: Clasificacion
    datos_extraidos: DatosExtraidos
    decision_enrutamiento: DecisionEnrutamiento
    almacenamiento_oci: Optional[AlmacenamientoOCI] = None


# --------------------
# Auto-test para corroborar que este archivo funciona
# --------------------

if __name__ == "__main__":
    ejemplo = {
        "status": "procesado",
        "documento_id": "DOC-CLIN-2026-8942",
        "clasificacion": {
            "tipo_documento": "Informe de Estudio",
            "especialidad": "Radiologia / Neumonologia",
            "nivel_prioridad": "Urgente",
            "score_confianza_clasificacion": 0.99,
        },
        "datos_extraidos": {
            "paciente": {"nombre": "Carlos Eduardo Mendes", "edad": 52},
            "medico_solicitante": {"nombre": "Dra. Renata Silveira", "matricula": "145892"},
            "estudio_realizado": "Tomografia de Torax con contraste",
            "diagnostico_principal": "Tromboembolismo Pulmonar Agudo (TEP)",
            "cie10_sugerido": "I26.9",
        },
        "decision_enrutamiento": {
            "destino_principal": "Cola_Emergencia_Medica",
            "requiere_auditoria_humana": False,
            "justificacion_enrutamiento": "Hallazgo critico de alta gravedad (TEP agudo).",
            "notificacion_generada": {
                "canal": "Alerta_Guardia_Medica",
                "mensaje": "ALERTA URGENTE: TEP Agudo para Carlos Eduardo Mendes.",
            },
        },
        "almacenamiento_oci": {
            "bucket": "mediflow-documentos-clinicos",
            "ruta_objeto": "procesados/urgentes/DOC-CLIN-2026-8942.json",
            "status_backup": "exito",
        },
    }
 
    respuesta = TriageResponse(**ejemplo)
    print("[OK] Schema valido. Ejemplo parseado correctamente:")
    print(respuesta.model_dump_json(indent=2))
