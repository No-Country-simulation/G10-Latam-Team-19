"""
main.py — MediFlow API (FastAPI)

Esqueleto inicial del backend para triaje, extracción y enrutamiento
de documentos clínicos.

Flujo del endpoint POST /triage:
    1. Validar entrada con DocumentoClinicoRequest
    2. Persistir documento crudo en OCI -> /recibidos/
    3. Clasificar, extraer y enrutar (preparado para integración con Agente)
    4. Persistir resultado procesado en OCI -> /procesados/ o /auditoria_humana/
    5. Devolver TriageResponse validado con Pydantic
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.schemas import (
    AlmacenamientoOCI,
    Clasificacion,
    DatosExtraidos,
    DecisionEnrutamiento,
    DestinoEnrutamiento,
    DocumentoClinicoRequest,
    EstadoDocumento,
    MedicoSolicitante,
    NivelPrioridad,
    NotificacionGenerada,
    Paciente,
    TipoDocumento,
    TriageResponse,
)
from app.services.oci_storage import get_oci_service

logger = logging.getLogger("mediflow")

app = FastAPI(
    title="MediFlow API",
    description="Agente autónomo para triaje, extracción y enrutamiento de documentos clínicos.",
    version="0.1.0",
)

# CORS abierto para desarrollo del MVP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check():
    """Endpoint de salud para monitorización del servicio."""
    return {"status": "ok", "service": "mediflow-api", "timestamp": datetime.now(timezone.utc)}


@app.post(
    "/triage",
    response_model=TriageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Triaje"],
    summary="Procesar y clasificar documento clínico",
)
def triage_documento(documento: DocumentoClinicoRequest) -> TriageResponse:
    """
    Recibe un documento clínico, guarda el documento crudo en OCI (/recibidos/),
    procesa la información y devuelve el resultado de triaje en formato TriageResponse.
    """
    ruta_recibido: str | None = None
    backup_recibido_status = "pendiente"

    # 1. Intentar persistir el crudo en OCI Object Storage (/recibidos/)
    try:
        oci_service = get_oci_service()
        ruta_recibido = oci_service.guardar_documento_recibido(
            documento_id=documento.documento_id,
            texto_original=documento.documento_texto,
        )
        backup_recibido_status = "exito"
    except Exception as exc:
        logger.warning("No se pudo conectar a OCI o guardar crudo (%s). Continuando en modo local.", exc)
        backup_recibido_status = "no_configurado_o_fallido"

    # 2. Esqueleto de triaje inicial (a conectar con el equipo de Agente / LangGraph)
    # Por defecto inicializamos con una estructura base válida según schemas.py
    clasificacion = Clasificacion(
        tipo_documento=TipoDocumento.INFORME_ESTUDIO,
        especialidad="Medicina General",
        nivel_prioridad=NivelPrioridad.RUTINA,
        score_confianza_clasificacion=0.95,
    )

    datos_extraidos = DatosExtraidos(
        paciente=Paciente(nombre="Paciente Pendiente de Extracción", edad=None),
        medico_solicitante=MedicoSolicitante(nombre="Dr. No especificado", matricula=None),
        estudio_realizado=None,
        diagnostico_principal="Pendiente de análisis por Agente",
        cie10_sugerido=None,
    )

    decision_enrutamiento = DecisionEnrutamiento(
        destino_principal=DestinoEnrutamiento.HISTORIA_CLINICA,
        requiere_auditoria_humana=False,
        justificacion_enrutamiento="Documento recibido y encolado para procesamiento.",
        notificacion_generada=None,
    )

    # 3. Determinar carpeta y respaldar resultado en OCI si está disponible
    estado = (
        EstadoDocumento.AUDITORIA_HUMANA
        if decision_enrutamiento.requiere_auditoria_humana
        else EstadoDocumento.PROCESADO
    )
    
    ruta_objeto_procesado = f"{estado.value}/{documento.documento_id}.json"
    status_backup = "pendiente"

    try:
        oci_service = get_oci_service()
        resultado_dict = {
            "documento_id": documento.documento_id,
            "canal_origen": documento.canal_origen,
            "tipo_archivo": documento.tipo_archivo.value,
            "clasificacion": clasificacion.model_dump(),
            "datos_extraidos": datos_extraidos.model_dump(),
            "decision_enrutamiento": decision_enrutamiento.model_dump(),
        }
        ruta_objeto_procesado = oci_service.guardar_json(
            documento_id=documento.documento_id,
            contenido=resultado_dict,
            estado=estado,
        )
        status_backup = "exito"
    except Exception:
        status_backup = "pendiente" if backup_recibido_status == "no_configurado_o_fallido" else "fallido"

    # 4. Respuesta estructurada
    return TriageResponse(
        status="procesado",
        documento_id=documento.documento_id,
        timestamp=datetime.now(timezone.utc),
        clasificacion=clasificacion,
        datos_extraidos=datos_extraidos,
        decision_enrutamiento=decision_enrutamiento,
        almacenamiento_oci=AlmacenamientoOCI(
            bucket=get_settings().OCI_BUCKET,
            ruta_objeto=ruta_objeto_procesado,
            status_backup=status_backup,
        ),
    )
