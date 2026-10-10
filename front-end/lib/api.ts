// Única capa de acceso a datos del frontend. 
// Conecta con el backend real y mantiene fallback a mocks para garantizar estabilidad.
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

// Estado en memoria (fallback): simula la persistencia si el backend falla.
const store = globalThis as typeof globalThis & { __mediflowTriajes?: Triaje[] };
const triajes: Triaje[] = (store.__mediflowTriajes ??= TRIAJES_MOCK.map((t) => ({
  ...t,
  estado: t.decision_enrutamiento.requiere_auditoria_humana
    ? "auditoria_humana"
    : "procesados",
  decision_auditoria: null,
})));

const latencia = () => new Promise((r) => setTimeout(r, 150));

/*
 * Adapta la respuesta del backend al tipo Triaje del frontend.
 */
function adaptarTriaje(response: any): Triaje {
  let estadoInferido: EstadoDocumento = "procesados";
  
  if (response.status === "validado") {
    estadoInferido = "validados";
  } else if (response.status === "rechazado") {
    estadoInferido = "auditoria_humana"; // Se queda en la carpeta, pero marcado
  } else if (response.decision_enrutamiento?.requiere_auditoria_humana) {
    estadoInferido = "auditoria_humana";
  }

  let decisionInferida: DecisionAuditoria | null = null;
  if (response.status === "validado") decisionInferida = "aprobado";
  if (response.status === "rechazado") decisionInferida = "rechazado";

  return {
    ...response,
    estado: response.estado ?? estadoInferido,
    decision_auditoria: response.decision_auditoria ?? decisionInferida,
  } as Triaje;
}

export async function listarTriajes(): Promise<Triaje[]> {
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
  
  await latencia();
  return [...triajes].sort((a, b) => b.timestamp.localeCompare(a.timestamp));
}

export async function obtenerTriaje(id: string): Promise<Triaje | null> {
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

  await latencia();
  return triajes.find((t) => t.documento_id === id) ?? null;
}

export async function listarAuditoria(): Promise<Triaje[]> {
  const todos = await listarTriajes();
  return todos.filter(
    (t) => t.estado === "auditoria_humana" && t.decision_auditoria !== "rechazado"
  );
}

/** 
 * Aprueba o rechaza un documento en la cola de auditoría.
 * Se conecta a los endpoints reales: /aprobar y /rechazar.
 * Mantiene el fallback local por seguridad.
 */
export async function resolverAuditoria(
  id: string,
  decision: DecisionAuditoria,
): Promise<Triaje | null> {
  if (!API_URL) throw new Error("Falta NEXT_PUBLIC_API_URL en .env.local");
  
  try {
    const accion = decision === "aprobado" ? "aprobar" : "rechazar";
    
    const res = await fetch(`${API_URL}/triage/${id}/${accion}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        comentario: `Decisión tomada desde interfaz web: ${decision}`,
        revisor: "Auditor MediFlow",
      }),
    });
    
    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Resolver auditoría falló (${res.status}): ${errorText}`);
    }
    
    const data: TriageResponse = await res.json();
    return adaptarTriaje(data);
    
  } catch (error) {
    console.warn(`Fallo al conectar con /triage/${id}/${decision}. Usando fallback local.`, error);
    
    // FALLBACK LOCAL: Actualiza el estado en memoria para que la UI reaccione
    const triajesActuales = await listarTriajes();
    const triaje = triajesActuales.find((t) => t.documento_id === id);
    
    if (triaje) {
      triaje.decision_auditoria = decision;
      if (decision === "aprobado") {
        triaje.estado = "validados";
      }
    }
    
    return triaje || null;
  }
}

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
  
  await latencia();
  return { ...TRIAJES_MOCK[1], documento_id: req.documento_id, canal_origen: req.canal_origen } as TriageResponse;
}