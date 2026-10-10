# Objetivo semanal: estado actual

## Implementado

- Extracción: prompt ajustado y via por medicamento conservada en ambas rutas.
- Confianza: nombre de paciente no penaliza; medicamento/dosis/vía comparten 0.30 en recetas.
- Nodo 2: apoyo LLM sobre diagnostico_principal y estudio_realizado.
- Fallback: structured output, JSON manual validado, RuntimeError si ambas rutas fallan.
- Máxima gravedad entre reglas y apoyo; destino recalculado preservando auditoría de medicamentos.
- Sin textos clínicos de apoyo, no se llama al proveedor. El gate de score bajo precede al Nodo 2.

## Validación

Suite local: 103 pruebas, 101 exitosas y 2 fallos esperados de reglas determinísticas.
Se validaron los cinco casos reales en Groq con pausas. El primer prompt de apoyo
mantuvo alto riesgo en Rutina. Después de precisar exacerbación activa, se repitió
ese caso con el prompt final: Prioritario, Auditoria_Autorizaciones, auditoría True.
La integración ahora exige explícitamente la prioridad de ese caso.
Los otros tres casos sin conflicto cumplieron sus expectativas en la ejecución completa.
Pediatría sigue Urgente por el umbral determinístico >38.0°C; no se rebaja por LLM.
El prompt final fue revalidado específicamente en alto riesgo; no se repitieron de nuevo
los otros cuatro casos después de esa última precisión.

## Pendientes

- Michelle: discrepancia pediátrica, identidad y score de signos vitales incompletos.
- Revisión del tipo documental del ejemplo de emergencia.
- Ampliar casos nuevos y repetir para medir estabilidad del proveedor.
- Manejo automático de errores de proveedor para revisión humana: hoy se propagan explícitamente.
- No hay nueva tabla numérica de pesos; se conserva la anterior con las decisiones documentadas.

## Revalidación final

Cinco casos ejecutados con prompt final, incluidos reintentos de alto riesgo y dosis ausente por cuota. Cuatro cumplen; pediatría mantiene la contradicción de Datos. Apoyo limitado a 256 tokens (o configuración menor). Suite: 104 pruebas, 102 exitosas y 2 fallos esperados.

## Casos adicionales del apoyo

Seis casos ficticios, dos pasadas reales: apoyo cumple 12/12; prioridad combinada 8/12. Negación y antecedente remoto producen falsos positivos en palabras clave, repetidos en ambas pasadas. Sin errores de proveedor. Evaluación aislada de Nodo 2; pendiente comprobación a través de extracción antes de concluir efectos en el grafo completo.

## Comprobación de contexto en el grafo

Infarto descartado y antecedente remoto con diagnóstico explícito de control pasan en el grafo: la extracción excluye el infarto del diagnóstico principal actual. Dos controles de urgencia pendientes por cuota diaria TPD confirmada de Groq. Ejecutor detenido, sin reanudación automática. Las reglas directas de palabras clave siguen limitadas; no se cambió producción en esta comprobación.
