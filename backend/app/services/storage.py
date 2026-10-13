"""
services/storage.py — Servicio de Almacenamiento Resiliente y Conmutable por Entorno.

Permite seleccionar el servicio de almacenamiento mediante la variable de entorno `STORAGE_PROVIDER`:
    - STORAGE_PROVIDER=r2  -> Cloudflare R2 (S3-compatible, rápido y activo).
    - STORAGE_PROVIDER=oci -> Oracle Cloud Infrastructure (Always Free, para la demo).

Ambos servicios implementan el mismo contrato y las 4 carpetas:
    /recibidos/
    /procesados/
    /auditoria_humana/
    /validados/
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.config import get_settings
from app.schemas import EstadoDocumento
from app.services.oci_storage import OCIStorageService, get_oci_service
from app.services.r2_storage import R2StorageService, get_r2_service

logger = logging.getLogger("mediflow.storage")


class StorageProvider:
    """
    Gestiona el almacenamiento de objetos delegando en el proveedor elegido
    en la variable de entorno STORAGE_PROVIDER ('r2' o 'oci').
    Si el proveedor seleccionado falla, conmuta automáticamente al alternativo.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def _proveedor_preferido(self) -> str:
        return (self.settings.STORAGE_PROVIDER or "r2").lower()

    def _obtener_oci(self) -> OCIStorageService | None:
        try:
            return get_oci_service()
        except Exception as exc:
            logger.debug("OCI no disponible: %s", exc)
            return None

    def _obtener_r2(self) -> R2StorageService | None:
        try:
            return get_r2_service()
        except Exception as exc:
            logger.warning("Cloudflare R2 no disponible: %s", exc)
            return None

    def _obtener_primario_y_secundario(self) -> list[tuple[str, Callable[[], Any]]]:
        preferido = self._proveedor_preferido()
        if preferido == "oci":
            return [("OCI", self._obtener_oci), ("Cloudflare R2", self._obtener_r2)]
        return [("Cloudflare R2", self._obtener_r2), ("OCI", self._obtener_oci)]

    def get_active_bucket(self) -> str:
        """Devuelve el nombre del bucket activo según el proveedor configurado."""
        preferido = self._proveedor_preferido()
        if preferido == "oci":
            oci = self._obtener_oci()
            if oci:
                return oci.bucket
            return self.settings.OCI_BUCKET or "mediflow-documentos-clinicos"
        r2 = self._obtener_r2()
        if r2:
            return r2.bucket
        return self.settings.R2_BUCKET_NAME or "mediflow-documentos-clinicos"

    def guardar_documento_recibido(self, documento_id: str, texto_original: str) -> str:
        """Guarda el documento crudo en el proveedor activo (o fallback si falla)."""
        intentos = self._obtener_primario_y_secundario()
        ultimo_error: Exception | None = None

        for nombre, getter in intentos:
            servicio = getter()
            if servicio is not None:
                try:
                    ruta = servicio.guardar_documento_recibido(documento_id, texto_original)
                    logger.info("Documento crudo '%s' guardado en %s.", documento_id, nombre)
                    return ruta
                except Exception as exc:
                    logger.warning("Fallo al guardar crudo '%s' en %s (%s). Probando alternativo...", documento_id, nombre, exc)
                    ultimo_error = exc

        raise RuntimeError(f"No se pudo guardar el documento crudo en ningún almacenamiento: {ultimo_error}")

    def guardar_json(
        self,
        documento_id: str,
        contenido: dict[str, Any],
        estado: EstadoDocumento,
        subcarpeta: str | None = None,
    ) -> str:
        """Guarda el resultado procesado en el proveedor activo (o fallback si falla)."""
        intentos = self._obtener_primario_y_secundario()
        ultimo_error: Exception | None = None

        for nombre, getter in intentos:
            servicio = getter()
            if servicio is not None:
                try:
                    ruta = servicio.guardar_json(documento_id, contenido, estado, subcarpeta)
                    logger.info("JSON '%s' guardado en %s (%s).", documento_id, nombre, ruta)
                    return ruta
                except Exception as exc:
                    logger.warning("Fallo al guardar JSON '%s' en %s (%s). Probando alternativo...", documento_id, nombre, exc)
                    ultimo_error = exc

        raise RuntimeError(f"No se pudo guardar el JSON en ningún almacenamiento: {ultimo_error}")

    def buscar_documento_triage(self, documento_id: str) -> tuple[str, dict[str, Any]] | None:
        """Busca el documento en el proveedor activo, y si no está, busca en el secundario."""
        intentos = self._obtener_primario_y_secundario()
        for nombre, getter in intentos:
            servicio = getter()
            if servicio is not None:
                try:
                    encontrado = servicio.buscar_documento_triage(documento_id)
                    if encontrado is not None:
                        return encontrado
                except Exception as exc:
                    logger.debug("Búsqueda en %s falló para '%s': %s", nombre, documento_id, exc)

        return None

    def mover_a_validados(self, documento_id: str, contenido: dict[str, Any]) -> str:
        """Mueve el documento a /validados/ en el proveedor activo (o fallback si falla)."""
        intentos = self._obtener_primario_y_secundario()
        ultimo_error: Exception | None = None

        for nombre, getter in intentos:
            servicio = getter()
            if servicio is not None:
                try:
                    ruta = servicio.mover_a_validados(documento_id, contenido)
                    logger.info("Documento '%s' movido a validados en %s.", documento_id, nombre)
                    return ruta
                except Exception as exc:
                    logger.warning("Fallo al mover a validados '%s' en %s (%s). Probando alternativo...", documento_id, nombre, exc)
                    ultimo_error = exc

        raise RuntimeError(f"No se pudo mover a validados en ningún almacenamiento: {ultimo_error}")

    def listar_documentos_triage(
        self, estado: EstadoDocumento | str | None = None
    ) -> list[tuple[str, dict[str, Any]]]:
        """Lista documentos de triaje desde el proveedor activo (o fallback si falla)."""
        intentos = self._obtener_primario_y_secundario()
        for nombre, getter in intentos:
            servicio = getter()
            if servicio is not None:
                try:
                    docs = servicio.listar_documentos_triage(estado=estado)
                    if docs:
                        return docs
                except Exception as exc:
                    logger.warning("Fallo al listar documentos desde %s (%s). Probando alternativo...", nombre, exc)

        # Si el primario devolvió lista vacía sin error, intentar también secundario por si hay docs guardados allí
        for nombre, getter in intentos:
            servicio = getter()
            if servicio is not None:
                try:
                    return servicio.listar_documentos_triage(estado=estado)
                except Exception:
                    pass

        return []


_storage_provider: StorageProvider | None = None


def get_storage_service() -> StorageProvider:
    global _storage_provider
    if _storage_provider is None:
        _storage_provider = StorageProvider()
    return _storage_provider
