import type { TipoArchivo } from "@/types/triage";

export const MAX_BYTES = 10 * 1024 * 1024;

const TEXTO_PLANO: Record<string, TipoArchivo> = { ".txt": "TEXTO", ".json": "JSON" };
const IMAGENES = [".jpg", ".jpeg", ".png"];

export const EXTENSIONES_ACEPTADAS = [".pdf", ...IMAGENES, ...Object.keys(TEXTO_PLANO)];

export type ClaseArchivo =
  /** Se lee tal cual como texto. */
  | { clase: "texto"; tipo: TipoArchivo }
  /** Hay que extraer el texto antes de enviarlo. */
  | { clase: "pdf" }
  /** Foto o escaneo: el backend lo transcribe con el modelo de visión (POST /ocr). */
  | { clase: "imagen" }
  | { clase: "rechazado"; motivo: string };

export function extension(nombre: string): string {
  const punto = nombre.lastIndexOf(".");
  return punto <= 0 ? "" : nombre.slice(punto).toLowerCase();
}

/** Decide qué hacer con un archivo a partir de su nombre y tamaño, sin leerlo. */
export function clasificarArchivo(archivo: { name: string; size: number }): ClaseArchivo {
  const ext = extension(archivo.name);

  if (!EXTENSIONES_ACEPTADAS.includes(ext)) {
    return { clase: "rechazado", motivo: "Formato no soportado. Usá PDF, imagen (JPG o PNG), TXT o JSON." };
  }
  if (archivo.size === 0) return { clase: "rechazado", motivo: "El archivo está vacío." };
  if (archivo.size > MAX_BYTES) {
    return { clase: "rechazado", motivo: "El archivo supera los 10 MB." };
  }
  if (IMAGENES.includes(ext)) return { clase: "imagen" };
  if (ext === ".pdf") return { clase: "pdf" };
  return { clase: "texto", tipo: TEXTO_PLANO[ext] };
}

export function formatearTamano(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
