import Link from "next/link";
import { ChevronDown } from "lucide-react";
import { PasosProcesamiento } from "@/components/pasos-procesamiento";

const GRUPOS = [
  {
    titulo: "Sobre MediFlow",
    preguntas: [
      {
        pregunta: "¿Qué hace MediFlow?",
        respuesta:
          "Recibe documentos clínicos, los clasifica, extrae los datos esenciales (paciente, médico, diagnóstico, CIE-10) y los enruta al destino correcto.",
      },
      {
        pregunta: "¿Cómo procesa MediFlow un documento?",
        respuesta: <PasosProcesamiento />,
      },
      {
        pregunta: "¿Qué tipos de documento reconoce?",
        respuesta:
          "Recetas médicas, informes de estudio, informes de laboratorio, órdenes de solicitud de procedimiento, epicrisis / informes de alta y certificados médicos. Si no encaja en ninguno, se marca como desconocido y pasa a revisión.",
      },
      {
        pregunta: "¿Cómo cargo un documento?",
        respuesta:
          "Desde la pestaña Cargar: pega el texto del documento, elige el canal de origen y presiona Procesar documento. Al terminar verás el resultado del triaje.",
      },
    ],
  },
  {
    titulo: "Prioridad y enrutamiento",
    preguntas: [
      {
        pregunta: "¿Qué significan los niveles de prioridad?",
        respuesta:
          "Rutina se procesa en el flujo normal, Prioritario se atiende antes y Urgente se deriva de inmediato a atención de guardia.",
      },
      {
        pregunta: "¿A dónde se envía cada documento?",
        respuesta:
          "A uno de los destinos: Cola de Emergencia Médica, Auditoría de Autorizaciones, Farmacia Hospitalaria, Cola de Revisión Humana o Historia Clínica Electrónica. Cada resultado incluye la justificación del enrutamiento.",
      },
    ],
  },
  {
    titulo: "Auditoría humana",
    preguntas: [
      {
        pregunta: "¿Cuándo interviene una persona?",
        respuesta:
          "Cuando la confianza es baja o hay datos ilegibles o faltantes: el documento se deriva a la cola de auditoría humana.",
      },
      {
        pregunta: "¿Qué pasa si apruebo o rechazo un caso?",
        respuesta:
          "Aprobar lo marca como validado; rechazar lo marca como rechazado y lo saca de la cola pendiente. La decisión queda registrada en el backend.",
      },
    ],
  },
  {
    titulo: "Datos y almacenamiento",
    preguntas: [
      {
        pregunta: "¿Dónde se guardan los documentos?",
        respuesta:
          "En OCI Object Storage, organizados por estado: recibidos, procesados, auditoría humana y validados. La ruta exacta aparece al pie del detalle de cada caso.",
      },
    ],
  },
];

export default function FaqPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 space-y-8 px-4 pb-16 pt-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Preguntas frecuentes</h1>
        <p className="text-muted-foreground">
          Cómo funciona el triaje, la priorización y la auditoría humana.
        </p>
      </header>

      {GRUPOS.map(({ titulo, preguntas }) => (
        <section key={titulo} className="space-y-3">
          <h2 className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">
            {titulo}
          </h2>
          <div className="space-y-2">
            {preguntas.map(({ pregunta, respuesta }) => (
              <details
                key={pregunta}
                className="group rounded-2xl bg-card shadow-sm ring-1 ring-foreground/5 open:ring-primary/30"
              >
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded-2xl p-5 font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
                  {pregunta}
                  <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
                </summary>
                <div className="px-5 pb-5 text-sm text-muted-foreground">{respuesta}</div>
              </details>
            ))}
          </div>
        </section>
      ))}

      <p className="rounded-2xl bg-secondary/60 p-5 text-sm">
        ¿Listo para probar?{" "}
        <Link href="/" className="font-medium text-primary underline-offset-4 hover:underline">
          Carga un documento
        </Link>{" "}
        o revisa los{" "}
        <Link href="/auditoria" className="font-medium text-primary underline-offset-4 hover:underline">
          casos en auditoría
        </Link>
        .
      </p>
    </main>
  );
}
