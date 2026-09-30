import { cn } from "@/lib/utils";

/** Barra de confianza; se marca en rojo cuando el caso requiere auditoría humana. */
export function Confianza({
  valor,
  enRiesgo = false,
}: {
  valor: number;
  enRiesgo?: boolean;
}) {
  const porcentaje = Math.round(valor * 100);
  return (
    <div className="flex items-center gap-2">
      <div
        role="meter"
        aria-label="Confianza de la clasificación"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={porcentaje}
        className="h-1.5 w-16 overflow-hidden rounded-full bg-muted"
      >
        <div
          className={cn("h-full rounded-full", enRiesgo ? "bg-destructive" : "bg-primary")}
          style={{ width: `${porcentaje}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground">{porcentaje}%</span>
    </div>
  );
}
