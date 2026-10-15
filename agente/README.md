# MediFlow/MediHelper → Agente (LangGraph)

Base del grafo de decisión del agente de triaje clínico.

Estado actual: **grafo con filtro de confianza, prioridad y enrutamiento implementados**.

```text
clasificación -> extracción -> score_confianza
  score < 0.75 -> revisión humana -> FIN
  score >= 0.75 -> prioridad -> enrutamiento final -> FIN
```

Clasificación y extracción están implementadas con respuesta estructurada y fallback JSON validado por Pydantic. La extracción informa datos ausentes y un score determinístico de completitud. El nodo de confianza lo utiliza para el filtro; las reglas de prioridad y el enrutamiento están implementados. Persisten interpretaciones pendientes de confirmación con Datos.

## Idioma

El código usa nombres de variables en **inglés**, por convención común de programación.

Esto es solo interno: el **contrato de salida** hacia el resto del sistema sigue en **español**, según lo definido en `schemas.py`.

## Estructura

* `state.py` - estado compartido entre los nodos del grafo.
* `nodes.py` - implementación de los nodos de clasificación, extracción y score de confianza.
* `graph.py` - arma y compila el grafo de LangGraph.
* `llm_provider.py` - selector de proveedor LLM según `LLM_ENV` (`dev` = Groq/Cohere, `prod` = Gemini).
* `prompts.py` - prompts utilizados por los nodos.
* `schemas.py` - modelos Pydantic y enums que definen el contrato de datos.
* `main.py` - ejemplo de cómo invocar el grafo con un documento de prueba.

## Estado de los nodos

| Nodo                          | Estado       | Responsable |
| ----------------------------- | ------------ | ----------- |
| Clasificación                 | Implementado | Jairo       |
| Extracción                    | Implementado | Seylin      |
| Score de confianza / urgencia | Implementado | Natalia     |

### Clasificación

`classification_node` utiliza una estrategia de dos capas:

1. **Structured output nativo** mediante `llm.with_structured_output(Clasificacion)`.
2. **Fallback manual** mediante `invoke()`, parseo de JSON y validación explícita con Pydantic.

Si ambas estrategias fallan, el nodo **no genera una clasificación por defecto**. En su lugar, lanza un error explícito para evitar que el flujo continúe con datos potencialmente falsos.

Las excepciones del proveedor todavía se propagan: el corte de revisión humana actual cubre score bajo, no fallos de clasificación o extracción.

El prompt de clasificación obtiene los valores permitidos directamente de los enums definidos en `schemas.py`, evitando duplicar manualmente las categorías y niveles de prioridad.

## Proveedores LLM

El proveedor se selecciona mediante la variable de entorno `LLM_ENV`:

* `dev` → Groq o Cohere, seleccionado mediante `LLM_DEV_PROVIDER`.
* `prod` → Gemini.

Los modelos pueden configurarse mediante variables de entorno:

```env
LLM_ENV=dev

LLM_DEV_PROVIDER=groq
GROQ_API_KEY=...
GROQ_MODEL=...

# Alternativamente:
LLM_DEV_PROVIDER=cohere
COHERE_API_KEY=...
COHERE_MODEL=...

# Para producción:
GEMINI_API_KEY=...
GEMINI_MODEL=...
```

Los valores por defecto de los modelos están definidos en `llm_provider.py` como fallback.

## Cómo levantar el proyecto

```bash
pip install -r requirements.txt
cp .env.example .env
# Completar .env con las API keys correspondientes
python main.py
```

**Nota:** las ejecuciones reales requieren un proveedor LLM configurado y consumen llamadas.
