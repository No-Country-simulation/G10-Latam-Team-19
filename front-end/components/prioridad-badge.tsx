import { Badge } from "@/components/ui/badge";
import type { NivelPrioridad } from "@/types/triage";

const VARIANTE: Record<NivelPrioridad, "destructive" | "default" | "outline"> = {
  Urgente: "destructive",
  Prioritario: "default",
  Rutina: "outline",
};

export function PrioridadBadge({ nivel }: { nivel: NivelPrioridad }) {
  return <Badge variant={VARIANTE[nivel]}>{nivel}</Badge>;
}
