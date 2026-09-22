#
# LLM_ENV=dev   -> Cohere o Groq (para prototipar)
# LLM_ENV=prod  -> Gemini (el elegido para producción)
#

import os

def get_llm():
    """
    Devuelve un cliente LLM listo para usar (interfaz de langchain),
    según la variable de entorno LLM_ENV.

    TODO (equipo Agente): completar cada rama con el modelo real y su configuración
                          (temperatura, max_tokens, etc.) una vez tengamos las API keys
                          Por ahora son placeholders.
    """
    environ = os.getenv("LLM_ENV", "dev").lower()

    if environ == "dev":
        provider = os.getenv("LLM_DEV_PROVIDER", "groq").lower()

        if provider == "groq":
            raise NotImplementedError(
                "TODO: instalar langchain-groq e implementar el cliente de Groq."
            )
        elif provider == "cohere":
            raise NotImplementedError(
                "TODO: instalar langchain-cohere e implementar el cliente de Cohere."
            )
        else:
            raise ValueError(f"LLM_DEV_PROVIDER desconocido: {provider}")

    elif environ == "prod":
        raise NotImplementedError(
            "TODO: instalar langchain-google-genai e implementar el cliente de Gemini."
        )
    else:
        raise ValueError(f"LLM_ENV desconocido: {environ} (usar 'dev' o 'prod')")
