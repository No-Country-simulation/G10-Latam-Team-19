"""
config.py — Configuración centralizada del Backend (FastAPI).

Todo lo que dependa del entorno (credenciales, endpoints, umbrales) vive
acá. Nunca hardcodear claves en el código: usar variables de entorno
(.env local, o config de OCI Compute / secrets en producción).
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- App ---
    APP_NAME: str = "MediFlow API"
    ENV: str = os.getenv("ENV", "development")  # development | production

    # --- Agente (grafo LangGraph) ---
    # Carpeta donde se alojan graph.py / nodes.py / schemas.py del agente. Si no se define,
    # se busca ../agente y ../agentes respecto a la raíz del backend.
    AGENTE_DIR: str | None = os.getenv("AGENTE_DIR")

    # --- Proveedor de Almacenamiento (r2 | oci) ---
    # Permite alternar entre Cloudflare R2 y OCI Object Storage desde .env sin tocar código.
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "r2").lower()

    # --- OCI Object Storage (Always Free) ---
    OCI_NAMESPACE: str | None = os.getenv("OCI_NAMESPACE")
    OCI_BUCKET: str = os.getenv("OCI_BUCKET", "mediflow-documentos-clinicos")
    OCI_REGION: str = os.getenv("OCI_REGION", "sa-santiago-1")
    OCI_USER: str | None = os.getenv("OCI_USER")
    OCI_FINGERPRINT: str | None = os.getenv("OCI_FINGERPRINT")
    OCI_TENANCY: str | None = os.getenv("OCI_TENANCY")
    OCI_KEY_FILE: str | None = os.getenv("OCI_KEY_FILE")
    OCI_KEY_CONTENT: str | None = os.getenv("OCI_KEY_CONTENT")

    # --- Cloudflare R2 (S3-compatible Object Storage) ---
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "mediflow-documentos-clinicos")
    R2_ACCESS_KEY_ID: str | None = os.getenv("R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY: str | None = os.getenv("R2_SECRET_ACCESS_KEY")
    R2_ENDPOINT_URL: str | None = os.getenv("R2_ENDPOINT_URL")
    R2_REGION_NAME: str = os.getenv("R2_REGION_NAME", "auto")


@lru_cache
def get_settings() -> Settings:
    return Settings()
