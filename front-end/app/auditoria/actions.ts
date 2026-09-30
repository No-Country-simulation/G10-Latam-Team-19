"use server";

import { revalidatePath } from "next/cache";
import { resolverAuditoria, type DecisionAuditoria } from "@/lib/api";

export async function resolver(id: string, decision: DecisionAuditoria) {
  await resolverAuditoria(id, decision);
  revalidatePath("/auditoria");
  revalidatePath("/historial");
  revalidatePath(`/triaje/${id}`);
}
