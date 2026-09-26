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

    # --- LLM (dev: Cohere/Groq, prod: Gemini — según Reunión 1 y 2) ---
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq" if ENV == "development" else "gemini")
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    COHERE_API_KEY: str | None = os.getenv("COHERE_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

    # --- OCI Object Storage (Always Free) ---
    OCI_NAMESPACE: str | None = os.getenv("OCI_NAMESPACE")
    OCI_BUCKET: str = os.getenv("OCI_BUCKET", "mediflow-documentos-clinicos")
    OCI_REGION: str = os.getenv("OCI_REGION", "sa-santiago-1")
    OCI_USER: str | None = os.getenv("OCI_USER")
    OCI_FINGERPRINT: str | None = os.getenv("OCI_FINGERPRINT")
    OCI_TENANCY: str | None = os.getenv("OCI_TENANCY")
    OCI_KEY_FILE: str | None = os.getenv("OCI_KEY_FILE")
    OCI_KEY_CONTENT: str | None = os.getenv("OCI_KEY_CONTENT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
