# Avance semanal: extracción y apoyo al Nodo 2

Estado al 10 de octubre de 2026. Implementación disponible para revisión;
la validación clínica y las respuestas pendientes de Datos no se consideran cerradas.

## Cambios implementados

- Prompt de extracción: datos explícitos independientes del nombre, vías normalizadas,
  dosis frente a concentración, tasas de parche, frecuencias y condiciones literales,
  y exclusión de diagnósticos negados/antecedentes como diagnóstico principal actual.
- Medicamentos: via inmediatamente después de nombre; catálogo ViaAdministracion.
- Confianza: medicamento/dosis/vía ausentes activan una sola categoría de 0.30
  en recetas. Frecuencia conserva 0.05 independiente. Nombre del paciente no penaliza.
  La etiqueta medicamentos_o_dosis se conserva por compatibilidad e incluye vía.
- Nodo 2: apoyo LLM sobre diagnostico_principal y estudio_realizado solamente.
  Máxima gravedad entre reglas y apoyo; destino calculado después de combinar,
  preservando medicamentos restringidos y alertas. El filtro de confianza precede al apoyo.
- Fallback: respuesta estructurada, JSON manual validado y error explícito si ambas fallan.
  Sin diagnóstico ni estudio no se llama al proveedor. Se registra prioridad y motivo del apoyo.
- Groq: salida configurable (800 por defecto), timeout 30 segundos, sin reintentos automáticos.
  El apoyo limita su salida a 256 tokens o una configuración inferior del proveedor.
- Corrección del valor por defecto de paciente.nombre: una coma sobrante lo convertía en tupla.

## Validación local

104 pruebas: 102 exitosas y 2 fallos esperados en reglas determinísticas.
Se cubren categoría agrupada, múltiples medicamentos, ambas rutas de extracción,
fallos del apoyo, presupuesto de salida, máximos de gravedad, destinos, alertas y grafo completo.
Las respuestas simuladas no miden precisión del proveedor.

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s agente -p 'test_*.py' -v
```

## Ejecuciones reales con Groq

Cinco casos de Michelle con el prompt final, incluyendo reintentos por cuota:

| Caso | Score | Prioridad/destino | Resultado |
| --- | --- | --- | --- |
| Rutina | 1.00 | Rutina / Historia clínica | Cumple |
| Emergencia | 1.00 | Urgente / Emergencia | Cumple |
| Alto riesgo | 1.00 | Prioritario / Auditoría | Cumple tras ajuste y reintento |
| Dosis y vía ausentes | 0.70 | Corte / Revisión humana | Cumple tras reintento |
| Pediatría | 0.90 | Urgente / Emergencia | No cumple Farmacia del ejemplo |

Seis casos adicionales del apoyo, dos pasadas: apoyo 12/12 conforme a expectativas;
prioridad combinada 8/12. Las cuatro discrepancias son dos casos repetidos:
infarto descartado y antecedente remoto activan palabras clave determinísticas.
Este ensayo aisló Nodo 2 con signos vitales normales; no representa el grafo completo.

En el grafo completo, infarto descartado y antecedente remoto con diagnóstico
explícito de control pasaron: extracción conservó control de salud normal.
Los controles de antecedente con infarto actual y negación con SpO2 88% siguen
pendientes de ejecución real por cuota diaria de Groq. Se detuvo el ejecutor.
No se compraron recursos, cambió de proveedor ni programó reanudación automática.

## Fuentes y decisiones pendientes con Michelle

El PDF de 17 páginas amplía criterios y casos, pero conserva la tabla previa y
un esquema anterior al repositorio. El esquema opcional no define penalizaciones.

- Lactantes >38.0°C son Urgente según la regla, pero el caso 5 espera Prioritario/Farmacia.
- Caso 5 espera score 1.00 aunque falta presión arterial; la tabla descuenta 0.10.
- La tabla incluye identidad -0.30, pero los casos sin identidad esperan 1.00.
  Se conserva la exclusión de nombre del objetivo semanal, sin reinterpretar identificación.
- Falta definir condiciones de unidad pediátrica, edad y sexo dependiente del diagnóstico.
- El caso de alto riesgo espera dolor severo sin explicitar intensidad en la entrada;
  el apoyo utiliza la exacerbación documentada, sin inventar riesgo vital.

## Pendientes técnicos

- Completar los dos controles reales bloqueados por cuota.
- Ampliar casos y repeticiones; esta muestra no demuestra estabilidad general.
- Revisar clasificación documental: emergencia fue etiquetada como Epicrisis/Informe de Alta.
- Derivar errores del proveedor a revisión humana controlada; hoy se propagan explícitamente.
- Palabras clave sin contexto pueden elevar diagnósticos negados/históricos si llegan sin filtrar.
  El apoyo no puede rebajar estas reglas ni signos vitales urgentes.
- Validar documentos largos con los límites de salida actuales.

Los ajustes realizados son de prompts y reglas; no se entrenó ni hizo fine-tuning del modelo.

## Ejecutores disponibles

Las llamadas reales requieren credenciales y consumen cuota. Los informes se guardan
con --output y los ejecutores permiten seleccionar casos o controlar intervalos:
evaluate_extraction.py, evaluate_priority_cases.py, evaluate_pipeline_context.py
y test_integration.py. Mantener separados errores de cuota y errores de precisión.
