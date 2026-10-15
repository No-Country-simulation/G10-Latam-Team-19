import Link from "next/link";
import { listarAuditoria } from "@/lib/api";
import { BotonesAuditoria } from "@/components/botones-auditoria";
import { Confianza } from "@/components/confianza";
import { PrioridadBadge } from "@/components/prioridad-badge";

export const dynamic = "force-dynamic";

export default async function AuditoriaPage() {
  const pendientes = await listarAuditoria();

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 space-y-4 px-4 pb-12 pt-6">
      <h1 className="text-3xl font-bold tracking-tight">Auditoría humana</h1>
      <p className="text-muted-foreground">
        Documentos con baja confianza o datos faltantes que requieren revisión.
      </p>

      {pendientes.length === 0 && (
        <p className="rounded-2xl bg-card p-6 text-sm text-muted-foreground ring-1 ring-foreground/5">
          No hay documentos pendientes.
        </p>
      )}

      <ul className="space-y-3">
        {pendientes.map((t) => (
          <li
            key={t.documento_id}
            className="space-y-3 rounded-2xl bg-card p-5 shadow-sm ring-1 ring-foreground/5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  href={`/triaje/${t.documento_id}`}
                  className="font-semibold underline-offset-4 hover:underline"
                >
                  {t.documento_id}
                </Link>
                <PrioridadBadge nivel={t.clasificacion.nivel_prioridad} />
              </div>
              <Confianza valor={t.clasificacion.score_confianza_clasificacion} enRiesgo />
            </div>
            <p className="text-sm text-muted-foreground">
              {t.clasificacion.tipo_documento} · {t.datos_extraidos.paciente.nombre}
            </p>
            <p className="text-sm">{t.decision_enrutamiento.justificacion_enrutamiento}</p>
            <BotonesAuditoria id={t.documento_id} />
          </li>
        ))}
      </ul>
    </main>
  );
}
