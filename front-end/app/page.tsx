import Link from "next/link";
import { listarTriajes } from "@/lib/api";
import { TriajesTabla } from "@/components/triajes-tabla";

export const dynamic = "force-dynamic";

export default async function Home() {
  const triajes = await listarTriajes();
  const urgentes = triajes.filter((t) => t.clasificacion.nivel_prioridad === "Urgente");
  const enAuditoria = triajes.filter((t) => t.estado === "auditoria_humana");

  const resumen = [
    { etiqueta: "Documentos procesados", valor: triajes.length },
    { etiqueta: "Urgentes", valor: urgentes.length },
    { etiqueta: "Pendientes de auditoría", valor: enAuditoria.length },
  ];

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 space-y-8 px-4 py-8">
      <section className="space-y-2">
        <h1 className="text-2xl font-semibold">MediFlow</h1>
        <p className="text-muted-foreground">
          Triaje y enrutamiento inteligente de documentos clínicos.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {resumen.map(({ etiqueta, valor }) => (
          <div key={etiqueta} className="rounded-lg border p-4">
            <p className="text-sm text-muted-foreground">{etiqueta}</p>
            <p className="text-3xl font-semibold">{valor}</p>
          </div>
        ))}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">Últimos documentos</h2>
          <Link href="/historial" className="text-sm underline-offset-4 hover:underline">
            Ver historial
          </Link>
        </div>
        <TriajesTabla triajes={triajes.slice(0, 5)} />
      </section>
    </main>
  );
}
