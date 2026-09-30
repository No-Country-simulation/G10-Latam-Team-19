import Link from "next/link";
import { ArrowRight, BellRing, FileText, Gauge, ShieldAlert, Siren } from "lucide-react";
import { listarTriajes } from "@/lib/api";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PrioridadBadge } from "@/components/prioridad-badge";
import { TriajesTabla } from "@/components/triajes-tabla";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function Home() {
  const triajes = await listarTriajes();
  const urgentes = triajes.filter((t) => t.clasificacion.nivel_prioridad === "Urgente");
  const enAuditoria = triajes.filter((t) => t.estado === "auditoria_humana");
  const confianzaMedia =
    triajes.length === 0
      ? 0
      : Math.round(
          (triajes.reduce((acc, t) => acc + t.clasificacion.score_confianza_clasificacion, 0) /
            triajes.length) *
            100,
        );

  const resumen = [
    { etiqueta: "Documentos procesados", valor: triajes.length, icono: FileText },
    { etiqueta: "Urgentes", valor: urgentes.length, icono: Siren },
    { etiqueta: "Pendientes de auditoría", valor: enAuditoria.length, icono: ShieldAlert },
    { etiqueta: "Confianza media", valor: `${confianzaMedia}%`, icono: Gauge },
  ];

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 space-y-8 px-4 py-10">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">MediFlow</h1>
          <p className="max-w-xl text-muted-foreground">
            Triaje y enrutamiento inteligente de documentos clínicos. Revisa lo que el agente
            procesó y resuelve los casos que necesitan una persona.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/auditoria" className={cn(buttonVariants({ size: "lg" }))}>
            Ir a auditoría
            <ArrowRight data-icon="inline-end" />
          </Link>
          <Link href="/historial" className={cn(buttonVariants({ variant: "outline", size: "lg" }))}>
            Ver historial
          </Link>
        </div>
      </section>

      {urgentes.length > 0 && (
        <Card className="ring-destructive/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <BellRing className="size-4" />
              Alertas urgentes
            </CardTitle>
            <CardDescription>Casos que el agente derivó a atención inmediata.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="divide-y">
              {urgentes.map((t) => (
                <li key={t.documento_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <div className="space-y-0.5">
                    <Link
                      href={`/triaje/${t.documento_id}`}
                      className="text-sm font-medium underline-offset-4 hover:underline"
                    >
                      {t.datos_extraidos.diagnostico_principal ?? t.clasificacion.tipo_documento}
                    </Link>
                    <p className="text-sm text-muted-foreground">
                      {t.decision_enrutamiento.notificacion_generada?.mensaje ??
                        t.decision_enrutamiento.justificacion_enrutamiento}
                    </p>
                  </div>
                  <PrioridadBadge nivel={t.clasificacion.nivel_prioridad} />
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {resumen.map(({ etiqueta, valor, icono: Icono }) => (
          <Card key={etiqueta}>
            <CardHeader>
              <CardDescription className="flex items-center gap-2">
                <Icono className="size-4" />
                {etiqueta}
              </CardDescription>
              <CardTitle className="text-3xl font-semibold tabular-nums">{valor}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">Últimos documentos</h2>
          <Link href="/historial" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
            Ver todos
          </Link>
        </div>
        <TriajesTabla triajes={triajes.slice(0, 5)} />
      </section>
    </main>
  );
}
