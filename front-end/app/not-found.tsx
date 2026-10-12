import Link from "next/link";
import { ArrowRight, FileSearch } from "lucide-react";

export default function NotFound() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 items-center justify-center px-4 pb-16 pt-6">
      <section className="w-full max-w-xl space-y-6 rounded-3xl bg-card p-8 text-center shadow-sm ring-1 ring-foreground/5 sm:p-12">
        <span className="mx-auto grid size-16 place-items-center rounded-2xl bg-secondary text-primary">
          <FileSearch className="size-8" />
        </span>
        <div className="space-y-3">
          <span className="inline-block rounded-full border bg-card px-3 py-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Error 404
          </span>
          <h1 className="text-4xl font-bold tracking-tight">
            No encontramos <span className="text-primary">esa página.</span>
          </h1>
          <p className="mx-auto max-w-md text-muted-foreground">
            El enlace puede estar mal escrito o el documento ya no existe. Vuelve a cargar un
            documento o revisa el historial.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/"
            className="inline-flex h-11 items-center gap-2 rounded-xl bg-foreground px-5 text-sm font-medium text-background"
          >
            Ir a Cargar
            <ArrowRight className="size-4" />
          </Link>
          <Link
            href="/historial"
            className="inline-flex h-11 items-center rounded-xl border bg-card px-5 text-sm font-medium hover:bg-muted"
          >
            Ver historial
          </Link>
        </div>
      </section>
    </main>
  );
}
