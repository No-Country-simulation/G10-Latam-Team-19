import { Suspense } from "react";
import Image from "next/image";
import { CargarDocumento } from "@/components/cargar-documento";
import { PanelResumen, PanelResumenCargando } from "@/components/panel-resumen";

export const dynamic = "force-dynamic";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 space-y-8 px-4 pb-16 pt-6">
      <section className="grid items-start gap-8 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          <span className="inline-block rounded-full border bg-card px-3 py-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Triaje clínico con IA
          </span>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Cargá un documento.
            <br />
            <span className="text-primary">Nosotros lo derivamos.</span>
          </h1>
          <p className="max-w-xl text-muted-foreground">
            Recetas, informes, órdenes o epicrisis. MediFlow lo clasifica, extrae los datos y lo
            envía al área correcta.
          </p>
          <CargarDocumento />
        </div>

        <aside className="relative min-h-[640px] overflow-hidden rounded-3xl bg-secondary ring-1 ring-foreground/5">
          <Image
            src="/home.webp"
            alt=""
            fill
            priority
            unoptimized
            sizes="(min-width: 1024px) 40vw, 100vw"
            className="object-cover object-top"
          />
          <Suspense fallback={<PanelResumenCargando />}>
            <PanelResumen />
          </Suspense>
        </aside>
      </section>
    </main>
  );
}
