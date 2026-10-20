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
from datetime import datetime, timezone
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
        """
        Busca el documento en TODOS los proveedores disponibles y devuelve la copia más
        reciente (por `timestamp`; ante empate, la del proveedor preferido).
        """
        mejor: tuple[str, dict[str, Any]] | None = None
        for nombre, getter in self._obtener_primario_y_secundario():
            servicio = getter()
            if servicio is None:
                continue
            try:
                encontrado = servicio.buscar_documento_triage(documento_id)
            except Exception as exc:
                logger.debug("Búsqueda en %s falló para '%s': %s", nombre, documento_id, exc)
                continue
            if encontrado is not None and (
                mejor is None or self._marca_tiempo(encontrado[1]) > self._marca_tiempo(mejor[1])
            ):
                mejor = encontrado
        return mejor

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

    @staticmethod
    def _marca_tiempo(data: dict[str, Any]) -> datetime:
        """Timestamp del documento como datetime aware (UTC); epoch si falta o es inválido."""
        minimo = datetime.min.replace(tzinfo=timezone.utc)
        crudo = data.get("timestamp")
        if not isinstance(crudo, str):
            return minimo
        try:
            valor = datetime.fromisoformat(crudo.replace("Z", "+00:00"))
        except ValueError:
            return minimo
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)

    def listar_documentos_triage_con_bucket(
        self, estado: EstadoDocumento | str | None = None
    ) -> list[tuple[str, dict[str, Any], str]]:
        """
        Lista documentos de triaje combinando TODOS los proveedores disponibles (R2 y OCI).

        - Un proveedor caído o sin credenciales se omite sin romper el listado.
        - Si un mismo `documento_id` existe en ambos (p. ej. quedó una copia vieja en
          /auditoria_humana/ en un proveedor y la validada en el otro), gana la copia con
          `timestamp` más reciente; ante empate, la del proveedor preferido.
        - Devuelve (ruta_objeto, contenido, bucket_de_origen) para que cada documento
          informe el bucket donde realmente está guardado.
        """
        por_id: dict[str, tuple[str, dict[str, Any], str]] = {}
        sin_id: list[tuple[str, dict[str, Any], str]] = []
        proveedores_ok = 0

        # Se recorre en orden de preferencia; solo reemplaza una copia si es estrictamente más nueva.
        for nombre, getter in self._obtener_primario_y_secundario():
            servicio = getter()
            if servicio is None:
                continue
            try:
                docs = servicio.listar_documentos_triage(estado=estado)
            except Exception as exc:
                logger.warning("Fallo al listar documentos desde %s (%s). Se omite.", nombre, exc)
                continue

            proveedores_ok += 1
            for ruta, data in docs:
                doc_id = data.get("documento_id")
                if not doc_id:
                    sin_id.append((ruta, data, servicio.bucket))
                    continue
                previo = por_id.get(doc_id)
                if previo is None or self._marca_tiempo(data) > self._marca_tiempo(previo[1]):
                    por_id[doc_id] = (ruta, data, servicio.bucket)

        if proveedores_ok == 0:
            raise RuntimeError("Ningún almacenamiento (R2/OCI) está disponible para listar documentos.")

        return [*por_id.values(), *sin_id]

    def listar_documentos_triage(
        self, estado: EstadoDocumento | str | None = None
    ) -> list[tuple[str, dict[str, Any]]]:
        """Versión compatible: (ruta_objeto, contenido) combinando R2 y OCI."""
        return [(ruta, data) for ruta, data, _ in self.listar_documentos_triage_con_bucket(estado=estado)]


_storage_provider: StorageProvider | None = None


def get_storage_service() -> StorageProvider:
    global _storage_provider
    if _storage_provider is None:
        _storage_provider = StorageProvider()
    return _storage_provider