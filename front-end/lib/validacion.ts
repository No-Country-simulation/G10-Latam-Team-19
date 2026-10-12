import type { DocumentoClinicoRequest, TipoArchivo } from "@/types/triage";
import { DECISIONES_AUDITORIA, type DecisionAuditoria } from "@/lib/triajes/tipos";

export const CANALES = [
  "Guardia de Emergencias",
  "Consultorio Externo",
  "Laboratorio",
  "Farmacia",
] as const;

/** Mínimo que exige el backend (schemas.py: documento_texto min_length=10). */
export const MIN_TEXTO = 10;
/** Tope propio: evita enviar al agente textos desproporcionados (y el límite de 1 MB de las server actions). */
export const MAX_TEXTO = 200_000;

/** Tipos que el navegador sabe convertir a texto. IMAGEN queda fuera: requiere OCR. */
const TIPOS_ENVIABLES: readonly TipoArchivo[] = ["TEXTO", "JSON", "PDF"];

export type DatosCarga = Omit<DocumentoClinicoRequest, "documento_id">;

export type ResultadoValidacion =
  | { ok: true; datos: DatosCarga }
  | { ok: false; error: string };

/** Valida lo que llega del formulario de carga. Los valores vienen de FormData: nunca se confía en su tipo. */
export function validarCarga(entrada: {
  texto: unknown;
  canal: unknown;
  tipo: unknown;
}): ResultadoValidacion {
  const texto = typeof entrada.texto === "string" ? entrada.texto.trim() : "";
  if (texto.length < MIN_TEXTO) {
    return { ok: false, error: `El documento debe tener al menos ${MIN_TEXTO} caracteres.` };
  }
  if (texto.length > MAX_TEXTO) {
    return { ok: false, error: "El documento es demasiado largo para procesarlo." };
  }

  const canal = CANALES.find((c) => c === entrada.canal);
  if (!canal) return { ok: false, error: "Elegí un canal de origen válido." };

  const tipo = TIPOS_ENVIABLES.find((t) => t === entrada.tipo);
  if (!tipo) return { ok: false, error: "Tipo de archivo no soportado." };

  return { ok: true, datos: { documento_texto: texto, canal_origen: canal, tipo_archivo: tipo } };
}

export function esDecisionAuditoria(v: unknown): v is DecisionAuditoria {
  return DECISIONES_AUDITORIA.some((d) => d === v);
}

/** IDs como "DOC-CLIN-2026-8942". Rechaza barras, puntos y espacios: el ID termina en una URL del backend. */
export function esIdDocumento(v: unknown): v is string {
  return typeof v === "string" && /^[A-Za-z0-9_-]{1,80}$/.test(v);
}
