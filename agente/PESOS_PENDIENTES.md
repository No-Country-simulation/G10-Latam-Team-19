# Preguntas para Michelle: pesos y extracción

Fuente: Proyecto alura_Data_UmbralScoreyReglas.pdf, pp. 7-11.
Los pesos numéricos se incorporaron; las siguientes interpretaciones son temporales,
no acuerdos clínicos nuevos. No se infieren edades, diagnósticos ni datos ausentes.

| Consulta concreta | Comportamiento actual | Función dentro de extracción y por qué importa |
| --- | --- | --- |
| ¿Nombre e identificación son alternativos o ambos obligatorios? ¿El ID sustituye un nombre ausente? | La ausencia del nombre no penaliza ni marca el campo como crítico; el ID faltante tampoco añade descuento. | La extracción conserva `null` cuando no hay nombre; la identificación nominal queda disponible para decisiones posteriores. |
| ¿Basta diagnóstico o CIE-10, o deben estar ambos? | Lectura literal de «o»: 0.15 solo si faltan ambos; no se genera un código para compensar la ausencia. | Decide qué evidencia clínica extraída basta para completar la categoría. El texto y el código podrían además contradecirse: no hay validador de equivalencia. |
| ¿Cuál es el nombre/tipo del campo vía y su catálogo de valores? | No existe en MedicamentoPrescrito ni en el schema del PDF. Se comprueban medicamento y dosis; vía queda pendiente. | Debe extraerse asociada a cada fármaco para verificar administración. Sin campo, no puede distinguirse vía ausente de vía que se perdió al validar. No usar frecuencia como sustituto. |
| ¿Los 0.30 de receta se descuentan una vez por categoría, por subcampo o por fármaco? ¿Frecuencia se descuenta si no hay ningún medicamento? | Una vez por categoría; frecuencia añade 0.05, también con lista vacía. Solo se aplica con tipo Receta Medica. | Evita multiplicar sanciones por longitud de la receta. Determina el score de recetas incompletas y qué hacer con tratamientos en epicrisis o sin clasificación. |
| ¿Cómo identificar pediatría cuando falta unidad_edad? ¿Qué edades/unidades cuentan como pediátricas? | Peso 0.30 registrado pero no aplicado. No se deduce pediatría del número ni se inventa una unidad. | Permite interpretar correctamente edad y rangos posteriores. El schema asigna años por defecto si se omite la unidad; hace falta distinguir valor explícito de valor por defecto. El prompt ya solicita null cuando no consta. |
| ¿Qué evidencia permite afirmar «adulto evidente»? ¿Qué descuento corresponde a edad ausente en menores o contexto desconocido? | Se conserva la regla previa de penalizar toda edad ausente con 0.15. Edad cero cuenta como presente. | Evita que la ausencia de edad pase sin descuento; falta una señal contextual para aplicar la condición del PDF sin inventar datos. |
| ¿En qué documentos son obligatorios los signos vitales y cuáles son los mínimos? | Si existe el objeto, se revisan los cinco campos y se resta 0.10 una vez. Un objeto null no activa la regla. | Distingue «no aplica» de «faltan todos». Sin criterio, una receta administrativa podría penalizarse injustificadamente o un documento clínico incompleto pasar sin descuento. |
| ¿Qué diagnósticos dependen del sexo y qué hacer si falta en ellos? | Se usa 0.05 como descuento base por sexo ausente; no se clasifica dependencia del diagnóstico. | Permite valorar si falta información necesaria para interpretar el documento. El PDF solo cuantifica diagnósticos no dependientes; no autoriza a inventar una sanción mayor. |
| ¿Qué señal indica OCR ambiguo, contradicciones, diagnóstico sensible a edad o receta de alto riesgo? | No se detectan ni se fuerzan bandas por estas condiciones. | La sección narrativa exige confianza baja en esos casos, pero el schema no contiene evidencia de legibilidad/contradicción ni define detección o fórmula. No basta con completar campos. |
| ¿Qué score consumirá el filtro Nodo 1 y cómo se relaciona con el score de clasificación? | Se publica extraction_confidence_score; no se reemplaza score_confianza_clasificacion ni final_confidence_score. | El PDF pide score matemático; el clasificador actual aún solicita uno al LLM. El equipo debe acordar qué valor controla el filtro para que estos descuentos tengan efecto operativo. |
| ¿Los límites son <0.75, [0.75,0.90) y >=0.90? ¿Qué prevalece ante urgencia con score bajo? | No se modifica prioridad ni enrutamiento. | La tabla y la prosa difieren en algunos puntos (sexo ausente: 0.95 frente a confianza media; dosis de alto riesgo y bandas). Se necesitan límites continuos para valores como 0.895 y precedencia de reglas. |

## Validación y límites

Las pruebas cubren pesos, descuentos acumulados, límite cero, recetas con entradas
parcialmente completas, signos vitales, edad cero y las dos rutas de extracción.
Las expectativas de interpretaciones temporales se prueban para que cualquier
cambio posterior sea explícito. No prueban exactitud clínica, OCR, proveedores
reales ni el grafo completo. La tabla numérica tiene prioridad en esta adaptación;
las contradicciones con la narrativa quedan para confirmar con Datos.
