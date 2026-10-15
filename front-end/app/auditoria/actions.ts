"use server";

import { revalidatePath } from "next/cache";
import { resolverAuditoria } from "@/lib/api";
import { esDecisionAuditoria, esIdDocumento } from "@/lib/validacion";

// Los argumentos de una server action llegan del navegador: se validan aunque la UI los fije con bind().
export async function resolver(id: string, decision: string) {
  if (!esIdDocumento(id) || !esDecisionAuditoria(decision)) {
    throw new Error("Solicitud de auditoría inválida.");
  }

  const triaje = await resolverAuditoria(id, decision);
  if (!triaje) throw new Error("El documento ya no existe.");

  revalidatePath("/", "layout");
}
