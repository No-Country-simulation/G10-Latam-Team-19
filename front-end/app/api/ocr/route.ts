import { NextResponse } from "next/server";
import { transcribirArchivo } from "@/lib/api";
import { ErrorOcr, validarArchivoOcr } from "@/lib/ocr";

export const runtime = "nodejs";
// Leer varias páginas con un modelo de visión puede tardar (relevante en plataformas con tope de duración).
export const maxDuration = 180;

const error = (mensaje: string, estado: number) => NextResponse.json({ error: mensaje }, { status: estado });

/**
 * El navegador no puede mandar la foto por una server action (límite de 1 MB), así que la sube
 * acá y esta ruta la reenvía al backend. Devuelve solo el texto: nada se guarda hasta que la
 * persona lo revisa y lo envía a procesar.
 */
export async function POST(request: Request) {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return error("No se pudo leer el archivo enviado.", 400);
  }

  const archivo = form.get("archivo");
  if (!(archivo instanceof File)) return error("Falta el archivo.", 400);

  const invalido = validarArchivoOcr(archivo);
  if (invalido) return error(invalido.message, invalido.estado);

  try {
    const { texto, paginas, paginasTotales } = await transcribirArchivo(archivo, archivo.name);
    return NextResponse.json({ texto, paginas, paginasTotales });
  } catch (e) {
    if (e instanceof ErrorOcr) {
      // Los errores del usuario (4xx) no son ruido de servidor; el resto sí queda en el log.
      if (e.estado === 0 || e.estado >= 500) console.error("[ocr]", e.estado, e.message);
      return error(e.message, e.estado === 0 ? 502 : e.estado);
    }
    console.error("[ocr] error inesperado", e);
    return error("No se pudo leer el archivo. Probá de nuevo o pegá el texto manualmente.", 500);
  }
}
