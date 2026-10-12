import { listarTriajes } from "@/lib/api";
import { buscarTriajes } from "@/lib/triajes/consultas";
import { TriajesTabla } from "@/components/triajes-tabla";

export const dynamic = "force-dynamic";

export default async function HistorialPage({ searchParams }: PageProps<"/historial">) {
  const { q } = await searchParams;
  const consulta = (Array.isArray(q) ? q[0] : q)?.trim() ?? "";
  const triajes = buscarTriajes(await listarTriajes(), consulta);

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 space-y-4 px-4 pb-12 pt-6">
      <h1 className="text-3xl font-bold tracking-tight">Historial</h1>
      <p className="text-muted-foreground">
        {consulta
          ? `${triajes.length} resultado(s) para "${consulta}".`
          : "Todos los documentos procesados por el agente."}
      </p>
      <TriajesTabla triajes={triajes} />
    </main>
  );
}
