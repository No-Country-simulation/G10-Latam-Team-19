import { PASOS_PROCESAMIENTO } from "@/lib/pasos";

export function PasosProcesamiento() {
  return (
    <ol className="space-y-3">
      {PASOS_PROCESAMIENTO.map(({ titulo, detalle }, i) => (
        <li key={titulo} className="flex items-start gap-3">
          <span className="grid size-6 shrink-0 place-items-center rounded-full bg-secondary text-xs font-semibold text-secondary-foreground">
            {i + 1}
          </span>
          <div className="text-sm">
            <p className="font-medium">{titulo}</p>
            <p className="text-xs text-muted-foreground">{detalle}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
