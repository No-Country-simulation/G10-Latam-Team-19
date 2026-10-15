// Única puerta de acceso a datos del frontend (solo servidor: páginas y server actions).
// Con API_URL usa el backend real; sin ella entra en modo demo con datos de ejemplo en memoria.
// Un fallo del backend NO cae a los datos de ejemplo: se propaga y lo muestra app/error.tsx,
// para no presentar pacientes ficticios como si fueran reales.
import type { DocumentoClinicoRequest } from "@/types/triage";
import { TRIAJES_MOCK } from "@/lib/mocks/triajes";
import { filtrarPendientesAuditoria } from "@/lib/triajes/consultas";
import { crearRepositorioHttp } from "@/lib/triajes/http";
import { crearRepositorioMemoria, sembrarTriajes } from "@/lib/triajes/memoria";
import type { DecisionAuditoria, RepositorioTriajes, Triaje } from "@/lib/triajes/tipos";

export type { DecisionAuditoria, Triaje } from "@/lib/triajes/tipos";

// API_URL es la variable preferida (no viaja al navegador); NEXT_PUBLIC_API_URL se mantiene por compatibilidad.
const API_URL = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;

export const MODO_DEMO = !API_URL;

// globalThis: páginas y server actions deben ver la misma instancia entre recargas en desarrollo.
const global = globalThis as typeof globalThis & { __mediflowTriajes?: Triaje[] };

const repositorio: RepositorioTriajes = API_URL
  ? crearRepositorioHttp(API_URL)
  : crearRepositorioMemoria(
      (global.__mediflowTriajes ??= sembrarTriajes(TRIAJES_MOCK)),
      TRIAJES_MOCK[1],
    );

export const listarTriajes = (): Promise<Triaje[]> => repositorio.listar();

export const obtenerTriaje = (id: string): Promise<Triaje | null> => repositorio.obtener(id);

export async function listarAuditoria(): Promise<Triaje[]> {
  return filtrarPendientesAuditoria(await repositorio.listar());
}

/** Aprueba o rechaza un documento de la cola de auditoría. Devuelve null si no existe. */
export const resolverAuditoria = (id: string, decision: DecisionAuditoria): Promise<Triaje | null> =>
  repositorio.resolver(id, decision);

export const procesarDocumento = (req: DocumentoClinicoRequest): Promise<Triaje> =>
  repositorio.procesar(req);
