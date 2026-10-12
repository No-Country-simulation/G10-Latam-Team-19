/** Pasos que sigue el agente al procesar un documento. Fuente única para la FAQ y el estado vacío. */
export const PASOS_PROCESAMIENTO = [
  { titulo: "Recibido", detalle: "Documento y canal de origen" },
  { titulo: "Clasificando", detalle: "Tipo y especialidad" },
  { titulo: "Extrayendo datos", detalle: "Paciente, médico, diagnóstico" },
  { titulo: "Validando", detalle: "Consistencia y confianza" },
  { titulo: "Enrutando", detalle: "Destino y prioridad" },
] as const;
