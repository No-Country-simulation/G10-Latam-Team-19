// Única capa de acceso a datos del frontend. Hoy responde con mocks; el
// backend real solo expone POST /triage (rama feature/backend), así que el
// resto de funciones seguirá en mock hasta que existan endpoints de lectura.
import type {
  DocumentoClinicoRequest,
  EstadoDocumento,
  TriageResponse,
} from "@/types/triage";
import { TRIAJES_MOCK } from "@/lib/mocks/triajes";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export type DecisionAuditoria = "aprobado" | "rechazado";

export interface Triaje extends TriageResponse {
  estado: EstadoDocumento;
  decision_auditoria: DecisionAuditoria | null;
}

// Estado en memoria (se reinicia al recargar el servidor): simula la
// persistencia por estado que en producción hará OCI Object Storage.
const triajes: Triaje[] = TRIAJES_MOCK.map((t) => ({
  ...t,
  estado: t.decision_enrutamiento.requiere_auditoria_humana
    ? "auditoria_humana"
    : "procesados",
  decision_auditoria: null,
}));

const latencia = () => new Promise((r) => setTimeout(r, 150));

export async function listarTriajes(): Promise<Triaje[]> {
  await latencia();
  return [...triajes].sort((a, b) => b.timestamp.localeCompare(a.timestamp));
}

export async function obtenerTriaje(id: string): Promise<Triaje | null> {
  await latencia();
  return triajes.find((t) => t.documento_id === id) ?? null;
}

export async function listarAuditoria(): Promise<Triaje[]> {
  const todos = await listarTriajes();
  return todos.filter((t) => t.estado === "auditoria_humana");
}

/** Aprobar mueve el documento a `validados`; rechazar lo deja en auditoría marcado. */
export async function resolverAuditoria(
  id: string,
  decision: DecisionAuditoria,
): Promise<Triaje | null> {
  await latencia();
  const triaje = triajes.find((t) => t.documento_id === id);
  if (!triaje) return null;
  triaje.decision_auditoria = decision;
  if (decision === "aprobado") triaje.estado = "validados";
  return triaje;
}

/** Con NEXT_PUBLIC_API_URL usa el POST /triage real; sin ella, devuelve un mock. */
export async function procesarDocumento(
  req: DocumentoClinicoRequest,
): Promise<TriageResponse> {
  if (API_URL) {
    const res = await fetch(`${API_URL}/triage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error(`POST /triage falló (${res.status})`);
    return res.json();
  }
  await latencia();
  return { ...TRIAJES_MOCK[1], documento_id: req.documento_id, canal_origen: req.canal_origen };
}
