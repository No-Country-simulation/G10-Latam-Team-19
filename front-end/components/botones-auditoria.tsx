"use client";

import { useState, useTransition } from "react";
import { Loader2 } from "lucide-react";
import { resolver } from "@/app/auditoria/actions";
import type { DecisionAuditoria } from "@/lib/triajes/tipos";
import { cn } from "@/lib/utils";

const BOTONES: { decision: DecisionAuditoria; etiqueta: string; enCurso: string; clase: string }[] = [
  {
    decision: "aprobado",
    etiqueta: "Aprobar",
    enCurso: "Aprobando…",
    clase: "bg-primary text-primary-foreground",
  },
  {
    decision: "rechazado",
    etiqueta: "Rechazar",
    enCurso: "Rechazando…",
    clase: "border text-destructive hover:bg-destructive/5",
  },
];

/** Aprobar / Rechazar. Mientras una decisión viaja al backend, ambos botones quedan bloqueados. */
export function BotonesAuditoria({ id }: { id: string }) {
  const [pendiente, iniciar] = useTransition();
  const [elegida, setElegida] = useState<DecisionAuditoria | null>(null);

  function decidir(decision: DecisionAuditoria) {
    setElegida(decision);
    iniciar(() => resolver(id, decision));
  }

  return (
    <div className="flex gap-2" aria-busy={pendiente}>
      {BOTONES.map(({ decision, etiqueta, enCurso, clase }) => {
        const activo = pendiente && elegida === decision;
        return (
          <button
            key={decision}
            type="button"
            disabled={pendiente}
            onClick={() => decidir(decision)}
            className={cn(
              "inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-opacity disabled:opacity-60",
              clase,
            )}
          >
            {activo && <Loader2 className="size-4 animate-spin" />}
            {activo ? enCurso : etiqueta}
          </button>
        );
      })}
    </div>
  );
}
