import { Badge } from "@/components/ui/badge";
import { ETIQUETA_ESTADO } from "@/lib/formato";
import { estadoVisible } from "@/lib/triajes/consultas";
import type { Triaje } from "@/lib/triajes/tipos";

const VARIANTE = {
  auditoria_humana: "secondary",
  rechazados: "destructive",
} as const;

/** Estado del documento tal como lo ve el usuario (un rechazado se muestra como "Rechazado"). */
export function EstadoBadge({ triaje }: { triaje: Pick<Triaje, "estado" | "decision_auditoria"> }) {
  const estado = estadoVisible(triaje);
  return (
    <Badge variant={VARIANTE[estado as keyof typeof VARIANTE] ?? "outline"}>
      {ETIQUETA_ESTADO[estado]}
    </Badge>
  );
}
