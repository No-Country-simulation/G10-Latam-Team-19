"""
main.py — MediFlow API (FastAPI)

Backend para triaje, extracción y enrutamiento inteligente de documentos clínicos.
Conectado con OCI Object Storage y listo para consumo directo desde Next.js.

Endpoints:
    - POST /triage                -> Procesa y clasifica un documento clínico.
    - GET  /triage                -> Retorna el historial de documentos procesados (para /historial).
    - GET  /triage/{documento_id} -> Obtiene el detalle de triaje de un documento (para /triaje/[id]).
    - GET  /health                -> Healthcheck del servicio.
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
    MedicamentoPrescrito,
    MedicoSolicitante,
    NivelPrioridad,
    NotificacionGenerada,
    Paciente,
    SignosVitales,
    TipoDocumento,
    TriageResponse,
    UnidadEdad,
)
from app.services.oci_storage import get_oci_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mediflow")

app = FastAPI(
    title="MediFlow API",
    description="Agente autónomo para triaje, extracción y enrutamiento de documentos clínicos.",
    version="0.2.0",
)

# -----------------------------
# CORS habilitado para Next.js (localhost:3000)
# -----------------------------
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Repositorio en memoria con datos iniciales (Mock) para Frontend
# -----------------------------
_DOCUMENTOS_STORE: dict[str, TriageResponse] = {
    "DOC-CLIN-2026-8942": TriageResponse(
        status="procesado",
        documento_id="DOC-CLIN-2026-8942",
        canal_origen="Guardia_Emergencias",
        timestamp=datetime(2026, 9, 30, 14, 20, 0, tzinfo=timezone.utc),
        clasificacion=Clasificacion(
            tipo_documento=TipoDocumento.INFORME_ESTUDIO,
            especialidad="Radiologia / Neumonologia",
            nivel_prioridad=NivelPrioridad.URGENTE,
            score_confianza_clasificacion=0.99,
        ),
        datos_extraidos=DatosExtraidos(
            paciente=Paciente(
                nombre="Carlos Eduardo Mendes",
                edad=52,
                unidad_edad=UnidadEdad.ANOS,
                sexo="M",
                documento_identidad="AB123456",
            ),
            medico_solicitante=MedicoSolicitante(
                nombre="Dra. Renata Silveira",
                matricula="145892",
            ),
            estudio_realizado="Tomografia de Torax con contraste",
            diagnostico_principal="Tromboembolismo Pulmonar Agudo (TEP)",
            cie10_sugerido="I26.9",
            medicamentos=[
                MedicamentoPrescrito(
                    nombre="Enoxaparina",
                    dosis="80 mg",
                    frecuencia_diaria="2 veces al día",
                )
            ],
            signos_vitales=SignosVitales(
                temperatura=37.5,
                frecuencia_cardiaca=115,
                frecuencia_respiratoria=28,
                presion_arterial="140/90",
                saturacion_oxigeno=88,
            ),
        ),
        decision_enrutamiento=DecisionEnrutamiento(
            destino_principal=DestinoEnrutamiento.COLA_URGENCIAS,
            requiere_auditoria_humana=False,
            justificacion_enrutamiento="Hallazgo critico de alta gravedad (TEP agudo) y desaturación (88%).",
            notificacion_generada=NotificacionGenerada(
                canal="Alerta_Guardia_Medica",
                mensaje="ALERTA URGENTE: TEP Agudo para Carlos Eduardo Mendes.",
            ),
        ),
        almacenamiento_oci=AlmacenamientoOCI(
            bucket="mediflow-documentos-clinicos",
            ruta_objeto="procesados/urgentes/DOC-CLIN-2026-8942.json",
            status_backup="exito",
        ),
    ),
    "DOC-CLIN-2026-3105": TriageResponse(
        status="auditoria_humana",
        documento_id="DOC-CLIN-2026-3105",
        canal_origen="Consultorios_Externos",
        timestamp=datetime(2026, 9, 30, 11, 15, 0, tzinfo=timezone.utc),
        clasificacion=Clasificacion(
            tipo_documento=TipoDocumento.RECETA_MEDICA,
            especialidad="Cardiologia",
            nivel_prioridad=NivelPrioridad.PRIORITARIO,
            score_confianza_clasificacion=0.72,
        ),
        datos_extraidos=DatosExtraidos(
            paciente=Paciente(
                nombre="Elena Beatriz Gomez",
                edad=67,
                unidad_edad=UnidadEdad.ANOS,
                sexo="F",
                documento_identidad="CD987654",
            ),
            medico_solicitante=MedicoSolicitante(
                nombre="Dr. Javier Dominguez",
                matricula="54128",
            ),
            estudio_realizado=None,
            diagnostico_principal="Insuficiencia Cardiaca Congestiva",
            cie10_sugerido="I50.9",
            medicamentos=[
                MedicamentoPrescrito(
                    nombre="Furosemida",
                    dosis="40 mg",
                    frecuencia_diaria="1 comprimido por la manana",
                ),
                MedicamentoPrescrito(
                    nombre="Carvedilol",
                    dosis="6.25 mg",
                    frecuencia_diaria="Cada 12 horas",
                ),
            ],
            signos_vitales=SignosVitales(
                temperatura=36.4,
                frecuencia_cardiaca=82,
                frecuencia_respiratoria=20,
                presion_arterial="130/85",
                saturacion_oxigeno=94,
            ),
        ),
        decision_enrutamiento=DecisionEnrutamiento(
            destino_principal=DestinoEnrutamiento.REVISION_HUMANA,
            requiere_auditoria_humana=True,
            justificacion_enrutamiento="Score de confianza (0.72) por debajo del umbral automatico.",
            notificacion_generada=NotificacionGenerada(
                canal="Cola_Revision_Humana",
                mensaje="Revision pendiente para paciente Elena Beatriz Gomez.",
            ),
        ),
        almacenamiento_oci=AlmacenamientoOCI(
            bucket="mediflow-documentos-clinicos",
            ruta_objeto="auditoria_humana/DOC-CLIN-2026-3105.json",
            status_backup="exito",
        ),
    ),
    "DOC-CLIN-2026-1044": TriageResponse(
        status="procesado",
        documento_id="DOC-CLIN-2026-1044",
        canal_origen="Pediatria_Ambulatoria",
        timestamp=datetime(2026, 9, 30, 9, 45, 0, tzinfo=timezone.utc),
        clasificacion=Clasificacion(
            tipo_documento=TipoDocumento.INFORME_LABORATORIO,
            especialidad="Pediatria / Infectologia",
            nivel_prioridad=NivelPrioridad.RUTINA,
            score_confianza_clasificacion=0.96,
        ),
        datos_extraidos=DatosExtraidos(
            paciente=Paciente(
                nombre="Mateo Valentino Rossi",
                edad=8,
                unidad_edad=UnidadEdad.MESES,
                sexo="M",
                documento_identidad="PE458123",
            ),
            medico_solicitante=MedicoSolicitante(
                nombre="Dra. Mariana Benitez",
                matricula="88741",
            ),
            estudio_realizado="Hemograma completo y PCR",
            diagnostico_principal="Cuadro viral agudo de vias respiratorias superiores",
            cie10_sugerido="J06.9",
            medicamentos=[
                MedicamentoPrescrito(
                    nombre="Paracetamol Gotas",
                    dosis="15 gotas",
                    frecuencia_diaria="Cada 6 horas si fiebre",
                )
            ],
            signos_vitales=SignosVitales(
                temperatura=38.2,
                frecuencia_cardiaca=128,
                frecuencia_respiratoria=34,
                presion_arterial="90/60",
                saturacion_oxigeno=97,
            ),
        ),
        decision_enrutamiento=DecisionEnrutamiento(
            destino_principal=DestinoEnrutamiento.HISTORIA_CLINICA,
            requiere_auditoria_humana=False,
            justificacion_enrutamiento="Informe de laboratorio pediatrico dentro de parametros virales esperados.",
            notificacion_generada=None,
        ),
        almacenamiento_oci=AlmacenamientoOCI(
            bucket="mediflow-documentos-clinicos",
            ruta_objeto="procesados/DOC-CLIN-2026-1044.json",
            status_backup="exito",
        ),
    ),
}


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
    backup_recibido_status = "pendiente"

    # 1. Persistir documento crudo en OCI Object Storage (/recibidos/)
    try:
        oci_service = get_oci_service()
        oci_service.guardar_documento_recibido(
            documento_id=documento.documento_id,
            texto_original=documento.documento_texto,
        )
        backup_recibido_status = "exito"
    except Exception as exc:
        logger.warning("No se pudo conectar a OCI o guardar crudo (%s). Continuando en modo local.", exc)
        backup_recibido_status = "no_configurado_o_fallido"

    # 2. Mock estructurado según el nuevo schemas.py
    clasificacion = Clasificacion(
        tipo_documento=TipoDocumento.INFORME_ESTUDIO,
        especialidad="Radiologia / Neumonologia",
        nivel_prioridad=NivelPrioridad.URGENTE,
        score_confianza_clasificacion=0.99,
    )

    datos_extraidos = DatosExtraidos(
        paciente=Paciente(
            nombre="Carlos Eduardo Mendes",
            edad=52,
            unidad_edad=UnidadEdad.ANOS,
            sexo="M",
            documento_identidad="AB123456",
        ),
        medico_solicitante=MedicoSolicitante(nombre="Dra. Renata Silveira", matricula="145892"),
        estudio_realizado="Tomografia de Torax con contraste",
        diagnostico_principal="Tromboembolismo Pulmonar Agudo (TEP)",
        cie10_sugerido="I26.9",
        medicamentos=[
            MedicamentoPrescrito(nombre="Enoxaparina", dosis="80 mg", frecuencia_diaria="2 veces al día")
        ],
        signos_vitales=SignosVitales(
            temperatura=37.5,
            frecuencia_cardiaca=115,
            frecuencia_respiratoria=28,
            presion_arterial="140/90",
            saturacion_oxigeno=88,
        ),
    )

    decision_enrutamiento = DecisionEnrutamiento(
        destino_principal=DestinoEnrutamiento.COLA_URGENCIAS,
        requiere_auditoria_humana=False,
        justificacion_enrutamiento="Hallazgo critico de alta gravedad (TEP agudo) y desaturación (88%).",
        notificacion_generada=NotificacionGenerada(
            canal="Alerta_Guardia_Medica",
            mensaje=f"ALERTA URGENTE: TEP Agudo para Carlos Eduardo Mendes en {documento.canal_origen}.",
        ),
    )

    # 3. Guardar en OCI (/procesados/ o /auditoria_humana/)
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
            "status": estado.value,
            "documento_id": documento.documento_id,
            "canal_origen": documento.canal_origen,
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
    respuesta = TriageResponse(
        status=estado.value,
        documento_id=documento.documento_id,
        canal_origen=documento.canal_origen,
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

    _DOCUMENTOS_STORE[documento.documento_id] = respuesta
    return respuesta


@app.get(
    "/triage",
    response_model=list[TriageResponse],
    status_code=status.HTTP_200_OK,
    tags=["Triaje"],
    summary="Listar historial de documentos de triaje",
)
def listar_historial_triage() -> list[TriageResponse]:
    """
    Retorna el listado de documentos para la vista /historial de Frontend.
    """
    return list(_DOCUMENTOS_STORE.values())


@app.get(
    "/triage/{documento_id}",
    response_model=TriageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Triaje"],
    summary="Obtener detalle de triaje por ID de documento",
)
def obtener_documento_por_id(documento_id: str) -> TriageResponse:
    """
    Retorna el detalle de un documento clínico procesado para la ruta /triaje/[id].
    """
    if documento_id in _DOCUMENTOS_STORE:
        return _DOCUMENTOS_STORE[documento_id]

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Documento clínico con ID '{documento_id}' no encontrado.",
    )
