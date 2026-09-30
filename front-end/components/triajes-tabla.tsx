import Link from "next/link";
import type { Triaje } from "@/lib/api";
import { Confianza } from "@/components/confianza";
import { EstadoBadge } from "@/components/estado-badge";
import { PrioridadBadge } from "@/components/prioridad-badge";

function formatearFecha(iso: string) {
  return new Date(iso).toLocaleString("es", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "UTC",
  });
}

export function TriajesTabla({ triajes }: { triajes: Triaje[] }) {
  if (triajes.length === 0) {
    return <p className="text-sm text-muted-foreground">No hay documentos.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-xl ring-1 ring-foreground/10">
      <table className="w-full text-left text-sm">
        <thead className="bg-muted text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-medium">Documento</th>
            <th className="px-3 py-2 font-medium">Paciente</th>
            <th className="px-3 py-2 font-medium">Tipo</th>
            <th className="px-3 py-2 font-medium">Prioridad</th>
            <th className="px-3 py-2 font-medium">Confianza</th>
            <th className="px-3 py-2 font-medium">Estado</th>
            <th className="px-3 py-2 font-medium">Fecha (UTC)</th>
          </tr>
        </thead>
        <tbody>
          {triajes.map((t) => (
            <tr key={t.documento_id} className="border-t hover:bg-muted/50">
              <td className="px-3 py-2">
                <Link href={`/triaje/${t.documento_id}`} className="font-medium whitespace-nowrap underline-offset-4 hover:underline">
                  {t.documento_id}
                </Link>
              </td>
              <td className="px-3 py-2">{t.datos_extraidos.paciente.nombre}</td>
              <td className="px-3 py-2">{t.clasificacion.tipo_documento}</td>
              <td className="px-3 py-2">
                <PrioridadBadge nivel={t.clasificacion.nivel_prioridad} />
              </td>
              <td className="px-3 py-2">
                <Confianza
                  valor={t.clasificacion.score_confianza_clasificacion}
                  enRiesgo={t.decision_enrutamiento.requiere_auditoria_humana}
                />
              </td>
              <td className="px-3 py-2">
                <EstadoBadge estado={t.estado} />
              </td>
              <td className="px-3 py-2">{formatearFecha(t.timestamp)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
