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
    DocumentoClinicoRequest,
    EstadoDocumento,
    TriageResponse,
)
from app.services.agente import AgenteError, ejecutar_agente
from app.services.storage import StorageProvider, get_storage_service

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


def _obtener_storage_service() -> StorageProvider:
    """Devuelve el proveedor de almacenamiento (OCI con fallback automático a Cloudflare R2)."""
    return get_storage_service()


def _cargar_documento(documento_id: str) -> TriageResponse | None:
    """Busca y recupera el documento desde OCI o fallback a Cloudflare R2."""
    storage = _obtener_storage_service()
    try:
        encontrado = storage.buscar_documento_triage(documento_id)
        if encontrado is None:
            return None
        ruta, data = encontrado
        doc = TriageResponse.model_validate(data)
        doc.almacenamiento_oci = AlmacenamientoOCI(
            bucket=storage.get_active_bucket(),
            ruta_objeto=ruta,
            status_backup="exito",
        )
        return doc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("No se pudo obtener '%s' desde el almacenamiento (%s).", documento_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al consultar el almacenamiento (OCI/R2): {exc}",
        ) from exc


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
    storage = _obtener_storage_service()
    backup_recibido = "pendiente"
    try:
        storage.guardar_documento_recibido(
            documento_id=documento.documento_id,
            texto_original=documento.documento_texto,
        )
        backup_recibido = "exito"
    except Exception as exc:
        logger.warning("No se pudo guardar el crudo en almacenamiento (%s).", exc)
        backup_recibido = "fallido"

    # 2. Agente real (grafo LangGraph)
    try:
        resultado = ejecutar_agente(documento)
    except AgenteError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detalle,
            headers=exc.headers,
        ) from exc

    # 3. El bucket sale de la decisión real del grafo
    estado = (
        EstadoDocumento.AUDITORIA_HUMANA
        if resultado.decision_enrutamiento.requiere_auditoria_humana
        else EstadoDocumento.PROCESADO
    )

    if resultado.score_confianza is not None:
        resultado.clasificacion.score_confianza_clasificacion = resultado.score_confianza

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
    try:
        ruta_objeto = storage.guardar_json(
            documento_id=documento.documento_id,
            contenido=_contenido_oci(respuesta),
            estado=estado,
        )
        status_backup = "exito"
    except Exception as exc:
        logger.warning("No se pudo guardar '%s' en almacenamiento (%s).", documento.documento_id, exc)
        status_backup = "fallido"

    if backup_recibido == "fallido":
        status_backup = "fallido"

    respuesta.almacenamiento_oci = AlmacenamientoOCI(
        bucket=storage.get_active_bucket(),
        ruta_objeto=ruta_objeto,
        status_backup=status_backup,
    )

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
    Combina los documentos de Cloudflare R2 y OCI (sin duplicados), sin importar STORAGE_PROVIDER.
    """
    storage = _obtener_storage_service()
    docs: list[TriageResponse] = []
    try:
        documentos = storage.listar_documentos_triage_con_bucket(estado=estado)
        for ruta, data, bucket in documentos:
            try:
                doc = TriageResponse.model_validate(data)
                doc.almacenamiento_oci = AlmacenamientoOCI(
                    bucket=bucket,
                    ruta_objeto=ruta,
                    status_backup="exito",
                )
                docs.append(doc)
            except Exception as exc:
                logger.warning("Error al validar schema de '%s' desde almacenamiento: %s", ruta, exc)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("No se pudo sincronizar el historial desde el almacenamiento (%s).", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al consultar el historial en almacenamiento (OCI/R2): {exc}",
        ) from exc

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

    storage = _obtener_storage_service()
    try:
        contenido = _contenido_oci(doc, revision or RevisionHumanaRequest())
        if aprobado:
            ruta_objeto = storage.mover_a_validados(documento_id, contenido)
        else:
            ruta_objeto = storage.guardar_json(
                documento_id=documento_id,
                contenido=contenido,
                estado=EstadoDocumento.AUDITORIA_HUMANA,
            )
        status_backup = "exito"
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Fallo al resolver '%s' en almacenamiento (%s).", documento_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo actualizar el documento en almacenamiento (OCI/R2): {exc}",
        ) from exc

    doc.almacenamiento_oci = AlmacenamientoOCI(
        bucket=storage.get_active_bucket(),
        ruta_objeto=ruta_objeto,
        status_backup=status_backup,
    )
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