"""
services/oci_storage.py — Integración con OCI Object Storage (Always Free).

Requiere el SDK oficial: `pip install oci`
Credenciales administradas 100% mediante variables de entorno (.env):
    - OCI_USER
    - OCI_FINGERPRINT
    - OCI_TENANCY
    - OCI_KEY_FILE (o OCI_KEY_CONTENT)
    - OCI_BUCKET
    - OCI_NAMESPACE
    - OCI_REGION

Organiza los objetos en 4 "carpetas" (prefijos) dentro del bucket:
    /recibidos/        -> El documento tal como llegó, sin procesar.
    /procesados/       -> El documento ya clasificado y extraído (JSON TriageResponse).
    /auditoria_humana/ -> Casos pendientes de revisión por score bajo / prioridad crítica.
    /validados/        -> Casos aprobados/auditados por un humano.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import oci

from app.config import get_settings
from app.schemas import EstadoDocumento

settings = get_settings()


class CarpetaOCI(str, Enum):
    RECIBIDOS = "recibidos"
    PROCESADOS = "procesados"
    AUDITORIA_HUMANA = "auditoria_humana"
    VALIDADOS = "validados"


_ESTADO_A_CARPETA = {
    EstadoDocumento.RECIBIDO: CarpetaOCI.RECIBIDOS,
    EstadoDocumento.PROCESADO: CarpetaOCI.PROCESADOS,
    EstadoDocumento.AUDITORIA_HUMANA: CarpetaOCI.AUDITORIA_HUMANA,
    EstadoDocumento.VALIDADO: CarpetaOCI.VALIDADOS,
}


class OCIStorageService:
    def __init__(
        self,
        bucket: str | None = None,
        namespace: str | None = None,
    ) -> None:
        if not (settings.OCI_USER and settings.OCI_TENANCY and settings.OCI_FINGERPRINT):
            raise ValueError(
                "Credenciales de OCI incompletas en .env. "
                "Asegúrate de definir OCI_USER, OCI_TENANCY, OCI_FINGERPRINT y OCI_KEY_FILE en tu .env"
            )

        config_dict: dict[str, Any] = {
            "user": settings.OCI_USER,
            "fingerprint": settings.OCI_FINGERPRINT,
            "tenancy": settings.OCI_TENANCY,
            "region": settings.OCI_REGION or "sa-santiago-1",
        }

        if settings.OCI_KEY_CONTENT:
            config_dict["key_content"] = settings.OCI_KEY_CONTENT
        elif settings.OCI_KEY_FILE:
            config_dict["key_file"] = os.path.expanduser(settings.OCI_KEY_FILE)
        else:
            raise ValueError("Debes especificar OCI_KEY_FILE o OCI_KEY_CONTENT en tu archivo .env")

        oci.config.validate_config(config_dict)
        self.config = config_dict
        self.client = oci.object_storage.ObjectStorageClient(self.config)

        self.namespace = (
            namespace
            or settings.OCI_NAMESPACE
            or self.client.get_namespace().data
        )
        self.bucket = bucket or settings.OCI_BUCKET

    def guardar_json(
        self,
        documento_id: str,
        contenido: dict[str, Any],
        estado: EstadoDocumento,
        subcarpeta: str | None = None,
    ) -> str:
        """
        Sube `contenido` como JSON al bucket, bajo la carpeta correspondiente
        al estado del documento. Devuelve la ruta_objeto para registrarla en
        AlmacenamientoOCI.

        Ej. de ruta resultante: procesados/urgentes/DOC-CLIN-2026-8942.json
        """
        carpeta = _ESTADO_A_CARPETA[estado].value
        partes = [carpeta]
        if subcarpeta:
            partes.append(subcarpeta)
        ruta_objeto = "/".join(partes) + f"/{documento_id}.json"

        self.client.put_object(
            namespace_name=self.namespace,
            bucket_name=self.bucket,
            object_name=ruta_objeto,
            put_object_body=json.dumps(contenido, ensure_ascii=False, indent=2).encode("utf-8"),
            content_type="application/json",
        )
        return ruta_objeto

    def guardar_documento_recibido(self, documento_id: str, texto_original: str) -> str:
        """Guarda el documento crudo apenas entra al pipeline, antes de procesarlo."""
        ruta_objeto = f"{CarpetaOCI.RECIBIDOS.value}/{documento_id}.json"
        cuerpo = {
            "documento_id": documento_id,
            "texto_original": texto_original,
            "recibido_en": datetime.now(timezone.utc).isoformat(),
        }
        self.client.put_object(
            namespace_name=self.namespace,
            bucket_name=self.bucket,
            object_name=ruta_objeto,
            put_object_body=json.dumps(cuerpo, ensure_ascii=False, indent=2).encode("utf-8"),
            content_type="application/json",
        )
        return ruta_objeto

    def subir_archivo(
        self,
        ruta_objeto: str,
        contenido_bytes: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Sube contenido binario o de texto genérico a la ruta especificada dentro del bucket."""
        self.client.put_object(
            namespace_name=self.namespace,
            bucket_name=self.bucket,
            object_name=ruta_objeto,
            put_object_body=contenido_bytes,
            content_type=content_type,
        )
        return ruta_objeto

    def descargar_objeto(self, ruta_objeto: str) -> bytes:
        """Descarga el contenido en bytes de un objeto almacenado en OCI."""
        response = self.client.get_object(
            namespace_name=self.namespace,
            bucket_name=self.bucket,
            object_name=ruta_objeto,
        )
        return response.data.content

    def descargar_json(self, ruta_objeto: str) -> dict[str, Any]:
        """Descarga y deserializa un archivo JSON almacenado en OCI."""
        data_bytes = self.descargar_objeto(ruta_objeto)
        return json.loads(data_bytes.decode("utf-8"))

    def listar_objetos(self, prefijo: str | None = None) -> list[str]:
        """Lista los nombres de los objetos dentro del bucket, filtrando opcionalmente por prefijo."""
        kwargs: dict[str, Any] = {
            "namespace_name": self.namespace,
            "bucket_name": self.bucket,
        }
        if prefijo:
            kwargs["prefix"] = prefijo
        response = self.client.list_objects(**kwargs)
        return [obj.name for obj in response.data.objects]

    def eliminar_objeto(self, ruta_objeto: str) -> None:
        """Elimina un objeto del bucket."""
        self.client.delete_object(
            namespace_name=self.namespace,
            bucket_name=self.bucket,
            object_name=ruta_objeto,
        )


_service: OCIStorageService | None = None


def get_oci_service() -> OCIStorageService:
    """Singleton simple para reusar el cliente OCI entre requests."""
    global _service
    if _service is None:
        _service = OCIStorageService()
    return _service
