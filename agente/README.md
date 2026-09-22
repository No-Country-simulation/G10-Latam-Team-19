# MediFlow/MediHelper → Agente (LangGraph)

Base del grafo de decisión del agente de triaje clínico.

Estado actual: **flujo lineal**, sin ramas condicionales todavía.

```text
clasificación -> extracción -> score_confianza -> FIN
```

Actualmente, el nodo de **clasificación está implementado y testeado de forma aislada**. Los nodos de extracción y score de confianza continúan como placeholders.

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
| Extracción                    | Pendiente    | Seylin      |
| Score de confianza / urgencia | Pendiente    | Natalia     |

### Clasificación

`classification_node` utiliza una estrategia de dos capas:

1. **Structured output nativo** mediante `llm.with_structured_output(Clasificacion)`.
2. **Fallback manual** mediante `invoke()`, parseo de JSON y validación explícita con Pydantic.

Si ambas estrategias fallan, el nodo **no genera una clasificación por defecto**. En su lugar, lanza un error explícito para evitar que el flujo continúe con datos potencialmente falsos.

La derivación efectiva de estos casos a revisión humana se implementará junto con las ramas condicionales del grafo.

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

**Nota:** `main.py` todavía no puede completar el flujo entero porque `extraction_node` y `confidence_node` levantan `NotImplementedError` a propósito.

## Próxima iteración esperada

Agregar las ramas condicionales para los distintos destinos del flujo, incluyendo los casos que requieran **revisión humana**, una vez definidos:

1. Los prompts y validaciones definitivos de los tres nodos.
2. Los umbrales de confianza.
3. Las reglas de prioridad y urgencia.
4. El mapeo entre clasificación, score y destino.
5. Las condiciones que obligan a derivar un documento a revisión humana.
