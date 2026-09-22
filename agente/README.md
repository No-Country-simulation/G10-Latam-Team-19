# MediFlow/MediHelper → Agente (LangGraph)

Base del grafo de decisión del agente de triaje. Estado actual: **flujo lineal**, sin ramas condicionales todavía.

```text
clasificación -> extracción -> score_confianza -> FIN
```

## Idioma

El código usa nombres de variables en **inglés**, por convención común de programación.

Esto es solo interno, el **contrato de salida** hacia el resto del sistema sigue en **español**,
por como fue definido en `schemas.py`.

## Estructura

- `state.py` - estado compartido entre nodos del grafo.
- `nodes.py` - los 3 nodos del grafo. Cada uno tiene un `TODO` con el
  responsable asignado (ver Reunión 3).
- `graph.py` - arma y compila el grafo de LangGraph.
- `llm_provider.py` - selector de proveedor LLM según `LLM_ENV`
  (`dev` = Cohere/Groq, `prod` = Gemini).
- `main.py` - ejemplo de cómo invocar el grafo con un documento de prueba.

## Responsables

| Nodo | Responsable |
| --- | --- |
| Clasificación | Jairo |
| Extracción | Seylin |
| Score de confianza / urgencia | Natalia |

## Cómo levantar el proyecto

```bash
pip install -r requirements.txt
cp .env.example .env
# Completar .env con las API keys correspondientes
python main.py
```

**Nota:** Por ahora `main.py` va a fallar con `NotImplementedError` en los nodos.

Es esperado, cada responsable completa su nodo en `nodes.py` implementando la llamada real al LLM.

## Próxima iteración esperada (no implementado aún)

Agregar las ramas condicionales (estándar / urgencia / ambigüedad → revisión humana) una vez que:

1. Los 3 nodos funcionen de forma aislada con los prompts reales.

2. El equipo de Datos entregue los umbrales y reglas de decisión.
