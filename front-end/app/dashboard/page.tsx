import Link from "next/link";
import { Bot, FileText, Gauge, UserCheck } from "lucide-react";
import { listarTriajes } from "@/lib/api";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ETIQUETA_ESTADO, etiquetaDestino } from "@/lib/formato";
import {
  contarPor,
  estadoVisible,
  porcentaje,
  resumirTriajes,
  type EstadoVisible,
} from "@/lib/triajes/consultas";
import { cn } from "@/lib/utils";
import { NIVELES_PRIORIDAD } from "@/types/triage";

export const dynamic = "force-dynamic";


const COLOR_PRIORIDAD: Record<string, string> = {
  Urgente: "bg-destructive",
  Prioritario: "bg-primary",
  Rutina: "bg-chart-3",
};

interface Item {
  etiqueta: string;
  cantidad: number;
  color?: string;
}

function Distribucion({ titulo, items, total }: { titulo: string; items: Item[]; total: number }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{titulo}</CardTitle>
      </CardHeader>
      <div className="space-y-3 px-4 pb-4">
        {items.map(({ etiqueta, cantidad, color }) => {
          const pct = porcentaje(cantidad, total);
          return (
            <div key={etiqueta} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>{etiqueta}</span>
                <span className="tabular-nums text-muted-foreground">
                  {cantidad} · {pct}%
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className={cn("h-full rounded-full", color ?? "bg-primary")}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export default async function DashboardPage() {
  const triajes = await listarTriajes();
  const r = resumirTriajes(triajes);
  const total = r.total;

  const resumen = [
    { etiqueta: "Documentos procesados", valor: total, icono: FileText },
    { etiqueta: "Resueltos por el agente", valor: `${r.pctResueltosPorAgente}%`, icono: Bot },
    { etiqueta: "Requirieron intervención humana", valor: `${r.pctConIntervencion}%`, icono: UserCheck },
    { etiqueta: "Confianza media", valor: `${r.confianzaMedia}%`, icono: Gauge },
  ];

  const porPrioridad = contarPor(triajes, (t) => t.clasificacion.nivel_prioridad);
  const porDestino = contarPor(triajes, (t) => t.decision_enrutamiento.destino_principal);
  const porEstado = contarPor(triajes, estadoVisible);

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 space-y-8 px-4 pb-12 pt-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Cuánto resuelve el agente por sí solo y cómo se reparten los documentos.
        </p>
      </div>

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

      {total === 0 ? (
        <p className="rounded-2xl bg-card p-6 text-sm text-muted-foreground ring-1 ring-foreground/5">
          Aún no hay documentos.{" "}
          <Link href="/" className="text-primary underline-offset-4 hover:underline">
            Carga el primero
          </Link>
          .
        </p>
      ) : (
        <section className="grid gap-4 lg:grid-cols-3">
          <Distribucion
            titulo="Por prioridad"
            total={total}
            items={NIVELES_PRIORIDAD.map((n) => ({
              etiqueta: n,
              cantidad: porPrioridad.get(n) ?? 0,
              color: COLOR_PRIORIDAD[n],
            }))}
          />
          <Distribucion
            titulo="Por estado"
            total={total}
            items={(Object.keys(ETIQUETA_ESTADO) as EstadoVisible[]).map((e) => ({
              etiqueta: ETIQUETA_ESTADO[e],
              cantidad: porEstado.get(e) ?? 0,
            }))}
          />
          <Distribucion
            titulo="Por destino"
            total={total}
            items={[...porDestino.entries()]
              .sort((a, b) => b[1] - a[1])
              .map(([destino, cantidad]) => ({
                etiqueta: etiquetaDestino(destino),
                cantidad,
              }))}
          />
        </section>
      )}

      <p className="text-sm text-muted-foreground">
        ¿Buscas un caso puntual?{" "}
        <Link href="/historial" className="text-primary underline-offset-4 hover:underline">
          Ver el historial completo
        </Link>
        .
      </p>
    </main>
  );
}
