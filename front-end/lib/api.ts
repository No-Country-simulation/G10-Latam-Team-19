// Única capa de acceso a datos del frontend. 
// Conecta con el backend real (GET/POST /triage) y mantiene fallback a mocks 
// para garantizar que la demo funcione incluso si falta algún endpoint (ej. auditoría).
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

// Estado en memoria (se reinicia al reiniciar el servidor): simula la
// persistencia por estado que en producción hará OCI Object Storage. Vive en
// globalThis para que páginas y server actions compartan la misma instancia.
// Se usa como fallback si la API real no responde o le faltan campos.
const store = globalThis as typeof globalThis & { __mediflowTriajes?: Triaje[] };
const triajes: Triaje[] = (store.__mediflowTriajes ??= TRIAJES_MOCK.map((t) => ({
  ...t,
  estado: t.decision_enrutamiento.requiere_auditoria_humana
    ? "auditoria_humana"
    : "procesados",
  decision_auditoria: null,
})));

const latencia = () => new Promise((r) => setTimeout(r, 150));

/**
 * Adapta la respuesta del backend al tipo Triaje del frontend.
 * Si el backend no envía 'estado' o 'decision_auditoria', los infiere 
 * de forma segura para que la UI no se rompa.
 */
function adaptarTriaje(response: any): Triaje {
  return {
    ...response,
    estado: response.estado ?? (response.decision_enrutamiento.requiere_auditoria_humana ? "auditoria_humana" : "procesados"),
    decision_auditoria: response.decision_auditoria ?? null,
  } as Triaje;
}

export async function listarTriajes(): Promise<Triaje[]> {
  // 1. Intentar obtener datos reales del backend
  if (API_URL) {
    try {
      const res = await fetch(`${API_URL}/triage`, { cache: "no-store" });
      if (res.ok) {
        const data: TriageResponse[] = await res.json();
        return data.map(adaptarTriaje);
      }
    } catch (error) {
      console.warn("Fallo al conectar con GET /triage. Usando fallback local.", error);
    }
  }
  
  // 2. Fallback a mocks en memoria
  await latencia();
  return [...triajes].sort((a, b) => b.timestamp.localeCompare(a.timestamp));
}

export async function obtenerTriaje(id: string): Promise<Triaje | null> {
  // 1. Intentar obtener dato real del backend
  if (API_URL) {
    try {
      const res = await fetch(`${API_URL}/triage/${id}`, { cache: "no-store" });
      if (res.status === 404) return null;
      if (res.ok) {
        const data: TriageResponse = await res.json();
        return adaptarTriaje(data);
      }
    } catch (error) {
      console.warn(`Fallo al conectar con GET /triage/${id}. Usando fallback local.`, error);
    }
  }

  // 2. Fallback a mocks en memoria
  await latencia();
  return triajes.find((t) => t.documento_id === id) ?? null;
}

export async function listarAuditoria(): Promise<Triaje[]> {
  // Reutiliza listarTriajes (que ya intenta ir al backend primero)
  const todos = await listarTriajes();
  return todos.filter(
    (t) => t.estado === "auditoria_humana" && t.decision_auditoria !== "rechazado"
  );
}

/** 
 * Aprobar mueve el documento a `validados`; rechazar lo deja en auditoría marcado.
 * Intenta llamar al backend, pero si el endpoint no existe aún, actualiza el store local 
 * para que la demo de auditoría siga funcionando visualmente.
 */
export async function resolverAuditoria(
  id: string,
  decision: DecisionAuditoria,
): Promise<Triaje | null> {
  // 1. Intentar llamar al endpoint real del backend (si lo han agregado)
  if (API_URL) {
    try {
      const res = await fetch(`${API_URL}/triage/${id}/auditoria`, {
        method: "POST", // Ajustar a PATCH si el backend lo define así
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision }),
      });
      
      if (res.ok) {
        const data: TriageResponse = await res.json();
        return adaptarTriaje(data);
      }
    } catch (error) {
      console.warn("Endpoint de auditoría no disponible. Usando fallback local para la demo.", error);
    }
  }

  // 2. Fallback local: Actualiza el estado en memoria para que la UI reaccione
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
    try {
      const res = await fetch(`${API_URL}/triage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      });
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`POST /triage falló (${res.status}): ${errorText}`);
      }
      return res.json();
    } catch (error) {
      console.error("Error en procesarDocumento (API):", error);
      throw error;
    }
  }
  
  // Fallback mock
  await latencia();
  return { ...TRIAJES_MOCK[1], documento_id: req.documento_id, canal_origen: req.canal_origen } as TriageResponse;
}