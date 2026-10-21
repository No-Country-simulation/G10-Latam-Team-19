import { clasificarArchivo, MAX_BYTES } from "@/lib/archivos";

export interface Transcripcion {
  texto: string;
  /** Páginas efectivamente leídas (1 para una imagen). */
  paginas: number;
  /** Páginas del PDF original. Si es mayor que `paginas`, se leyó solo el principio. */
  paginasTotales: number;
}

/**
 * Fallo al transcribir. `estado` es el código HTTP que corresponde devolver a quien llamó
 * (0 = no hubo respuesta del backend). `message` está redactado para mostrárselo a la persona.
 */
export class ErrorOcr extends Error {
  constructor(
    mensaje: string,
    readonly estado: number,
  ) {
    super(mensaje);
    this.name = "ErrorOcr";
  }
}

/** POST /ocr lee una imagen con un modelo de visión (puede tardar) y hasta 3 páginas de un PDF. */
const TIMEOUT_OCR_MS = 180_000;

const GENERICO = "No se pudo leer el archivo. Probá de nuevo o pegá el texto manualmente.";

/**
 * Convierte la respuesta de error del backend en un mensaje para la persona. Solo se muestra
 * el detalle de los errores pensados para el usuario (archivo inválido o sin texto legible):
 * en un 5xx el detalle trae trazas de configuración o del proveedor, que no se exponen.
 */
function mensajeParaUsuario(estado: number, detalle: unknown): string {
  if ([413, 415, 422].includes(estado) && typeof detalle === "string" && detalle) return detalle;
  if (estado === 503) {
    return "La lectura de imágenes no está disponible en este momento. Pegá el texto manualmente.";
  }
  return GENERICO;
}

/** Valida en el servidor del frontend lo que llega por el formulario, antes de reenviarlo. */
export function validarArchivoOcr(archivo: { name: string; size: number }): ErrorOcr | null {
  const clase = clasificarArchivo(archivo);
  if (clase.clase === "imagen" || clase.clase === "pdf") return null;
  const motivo =
    clase.clase === "rechazado" ? clase.motivo : "Solo se transcriben imágenes (JPG o PNG) y PDF.";
  // Mismos códigos que devuelve el backend para los mismos casos.
  const estado = archivo.size === 0 ? 422 : archivo.size > MAX_BYTES ? 413 : 415;
  return new ErrorOcr(motivo, estado);
}

export async function transcribirConBackend(
  baseUrl: string,
  archivo: Blob,
  nombre: string,
  fetchImpl: typeof fetch = fetch,
): Promise<Transcripcion> {
  const form = new FormData();
  form.append("archivo", archivo, nombre);

  let respuesta: Response;
  try {
    respuesta = await fetchImpl(`${baseUrl.replace(/\/+$/, "")}/ocr`, {
      method: "POST",
      body: form,
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_OCR_MS),
    });
  } catch {
    throw new ErrorOcr("No hay conexión con el backend. Revisá que esté en marcha.", 0);
  }

  const cuerpo: unknown = await respuesta.json().catch(() => null);
  const detalle = (cuerpo as { detail?: unknown } | null)?.detail;

  if (!respuesta.ok) throw new ErrorOcr(mensajeParaUsuario(respuesta.status, detalle), respuesta.status);

  const datos = cuerpo as { texto?: unknown; paginas?: unknown; paginas_totales?: unknown } | null;
  if (typeof datos?.texto !== "string" || !datos.texto.trim()) {
    throw new ErrorOcr(GENERICO, 502);
  }
  const paginas = typeof datos.paginas === "number" ? datos.paginas : 1;
  const paginasTotales = typeof datos.paginas_totales === "number" ? datos.paginas_totales : paginas;
  return { texto: datos.texto, paginas, paginasTotales };
}
