import Link from "next/link";
import { listarAuditoria } from "@/lib/api";
import { resolver } from "./actions";

export const dynamic = "force-dynamic";

export default async function AuditoriaPage() {
  const pendientes = await listarAuditoria();

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 space-y-4 px-4 py-8">
      <h1 className="text-2xl font-semibold">Auditoría humana</h1>
      <p className="text-muted-foreground">
        Documentos con baja confianza o datos faltantes que requieren revisión.
      </p>

      {pendientes.length === 0 && (
        <p className="text-sm text-muted-foreground">No hay documentos pendientes.</p>
      )}

      <ul className="space-y-3">
        {pendientes.map((t) => (
          <li key={t.documento_id} className="space-y-3 rounded-lg border p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <Link
                href={`/triaje/${t.documento_id}`}
                className="font-medium underline-offset-4 hover:underline"
              >
                {t.documento_id}
              </Link>
              <span className="text-sm text-muted-foreground">
                Confianza {Math.round(t.clasificacion.score_confianza_clasificacion * 100)}%
              </span>
            </div>
            <p className="text-sm">{t.decision_enrutamiento.justificacion_enrutamiento}</p>
            {t.decision_auditoria === "rechazado" ? (
              <p className="text-sm font-medium text-destructive">Rechazado</p>
            ) : (
              <div className="flex gap-2">
                <form action={resolver.bind(null, t.documento_id, "aprobado")}>
                  <button type="submit" className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground">
                    Aprobar
                  </button>
                </form>
                <form action={resolver.bind(null, t.documento_id, "rechazado")}>
                  <button type="submit" className="rounded-md border px-3 py-1.5 text-sm">
                    Rechazar
                  </button>
                </form>
              </div>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
