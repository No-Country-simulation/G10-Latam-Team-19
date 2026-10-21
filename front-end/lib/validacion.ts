import type { DocumentoClinicoRequest, TipoArchivo } from "@/types/triage";
import { DECISIONES_AUDITORIA, type DecisionAuditoria } from "@/lib/triajes/tipos";

/** Valor que se envía (formato del agente: "Guardia_Emergencias") → texto que ve el usuario. */
export const CANALES = {
  Guardia_Emergencias: "Guardia de Emergencias",
  Consultorio_Externo: "Consultorio Externo",
  Laboratorio: "Laboratorio",
  Farmacia: "Farmacia",
} as const;
export type Canal = keyof typeof CANALES;

const esCanal = (v: unknown): v is Canal => typeof v === "string" && Object.hasOwn(CANALES, v);

/** Mínimo que exige el backend (schemas.py: documento_texto min_length=10). */
export const MIN_TEXTO = 10;
/** Tope propio: evita enviar al agente textos desproporcionados (y el límite de 1 MB de las server actions). */
export const MAX_TEXTO = 200_000;

/**
 * Tipos cuyo texto ya está resuelto al enviar. IMAGEN entra porque la foto se transcribe
 * antes (POST /ocr) y la persona revisa ese texto: al backend llega como texto.
 */
const TIPOS_ENVIABLES: readonly TipoArchivo[] = ["TEXTO", "JSON", "PDF", "IMAGEN"];

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

  const canal = entrada.canal;
  if (!esCanal(canal)) return { ok: false, error: "Elegí un canal de origen válido." };

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
