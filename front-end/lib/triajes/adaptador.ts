import { ESTADOS_DOCUMENTO, type EstadoDocumento, type TriageResponse } from "@/types/triage";
import { DECISIONES_AUDITORIA, type DecisionAuditoria, type Triaje } from "./tipos";

/** El backend devolvió algo que no cumple el contrato de TriageResponse. */
export class RespuestaInvalidaError extends Error {
  constructor(motivo: string) {
    super(`Respuesta del backend inválida: ${motivo}`);
    this.name = "RespuestaInvalidaError";
  }
}

function esObjeto(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** Comprueba los campos que la UI lee sin protección; no es una validación completa del esquema. */
export function esTriageResponse(v: unknown): v is TriageResponse {
  if (!esObjeto(v)) return false;
  const { clasificacion, datos_extraidos, decision_enrutamiento } = v;
  return (
    typeof v.documento_id === "string" &&
    v.documento_id.length > 0 &&
    typeof v.timestamp === "string" &&
    esObjeto(clasificacion) &&
    typeof clasificacion.nivel_prioridad === "string" &&
    typeof clasificacion.score_confianza_clasificacion === "number" &&
    esObjeto(datos_extraidos) &&
    esObjeto(datos_extraidos.paciente) &&
    esObjeto(decision_enrutamiento) &&
    typeof decision_enrutamiento.requiere_auditoria_humana === "boolean"
  );
}

function inferirEstado(r: TriageResponse): EstadoDocumento {
  if (r.status === "validados") return "validados";
  // Un rechazado se queda en la carpeta de auditoría, pero marcado.
  if (r.status === "rechazado") return "auditoria_humana";
  return r.decision_enrutamiento.requiere_auditoria_humana ? "auditoria_humana" : "procesados";
}

function inferirDecision(r: TriageResponse): DecisionAuditoria | null {
  if (r.status === "validado") return "aprobado";
  if (r.status === "rechazado") return "rechazado";
  return null;
}

/** Adapta la respuesta del backend al tipo Triaje. Lanza si no cumple el contrato. */
export function adaptarTriaje(respuesta: unknown): Triaje {
  if (!esTriageResponse(respuesta)) {
    throw new RespuestaInvalidaError("faltan campos obligatorios del triaje");
  }
  const extra = respuesta as TriageResponse & { estado?: unknown; decision_auditoria?: unknown };
  const estado = ESTADOS_DOCUMENTO.find((e) => e === extra.estado);
  const decision = DECISIONES_AUDITORIA.find((d) => d === extra.decision_auditoria);

  return {
    ...respuesta,
    estado: estado ?? inferirEstado(respuesta),
    decision_auditoria: decision ?? inferirDecision(respuesta),
  };
}
