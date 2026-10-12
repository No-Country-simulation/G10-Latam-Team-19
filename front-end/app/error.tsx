"use client";

import { useEffect } from "react";
import Link from "next/link";
import { RotateCw, ServerCrash } from "lucide-react";

export default function ErrorPage({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    // El digest permite ubicar el error en los logs del servidor sin exponer su detalle.
    console.error("Error de MediFlow:", error.digest ?? error.message);
  }, [error]);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 items-center justify-center px-4 pb-16 pt-6">
      <section className="w-full max-w-xl space-y-6 rounded-3xl bg-card p-8 text-center shadow-sm ring-1 ring-foreground/5 sm:p-12">
        <span className="mx-auto grid size-16 place-items-center rounded-2xl bg-destructive/10 text-destructive">
          <ServerCrash className="size-8" />
        </span>
        <div className="space-y-3">
          <h1 className="text-3xl font-bold tracking-tight">No pudimos conectar con MediFlow.</h1>
          <p className="mx-auto max-w-md text-muted-foreground">
            El servicio de triaje no respondió. Tus datos no se modificaron. Probá de nuevo en unos
            segundos.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => retry()}
            className="inline-flex h-11 items-center gap-2 rounded-xl bg-foreground px-5 text-sm font-medium text-background"
          >
            <RotateCw className="size-4" />
            Reintentar
          </button>
          <Link
            href="/faq"
            className="inline-flex h-11 items-center rounded-xl border bg-card px-5 text-sm font-medium hover:bg-muted"
          >
            Ver ayuda
          </Link>
        </div>
      </section>
    </main>
  );
}
