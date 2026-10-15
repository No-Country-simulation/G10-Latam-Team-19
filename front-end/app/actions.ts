"use server";

import { randomUUID } from "node:crypto";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { procesarDocumento } from "@/lib/api";
import { validarCarga } from "@/lib/validacion";

export interface EstadoCarga {
  error: string | null;
}

export async function cargarDocumento(
  _anterior: EstadoCarga,
  formData: FormData,
): Promise<EstadoCarga> {
  const validacion = validarCarga({
    texto: formData.get("documento_texto"),
    canal: formData.get("canal_origen"),
    tipo: formData.get("tipo_archivo"),
  });
  if (!validacion.ok) return { error: validacion.error };

  let id: string;
  try {
    const triaje = await procesarDocumento({
      documento_id: `DOC-${randomUUID()}`,
      ...validacion.datos,
    });
    id = triaje.documento_id;
  } catch (error) {
    // Solo el tipo de fallo: el mensaje no incluye el texto clínico ni el cuerpo de la respuesta.
    console.error("cargarDocumento:", error instanceof Error ? error.message : "error desconocido");
    return { error: "No se pudo procesar el documento. Intentá nuevamente." };
  }

  revalidatePath("/", "layout");
  redirect(`/triaje/${encodeURIComponent(id)}`);
}
