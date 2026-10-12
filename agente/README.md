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

## Pendientes de validación

- Evaluar el prompt con documentos ficticios y proveedor real; las pruebas locales simulan sus respuestas.
- Confirmar con Datos las interpretaciones de PESOS_PENDIENTES.md.
- Resolver los dos fallos esperados de prioridad (dolor severo y caso pediátrico) conforme a reglas acordadas.
- Implementar el manejo de errores del proveedor para revisión humana.
- Confirmar el objetivo semanal exacto antes de declarar su cumplimiento.

## Regla de confianza por datos faltantes

Pesos de `Proyecto alura_Data_UmbralScoreyReglas.pdf`, páginas 10-11.
El score de extracción mide completitud, no exactitud clínica. Se calcula desde
1 en cada ejecución, resta las categorías ausentes una sola vez, se limita a
[0, 1] y se redondea a seis decimales.

| Categoría | Descuento | Aplicación actual |
| --- | --- | --- |
| Edad numérica | 0.15 | Siempre, conservando la regla acordada; cero es válido |
| Diagnóstico o CIE-10 | 0.15 | Si faltan ambos |
| Medicamento, dosis o vía | 0.30 | En receta, si falta cualquiera en alguna entrada |
| Frecuencia diaria | 0.05 | En receta, si falta en alguna entrada o no hay medicamentos |
| Signos vitales incompletos | 0.10 | Si existe el objeto y falta alguno de sus cinco campos |
| Sexo | 0.05 | Descuento base por ausencia; no se infiere dependencia clínica |
| Unidad de edad pediátrica | 0.30 | Peso registrado, aplicación pendiente de señal de pediatría |

Todas las categorías aplicadas aparecen en `missing_relevant_fields`; las etiquetas de
medicamentos/dosis y diagnóstico cambiaron para reflejar penalizaciones agrupadas.
No se penaliza médico ni estudio, porque no figuran en la tabla del PDF.
La vía se extrae mediante ViaAdministracion y su ausencia activa el descuento agrupado de 0.30 en recetas, sin sumarlo por cada campo o fármaco. La etiqueta medicamentos_o_dosis se conserva por compatibilidad y ahora también incluye vía. Las decisiones temporales y preguntas para Datos
están en [PESOS_PENDIENTES.md](PESOS_PENDIENTES.md).

La extracción conserva `extraction_confidence_score`; no modifica el score
LLM de clasificación. El filtro utiliza ese score de extracción mediante final_confidence_score.
Los pesos están alineados al PDF, pero su aplicación clínica completa requiere
resolver los pendientes documentados.

Pruebas locales sin llamadas al proveedor, desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s agente -p 'test_*.py' -v
.\.venv\Scripts\python.exe -m compileall -q agente schemas.py
```

Las pruebas de test_graph_local.py recorren el grafo con proveedor simulado: corte por score bajo, límite 0.75, conservación de vía y auditoría por medicamento restringido.

Evaluación real de extracción: `python evaluate_extraction.py --output informe.json`.
Groq usa GROQ_MAX_TOKENS (800 por defecto), timeout de 30 segundos y sin reintentos automáticos.
El límite por minuto de la cuenta puede requerir espaciar las ejecuciones; un error 429 no mide precisión del prompt.

## Apoyo LLM del Nodo 2

priority_support.py evalúa únicamente diagnostico_principal y estudio_realizado.
Valida ApoyoPrioridad mediante respuesta estructurada; si falla, intenta JSON manual.
Si ambas rutas fallan, lanza RuntimeError sin inventar una prioridad. Si no existe
ninguno de los dos textos, omite la llamada y conserva la evaluación determinística.
La gravedad máxima entre reglas existentes y apoyo determina la prioridad; el destino
se calcula después, conservando medicamentos restringidos y el filtro de confianza.
El estado conserva nivel_prioridad_apoyo y justificacion_apoyo para inspección.

El apoyo no resuelve contradicciones entre el PDF y los casos esperados. Tampoco
puede rebajar un falso positivo de palabras clave determinísticas en diagnósticos negados.
Los errores del apoyo se propagan; su derivación automática a revisión humana sigue pendiente.

El apoyo limita su respuesta a 256 tokens y respeta una configuración menor del proveedor; clasificación y extracción conservan sus propios límites.

Validación adicional aislada del Nodo 2: `python evaluate_priority_cases.py --output informe_nodo2.json --repetitions 2 --interval 20`. Usa casos ficticios, consume llamadas al proveedor y compara apoyo y resultado combinado por separado. No ejecuta el grafo completo.

Validación contextual por grafo completo: `python evaluate_pipeline_context.py --output contexto.json --interval 65`. Para retomar solo controles pendientes, añadir `--case antecedente_y_infarto_actual infarto_descartado_signo_critico`. Las cuotas diarias no se resuelven solo espaciando solicitudes.
