const PREGUNTAS = [
  {
    pregunta: "¿Qué hace MediFlow?",
    respuesta:
      "Recibe documentos clínicos, los clasifica, extrae los datos esenciales y los enruta al destino correcto.",
  },
  {
    pregunta: "¿Cuándo interviene una persona?",
    respuesta:
      "Cuando la confianza es baja, hay datos ilegibles o faltantes, el documento se deriva a la cola de auditoría humana.",
  },
  {
    pregunta: "¿Qué significan los niveles de prioridad?",
    respuesta:
      "Rutina se procesa en el flujo normal, Prioritario se atiende antes y Urgente dispara una alerta a la guardia médica.",
  },
  {
    pregunta: "¿Dónde se guardan los documentos?",
    respuesta:
      "En OCI Object Storage, organizados por estado: recibidos, procesados, auditoría humana y validados.",
  },
];

export default function FaqPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 space-y-6 px-4 py-8">
      <h1 className="text-2xl font-semibold">Preguntas frecuentes</h1>
      <dl className="space-y-5">
        {PREGUNTAS.map(({ pregunta, respuesta }) => (
          <div key={pregunta} className="space-y-1">
            <dt className="font-medium">{pregunta}</dt>
            <dd className="text-muted-foreground">{respuesta}</dd>
          </div>
        ))}
      </dl>
    </main>
  );
}
