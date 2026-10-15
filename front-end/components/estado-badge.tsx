import { Badge } from "@/components/ui/badge";
import type { EstadoDocumento } from "@/types/triage";

const ETIQUETA: Record<EstadoDocumento, string> = {
  recibidos: "Recibido",
  procesados: "Procesado",
  auditoria_humana: "En auditoría",
  validados: "Validado",
};

export function EstadoBadge({ estado }: { estado: EstadoDocumento }) {
  return (
    <Badge variant={estado === "auditoria_humana" ? "secondary" : "outline"}>
      {ETIQUETA[estado]}
    </Badge>
  );
}
