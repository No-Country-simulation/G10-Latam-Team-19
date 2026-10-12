"""
main.py — MediFlow API (FastAPI)

Backend para triaje, extracción y enrutamiento inteligente de documentos clínicos.
Conectado con OCI Object Storage y listo para consumo directo desde Next.js.

Endpoints:
    - POST /triage                          -> Procesa y clasifica un documento clínico.
    - GET  /triage                          -> Retorna el historial de documentos procesados (para /historial).
    - GET  /triage/{documento_id}           -> Obtiene el detalle de triaje de un documento (para /triaje/[id]).
    - POST /triage/{documento_id}/aprobar   -> Aprueba un doc en cola de auditoría, lo mueve a /validados/.
    - POST /triage/{documento_id}/rechazar  -> Rechaza un doc en cola de auditoría (queda marcado, sin mover).
    - GET  /health                          -> Healthcheck del servicio.
"""


from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
from app.services.agente import AgenteError, ejecutar_agente
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
        status="procesados",
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
        status="procesados",
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


class RevisionHumanaRequest(BaseModel):
    """
    Body opcional para aprobar/rechazar. Definido acá (no en schemas.py)
    porque es un detalle del endpoint de auditoría, no parte del contrato
    compartido con Agente/Frontend.
    """
    comentario: str | None = None
    revisor: str | None = None


# -----------------------------
# Helpers de persistencia (OCI)
# -----------------------------

def _contenido_oci(doc: TriageResponse, revision: RevisionHumanaRequest | None = None) -> dict:
    """
    JSON que se guarda en OCI: el TriageResponse completo (menos `almacenamiento_oci`, que
    describe justamente dónde quedó guardado) para poder rehidratarlo luego.
    """
    contenido = doc.model_dump(mode="json", exclude={"almacenamiento_oci"})
    if revision is not None:
        contenido["revision_humana"] = {
            **revision.model_dump(),
            "decision": doc.decision_auditoria,
            "fecha": datetime.now(timezone.utc).isoformat(),
        }
    return contenido


def _oci_o_none():
    """Devuelve el servicio OCI, o None si las credenciales no están configuradas (modo local)."""
    try:
        return get_oci_service()
    except ValueError as exc:
        logger.warning("OCI no configurado (%s). Continuando en modo local.", exc)
        return None


def _cargar_documento(documento_id: str) -> TriageResponse | None:
    """Busca el documento en memoria y, si no está (p. ej. tras reiniciar), en OCI."""
    if documento_id in _DOCUMENTOS_STORE:
        return _DOCUMENTOS_STORE[documento_id]

    oci_service = _oci_o_none()
    if oci_service is None:
        return None
    try:
        encontrado = oci_service.buscar_documento_triage(documento_id)
        if encontrado is None:
            return None
        ruta, data = encontrado
        doc = TriageResponse.model_validate(data)
        doc.almacenamiento_oci = AlmacenamientoOCI(
            bucket=get_settings().OCI_BUCKET, ruta_objeto=ruta, status_backup="exito"
        )
        _DOCUMENTOS_STORE[documento_id] = doc
        return doc
    except Exception as exc:
        logger.warning("No se pudo rehidratar '%s' desde OCI (%s).", documento_id, exc)
        return None


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
    Recibe un documento clínico, guarda el crudo en OCI (/recibidos/), lo procesa con el
    grafo real del Agente y guarda el resultado en /procesados/ o /auditoria_humana/ según
    `decision_enrutamiento.requiere_auditoria_humana` (decidido por el grafo).
    """
    # 1. Persistir documento crudo (/recibidos/) antes de procesar
    oci_service = _oci_o_none()
    backup_recibido = "pendiente"
    if oci_service is not None:
        try:
            oci_service.guardar_documento_recibido(
                documento_id=documento.documento_id,
                texto_original=documento.documento_texto,
            )
            backup_recibido = "exito"
        except Exception as exc:
            logger.warning("No se pudo guardar el crudo en OCI (%s).", exc)
            backup_recibido = "fallido"

    # 2. Agente real (grafo LangGraph)
    try:
        resultado = ejecutar_agente(documento)
    except AgenteError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detalle) from exc

    # 3. El bucket sale de la decisión real del grafo
    estado = (
        EstadoDocumento.AUDITORIA_HUMANA
        if resultado.decision_enrutamiento.requiere_auditoria_humana
        else EstadoDocumento.PROCESADO
    )
    respuesta = TriageResponse(
        status=estado.value,
        documento_id=documento.documento_id,
        canal_origen=documento.canal_origen,
        timestamp=datetime.now(timezone.utc),
        clasificacion=resultado.clasificacion,
        datos_extraidos=resultado.datos_extraidos,
        decision_enrutamiento=resultado.decision_enrutamiento,
    )

    ruta_objeto = f"{estado.value}/{documento.documento_id}.json"
    status_backup = "pendiente"
    if oci_service is not None:
        try:
            ruta_objeto = oci_service.guardar_json(
                documento_id=documento.documento_id,
                contenido=_contenido_oci(respuesta),
                estado=estado,
            )
            status_backup = "exito"
        except Exception as exc:
            logger.warning("No se pudo guardar '%s' en OCI (%s).", documento.documento_id, exc)
            status_backup = "fallido"
    elif backup_recibido == "fallido":
        status_backup = "fallido"

    respuesta.almacenamiento_oci = AlmacenamientoOCI(
        bucket=get_settings().OCI_BUCKET,
        ruta_objeto=ruta_objeto,
        status_backup=status_backup,
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
def listar_historial_triage(estado: EstadoDocumento | None = None) -> list[TriageResponse]:
    """
    Listado para /historial. Con `?estado=auditoria_humana` devuelve solo la cola de
    auditoría humana (pantalla /auditoria). Más recientes primero.
    """
    docs = list(_DOCUMENTOS_STORE.values())
    if estado is not None:
        docs = [d for d in docs if d.status == estado.value]
    return sorted(docs, key=lambda d: d.timestamp, reverse=True)


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
    doc = _cargar_documento(documento_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento clínico con ID '{documento_id}' no encontrado.",
        )
    return doc


def _obtener_doc_en_auditoria(documento_id: str) -> TriageResponse:
    """Busca el documento y valida que esté en cola de auditoría humana."""
    doc = _cargar_documento(documento_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento clínico con ID '{documento_id}' no encontrado.",
        )
    if doc.status != EstadoDocumento.AUDITORIA_HUMANA.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El documento '{documento_id}' no está en cola de auditoría humana "
                f"(estado actual: '{doc.status}')."
            ),
        )
    return doc


def _resolver_auditoria(
    documento_id: str,
    decision: str,
    revision: RevisionHumanaRequest | None,
) -> TriageResponse:
    """
    Aplica la decisión del revisor. Primero se persiste en OCI y recién después se actualiza
    la copia en memoria: si OCI falla (estando configurado) se responde 502 y el caso sigue
    pendiente, para no declarar "validado" un documento que sigue en /auditoria_humana/.
    Sin credenciales de OCI (modo local) solo se actualiza la memoria.
    """
    doc = _obtener_doc_en_auditoria(documento_id).model_copy(deep=True)
    aprobado = decision == "aprobado"
    etiqueta = "Aprobado" if aprobado else "Rechazado"

    doc.decision_auditoria = decision
    doc.timestamp = datetime.now(timezone.utc)
    if aprobado:
        doc.status = EstadoDocumento.VALIDADO.value
        doc.decision_enrutamiento.requiere_auditoria_humana = False
    # rechazado: sigue en auditoria_humana (no hay carpeta /rechazados/ en el brief)
    if revision and revision.comentario:
        quien = f" ({revision.revisor})" if revision.revisor else ""
        doc.decision_enrutamiento.justificacion_enrutamiento += (
            f" | {etiqueta} por revisor humano{quien}: {revision.comentario}"
        )

    ruta_objeto = f"{doc.status}/{documento_id}.json"
    status_backup = "pendiente"
    oci_service = _oci_o_none()
    if oci_service is not None:
        try:
            contenido = _contenido_oci(doc, revision or RevisionHumanaRequest())
            if aprobado:
                ruta_objeto = oci_service.mover_a_validados(documento_id, contenido)
            else:
                ruta_objeto = oci_service.guardar_json(
                    documento_id=documento_id,
                    contenido=contenido,
                    estado=EstadoDocumento.AUDITORIA_HUMANA,
                )
            status_backup = "exito"
        except Exception as exc:
            logger.error("OCI falló al resolver '%s' (%s).", documento_id, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"No se pudo actualizar el documento en OCI: {exc}",
            ) from exc

    doc.almacenamiento_oci = AlmacenamientoOCI(
        bucket=get_settings().OCI_BUCKET,
        ruta_objeto=ruta_objeto,
        status_backup=status_backup,
    )
    _DOCUMENTOS_STORE[documento_id] = doc
    return doc


@app.post(
    "/triage/{documento_id}/aprobar",
    response_model=TriageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Auditoría Humana"],
    summary="Aprobar un documento en cola de auditoría humana",
)
def aprobar_documento(documento_id: str, revision: RevisionHumanaRequest | None = None) -> TriageResponse:
    """
    Aprueba un documento pendiente de revisión: lo mueve de /auditoria_humana/ a /validados/
    en OCI y devuelve `status="validados"`, `decision_auditoria="aprobado"`.
    No recalcula clasificación, score ni enrutamiento.
    """
    return _resolver_auditoria(documento_id, "aprobado", revision)


@app.post(
    "/triage/{documento_id}/rechazar",
    response_model=TriageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Auditoría Humana"],
    summary="Rechazar un documento en cola de auditoría humana",
)
def rechazar_documento(documento_id: str, revision: RevisionHumanaRequest | None = None) -> TriageResponse:
    """
    Rechaza un documento pendiente de revisión. Permanece en /auditoria_humana/ (el brief no
    define /rechazados/) con `decision_auditoria="rechazado"`; `status` sigue en
    "auditoria_humana". Un caso rechazado puede aprobarse después (segunda revisión).
    """
    return _resolver_auditoria(documento_id, "rechazado", revision)
