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
            from langchain_groq import ChatGroq

            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("Falta GROQ_API_KEY en el .env")

            return ChatGroq(
                model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
                api_key=api_key,
                temperature=0,
            )

        elif provider == "cohere":
            from langchain_cohere import ChatCohere

            api_key = os.getenv("COHERE_API_KEY")
            if not api_key:
                raise ValueError("Falta COHERE_API_KEY en el .env")

            return ChatCohere(
                model=os.getenv("COHERE_MODEL", "command-a-plus-05-2026"),
                cohere_api_key=api_key,
                temperature=0,
            )

        else:
            raise ValueError(f"LLM_DEV_PROVIDER desconocido: {provider}")

    elif environ == "prod":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Falta GEMINI_API_KEY en el .env")

        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            api_key=api_key,
            temperature=0,
        )
        
    else:
        raise ValueError(f"LLM_ENV desconocido: {environ} (usar 'dev' o 'prod')")
