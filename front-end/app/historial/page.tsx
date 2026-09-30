import { listarTriajes } from "@/lib/api";
import { TriajesTabla } from "@/components/triajes-tabla";

export const dynamic = "force-dynamic";

export default async function HistorialPage() {
  const triajes = await listarTriajes();

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 space-y-4 px-4 py-8">
      <h1 className="text-2xl font-semibold">Historial</h1>
      <p className="text-muted-foreground">Todos los documentos procesados por el agente.</p>
      <TriajesTabla triajes={triajes} />
    </main>
  );
}
