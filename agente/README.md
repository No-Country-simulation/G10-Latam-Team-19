# MediFlow/MediHelper → Agente (LangGraph)

Base del grafo de decisión del agente de triaje clínico.

Estado actual: **flujo lineal**, sin ramas condicionales todavía.

```text
clasificación -> extracción -> score_confianza -> FIN
```

Clasificación y extracción están implementadas con respuesta estructurada y fallback JSON validado por Pydantic. La extracción informa datos ausentes y un score provisional de completitud. El nodo de confianza final, la revisión humana y el enrutamiento siguen pendientes de sus responsables y de la matriz del equipo de Datos.

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

**Nota:** `main.py` todavía no puede completar el flujo entero porque `confidence_node` conserva su `NotImplementedError` original. La extracción puede probarse de forma aislada; las llamadas reales requieren un proveedor LLM configurado.

## Próxima iteración esperada

Agregar las ramas condicionales para los distintos destinos del flujo, incluyendo los casos que requieran **revisión humana**, una vez definidos:

1. Los prompts y validaciones definitivos de los tres nodos.
2. Los umbrales de confianza.
3. Las reglas de prioridad y urgencia.
4. El mapeo entre clasificación, score y destino.
5. Las condiciones que obligan a derivar un documento a revisión humana.


## Regla de confianza por datos faltantes

Regla de Michelle: datos relevantes ausentes reducen la confianza. Los pesos
provisionales están centralizados en `confidence.py`; requieren calibración del
equipo de Datos y no representan probabilidades de exactitud clínica.

| Campo ausente | Descuento | Cuándo aplica |
| --- | --- | --- |
| `paciente.nombre` (nombre_paciente) | 0.15 | Siempre |
| `paciente.edad` | 0.10 | Siempre |
| `medico_solicitante.nombre` | 0.10 | Siempre |
| `diagnostico_principal` | 0.20 | Siempre |
| `estudio_realizado` | 0.10 | Informe de estudio o laboratorio |
| `medicamentos` | 0.10 | Receta médica |
| `dosis` | 0.05 | Receta médica o medicamentos presentes |

`penalización = suma de los pesos de campos relevantes ausentes`.
La extracción devuelve `extraction_confidence_score = max(0, 1 - penalización)`.
Se limita a [0, 1] y se redondea a seis decimales. Se recalcula desde 1 para
no acumular descuentos al repetir la extracción. Este valor describe únicamente
la completitud de la extracción: no combina el score de clasificación ni
establece `final_confidence_score` o `requires_human_review`. Esa integración
queda pendiente del trabajo de los responsables del nodo de confianza y Datos.

El esquema `DatosExtraidos` no cambia. La confianza se publica en el estado del
grafo; no se añade un score solicitado al LLM al contrato de extracción. La
matrícula y el CIE-10 no penalizan. Sin clasificación, la extracción aplica los
campos comunes y dosis si hay medicamentos. Los campos opcionales no se vuelven obligatorios.

Se consideran ausentes `None`, texto vacío, marcadores normalizados definidos
en `MISSING_TEXT_VALUES` (incluido `Desconocido`) y listas sin valores útiles.
La edad cero sí cuenta como presente. `missing_critical_fields` registra nombre
y edad; `missing_relevant_fields` explica todos los descuentos aplicables.
La política verifica presencia, no exactitud clínica ni correspondencia entre
cada medicamento y su dosis.

Con los demás datos relevantes completos:

| Caso | Score provisional de extracción |
| --- | --- |
| Datos completos | 1.00 |
| Sin nombre | 0.85 |
| Sin edad | 0.90 |
| Sin ambos | 0.75 |

Pruebas locales sin credenciales ni llamadas al proveedor, desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s agente -p test_extraction_local.py -v
.\.venv\Scripts\python.exe -m unittest discover -s agente -p test_confidence.py -v
```

Incluyen ambas rutas de extracción, campos opcionales, edad cero, reintentos
y extracción sin clasificación previa. No se prueba la ejecución completa del
grafo porque el nodo de confianza final sigue pendiente.
