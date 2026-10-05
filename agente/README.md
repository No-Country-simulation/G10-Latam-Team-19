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

Pesos de `Proyecto alura_Data_UmbralScoreyReglas.pdf`, páginas 10-11.
El score de extracción mide completitud, no exactitud clínica. Se calcula desde
1 en cada ejecución, resta las categorías ausentes una sola vez, se limita a
[0, 1] y se redondea a seis decimales.

| Categoría | Descuento | Aplicación actual |
| --- | --- | --- |
| Edad numérica | 0.15 | Siempre, conservando la regla acordada; cero es válido |
| Diagnóstico o CIE-10 | 0.15 | Si faltan ambos |
| Medicamento o dosis | 0.30 | En receta, si falta cualquiera en alguna entrada |
| Frecuencia diaria | 0.05 | En receta, si falta en alguna entrada o no hay medicamentos |
| Signos vitales incompletos | 0.10 | Si existe el objeto y falta alguno de sus cinco campos |
| Sexo | 0.05 | Descuento base por ausencia; no se infiere dependencia clínica |
| Unidad de edad pediátrica | 0.30 | Peso registrado, aplicación pendiente de señal de pediatría |

Todas las categorías aplicadas aparecen en `missing_relevant_fields`; las etiquetas de
medicamentos/dosis y diagnóstico cambiaron para reflejar penalizaciones agrupadas.
No se penaliza médico ni estudio, porque no figuran en la tabla del PDF.
No se añade vía al schema. Las decisiones temporales y preguntas para Datos
están en [PESOS_PENDIENTES.md](PESOS_PENDIENTES.md).

La extracción conserva `extraction_confidence_score`; no modifica el score
LLM de clasificación ni implementa el filtro, la prioridad o el enrutamiento.
Los pesos están alineados al PDF, pero su aplicación clínica completa requiere
resolver los pendientes documentados.

Pruebas locales sin llamadas al proveedor, desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s agente -p 'test_*.py' -v
.\.venv\Scripts\python.exe -m compileall -q agente schemas.py
```
