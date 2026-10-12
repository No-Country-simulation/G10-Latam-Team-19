import Link from "next/link";
import { ArrowRight, ShieldAlert, Siren } from "lucide-react";
import { listarTriajes } from "@/lib/api";
import { etiquetaDestino } from "@/lib/formato";
import { resumirTriajes } from "@/lib/triajes/consultas";
import { PasosProcesamiento } from "@/components/pasos-procesamiento";
import { PrioridadBadge } from "@/components/prioridad-badge";

const CONTENEDOR = "relative flex h-full min-h-[640px] flex-col justify-between gap-6 p-5";

/** Datos del panel derecho de la carga. Va en Suspense para no frenar el formulario. */
export async function PanelResumen() {
  const triajes = await listarTriajes();
  const resumen = resumirTriajes(triajes);
  const urgente = triajes.find((t) => t.clasificacion.nivel_prioridad === "Urgente");
  const recientes = triajes.slice(0, 3);

  return (
    <div className={CONTENEDOR}>
      <div className="grid w-44 gap-3">
        <Link
          href="/auditoria"
          className="space-y-1 rounded-2xl bg-card/90 p-4 shadow-sm backdrop-blur transition-shadow hover:shadow-md"
        >
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <ShieldAlert className="size-3.5" />
            Pendientes de auditoría
          </p>
          <p className="text-3xl font-bold tabular-nums">{resumen.pendientesAuditoria}</p>
          <p className="flex items-center gap-1 text-sm font-medium text-primary">
            Revisar ahora
            <ArrowRight className="size-3.5" />
          </p>
        </Link>
        <Link
          href={urgente ? `/triaje/${urgente.documento_id}` : "/historial"}
          className="space-y-1 rounded-2xl bg-card/90 p-4 shadow-sm backdrop-blur transition-shadow hover:shadow-md"
        >
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <Siren className="size-3.5" />
            Urgentes
          </p>
          <p className="text-3xl font-bold tabular-nums">{resumen.urgentes}</p>
        </Link>
      </div>

      <div className="space-y-3 rounded-2xl bg-card/85 p-4 shadow-sm backdrop-blur-md">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">
            {recientes.length === 0 ? "Así procesa MediFlow" : "Últimos procesados"}
          </h2>
          {recientes.length > 0 && (
            <Link href="/dashboard" className="text-xs text-primary hover:underline">
              Ver dashboard
            </Link>
          )}
        </div>
        {recientes.length === 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Todavía no hay documentos. Así procesa MediFlow el primero:
            </p>
            <PasosProcesamiento />
          </div>
        ) : (
          <ul className="divide-y">
            {recientes.map((t) => (
              <li key={t.documento_id}>
                <Link
                  href={`/triaje/${t.documento_id}`}
                  className="flex items-center justify-between gap-3 py-2 text-sm"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">
                      {t.datos_extraidos.diagnostico_principal ?? t.clasificacion.tipo_documento}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {etiquetaDestino(t.decision_enrutamiento.destino_principal)}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <PrioridadBadge nivel={t.clasificacion.nivel_prioridad} />
                    <span className="text-xs tabular-nums text-muted-foreground">
                      {Math.round(t.clasificacion.score_confianza_clasificacion * 100)}%
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function PanelResumenCargando() {
  return (
    <div aria-busy="true" aria-label="Cargando resumen" className={CONTENEDOR}>
      <div className="grid w-44 gap-3">
        <div className="h-28 animate-pulse rounded-2xl bg-card/80" />
        <div className="h-20 animate-pulse rounded-2xl bg-card/80" />
      </div>
      <div className="h-48 animate-pulse rounded-2xl bg-card/80" />
    </div>
  );
}
