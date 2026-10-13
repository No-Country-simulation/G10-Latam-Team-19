"""
services/r2_storage.py — Integración con Cloudflare R2 (S3-compatible Object Storage).

Utiliza `boto3` para interactuar con Cloudflare R2.
Credenciales administradas mediante variables de entorno (.env):
    - R2_BUCKET_NAME
    - R2_ACCESS_KEY_ID
    - R2_SECRET_ACCESS_KEY
    - R2_ENDPOINT_URL
    - R2_REGION_NAME (default: "auto")
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings
from app.schemas import EstadoDocumento
from app.services.oci_storage import CarpetaOCI, _ESTADO_A_CARPETA

logger = logging.getLogger("mediflow.r2")
settings = get_settings()


class R2StorageService:
    def __init__(self) -> None:
        if not (settings.R2_ENDPOINT_URL and settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY):
            raise ValueError(
                "Credenciales de Cloudflare R2 incompletas en .env. "
                "Asegúrate de definir R2_ENDPOINT_URL, R2_ACCESS_KEY_ID y R2_SECRET_ACCESS_KEY."
            )

        self.bucket = settings.R2_BUCKET_NAME or "mediflow-documentos-clinicos"
        self.client = boto3.client(
            service_name="s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name=settings.R2_REGION_NAME or "auto",
        )

    def guardar_json(
        self,
        documento_id: str,
        contenido: dict[str, Any],
        estado: EstadoDocumento,
        subcarpeta: str | None = None,
    ) -> str:
        """Sube contenido JSON a R2 bajo la carpeta correspondiente al estado."""
        carpeta = _ESTADO_A_CARPETA[estado].value
        partes = [carpeta]
        if subcarpeta:
            partes.append(subcarpeta)
        ruta_objeto = "/".join(partes) + f"/{documento_id}.json"

        body_bytes = json.dumps(contenido, ensure_ascii=False, indent=2).encode("utf-8")
        self.client.put_object(
            Bucket=self.bucket,
            Key=ruta_objeto,
            Body=body_bytes,
            ContentType="application/json",
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
        body_bytes = json.dumps(cuerpo, ensure_ascii=False, indent=2).encode("utf-8")
        self.client.put_object(
            Bucket=self.bucket,
            Key=ruta_objeto,
            Body=body_bytes,
            ContentType="application/json",
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
            Bucket=self.bucket,
            Key=ruta_objeto,
            Body=contenido_bytes,
            ContentType=content_type,
        )
        return ruta_objeto

    def descargar_objeto(self, ruta_objeto: str) -> bytes:
        """Descarga el contenido en bytes de un objeto almacenado en R2."""
        response = self.client.get_object(Bucket=self.bucket, Key=ruta_objeto)
        return response["Body"].read()

    def descargar_json(self, ruta_objeto: str) -> dict[str, Any]:
        """Descarga y deserializa un archivo JSON almacenado en R2."""
        data_bytes = self.descargar_objeto(ruta_objeto)
        return json.loads(data_bytes.decode("utf-8"))

    def listar_objetos(self, prefijo: str | None = None) -> list[str]:
        """Lista las claves de los objetos dentro del bucket, filtrando opcionalmente por prefijo."""
        kwargs: dict[str, Any] = {"Bucket": self.bucket}
        if prefijo:
            kwargs["Prefix"] = prefijo

        response = self.client.list_objects_v2(**kwargs)
        contents = response.get("Contents", [])
        # Ignorar las entradas de "carpeta" vacías (claves que terminan en '/' y tamaño 0)
        return [obj["Key"] for obj in contents if not obj["Key"].endswith("/")]

    def eliminar_objeto(self, ruta_objeto: str) -> None:
        """Elimina un objeto del bucket."""
        self.client.delete_object(Bucket=self.bucket, Key=ruta_objeto)

    def buscar_documento_triage(self, documento_id: str) -> tuple[str, dict[str, Any]] | None:
        """
        Busca un documento de triaje en R2 en orden de prioridad:
        1. /validados/
        2. /procesados/
        3. /auditoria_humana/
        Devuelve (ruta_objeto, dict_contenido) o None si no existe.
        """
        rutas_candidatas = [
            f"{CarpetaOCI.VALIDADOS.value}/{documento_id}.json",
            f"{CarpetaOCI.PROCESADOS.value}/{documento_id}.json",
            f"{CarpetaOCI.AUDITORIA_HUMANA.value}/{documento_id}.json",
        ]
        for ruta in rutas_candidatas:
            try:
                data = self.descargar_json(ruta)
                return ruta, data
            except Exception:
                continue

        # Si no se encontró por ruta directa, intentar listar si estaba en subcarpeta
        try:
            objetos = self.listar_objetos()
            for obj in objetos:
                if obj.endswith(f"/{documento_id}.json") and not obj.startswith(f"{CarpetaOCI.RECIBIDOS.value}/"):
                    data = self.descargar_json(obj)
                    return obj, data
        except Exception:
            pass

        return None

    def mover_a_validados(self, documento_id: str, contenido: dict[str, Any]) -> str:
        """Guarda en /validados/ y elimina de /auditoria_humana/."""
        ruta_validado = self.guardar_json(
            documento_id=documento_id,
            contenido=contenido,
            estado=EstadoDocumento.VALIDADO,
        )
        try:
            self.eliminar_objeto(f"{CarpetaOCI.AUDITORIA_HUMANA.value}/{documento_id}.json")
        except Exception:
            pass
        return ruta_validado

    def listar_documentos_triage(
        self, estado: EstadoDocumento | str | None = None
    ) -> list[tuple[str, dict[str, Any]]]:
        """Lista y descarga los documentos de triaje procesados desde R2."""
        if isinstance(estado, str):
            try:
                estado = EstadoDocumento(estado)
            except ValueError:
                estado = None

        carpetas = (
            [_ESTADO_A_CARPETA[estado].value]
            if estado is not None and estado in _ESTADO_A_CARPETA
            else [
                CarpetaOCI.PROCESADOS.value,
                CarpetaOCI.AUDITORIA_HUMANA.value,
                CarpetaOCI.VALIDADOS.value,
            ]
        )

        resultados: list[tuple[str, dict[str, Any]]] = []
        for carpeta in carpetas:
            try:
                objetos = self.listar_objetos(prefijo=f"{carpeta}/")
            except Exception as exc:
                logger.warning("No se pudieron listar objetos bajo '%s/' en R2: %s", carpeta, exc)
                continue

            for obj in objetos:
                if not obj.endswith(".json"):
                    continue
                try:
                    data = self.descargar_json(obj)
                    resultados.append((obj, data))
                except Exception as exc:
                    logger.warning("No se pudo descargar documento '%s' desde R2: %s", obj, exc)

        return resultados


_r2_service: R2StorageService | None = None


def get_r2_service() -> R2StorageService:
    global _r2_service
    if _r2_service is None:
        _r2_service = R2StorageService()
    return _r2_service
