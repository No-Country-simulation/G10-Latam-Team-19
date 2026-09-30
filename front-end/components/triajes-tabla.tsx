import Link from "next/link";
import type { Triaje } from "@/lib/api";

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
    <div className="overflow-x-auto rounded-lg border">
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
            <tr key={t.documento_id} className="border-t">
              <td className="px-3 py-2">
                <Link href={`/triaje/${t.documento_id}`} className="font-medium underline-offset-4 hover:underline">
                  {t.documento_id}
                </Link>
              </td>
              <td className="px-3 py-2">{t.datos_extraidos.paciente.nombre}</td>
              <td className="px-3 py-2">{t.clasificacion.tipo_documento}</td>
              <td className="px-3 py-2">{t.clasificacion.nivel_prioridad}</td>
              <td className="px-3 py-2">
                {Math.round(t.clasificacion.score_confianza_clasificacion * 100)}%
              </td>
              <td className="px-3 py-2">{t.estado}</td>
              <td className="px-3 py-2">{formatearFecha(t.timestamp)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
