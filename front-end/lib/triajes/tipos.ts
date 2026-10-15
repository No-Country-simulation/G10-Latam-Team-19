import type {
  DocumentoClinicoRequest,
  EstadoDocumento,
  TriageResponse,
} from "@/types/triage";

export const DECISIONES_AUDITORIA = ["aprobado", "rechazado"] as const;
export type DecisionAuditoria = (typeof DECISIONES_AUDITORIA)[number];

/** TriageResponse + campos que el frontend deriva del `status` del backend. */
export interface Triaje extends TriageResponse {
  estado: EstadoDocumento;
  decision_auditoria: DecisionAuditoria | null;
}

/** Contrato de acceso a datos. Lo cumplen el backend real (http) y el modo demo (memoria). */
export interface RepositorioTriajes {
  listar(): Promise<Triaje[]>;
  obtener(id: string): Promise<Triaje | null>;
  resolver(id: string, decision: DecisionAuditoria): Promise<Triaje | null>;
  procesar(req: DocumentoClinicoRequest): Promise<Triaje>;
}
