import Link from "next/link";
import { notFound } from "next/navigation";
import { Activity, ArrowLeft, Pill, Route, ShieldAlert, UserCheck } from "lucide-react";
import { obtenerTriaje } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { EstadoBadge } from "@/components/estado-badge";
import { PrioridadBadge } from "@/components/prioridad-badge";
import { etiquetaDestino, formatearFecha } from "@/lib/formato";
import { cn } from "@/lib/utils";
import { esIdDocumento } from "@/lib/validacion";

export const dynamic = "force-dynamic";

function Panel({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <section className={cn("rounded-2xl bg-card p-5 shadow-sm ring-1 ring-foreground/5", className)}>
      {children}
    </section>
  );
}

function Fila({ letra, etiqueta, valor }: { letra: string; etiqueta: string; valor: string | null }) {
  return (
    <div className="flex items-center gap-3 border-b py-3 last:border-b-0">
      <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-secondary text-xs font-semibold text-secondary-foreground">
        {letra}
      </span>
      <dt className="w-40 shrink-0 text-sm text-muted-foreground">{etiqueta}</dt>
      <dd className="flex-1 text-right text-sm font-medium">{valor ?? "—"}</dd>
    </div>
  );
}

export default async function TriajePage({ params }: PageProps<"/triaje/[id]">) {
  const { id } = await params;
  if (!esIdDocumento(id)) notFound();
  const t = await obtenerTriaje(id);
  if (!t) notFound();

  const { clasificacion, datos_extraidos: d, decision_enrutamiento: dec } = t;
  const { paciente, signos_vitales: sv } = d;
  const requiereAuditoria = dec.requiere_auditoria_humana;
  const urgente = clasificacion.nivel_prioridad === "Urgente";

  const edad =
    paciente.edad === null ? null : `${paciente.edad} ${paciente.unidad_edad ?? ""}`.trim();
  const medico = d.medico_solicitante
    ? `${d.medico_solicitante.nombre}${d.medico_solicitante.matricula ? ` · MP ${d.medico_solicitante.matricula}` : ""}`
    : null;

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 space-y-5 px-4 pb-12 pt-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <Link href="/historial" className="inline-flex items-center gap-1 text-primary hover:underline">
            <ArrowLeft className="size-3.5" />
            Historial
          </Link>
          <span>/</span>
          <span>
            {t.documento_id} · {t.canal_origen} · {formatearFecha(t.timestamp)} UTC
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PrioridadBadge nivel={clasificacion.nivel_prioridad} />
          <EstadoBadge estado={t.estado} />
          {t.decision_auditoria && (
            <Badge variant={t.decision_auditoria === "rechazado" ? "destructive" : "secondary"}>
              {t.decision_auditoria === "rechazado" ? "Rechazado" : "Aprobado"}
            </Badge>
          )}
        </div>
      </div>

      {urgente && (
        <div className="flex items-start gap-4 rounded-2xl border border-destructive/30 bg-destructive/5 p-5">
          <span className="grid size-12 shrink-0 place-items-center rounded-full bg-destructive text-white">
            <ShieldAlert className="size-6" />
          </span>
          <div className="space-y-1">
            <p className="flex flex-wrap items-center gap-2 text-xl font-semibold">
              <Badge className="bg-destructive text-white">URGENTE</Badge>
              Derivado a {etiquetaDestino(dec.destino_principal)}
            </p>
            <p className="text-sm text-destructive">{dec.justificacion_enrutamiento}</p>
          </div>
        </div>
      )}

      {requiereAuditoria && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-secondary/60 p-5">
          <div className="flex items-start gap-3">
            <UserCheck className="mt-0.5 size-5 text-primary" />
            <div>
              <p className="font-semibold">Requiere auditoría humana</p>
              {!urgente && (
                <p className="text-sm text-muted-foreground">{dec.justificacion_enrutamiento}</p>
              )}
            </div>
          </div>
          <Link href="/auditoria" className="text-sm font-medium text-primary underline-offset-4 hover:underline">
            Ir a la cola de auditoría
          </Link>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-[2fr_1fr]">
        <Panel>
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Tipo de documento
          </p>
          <p className="mt-1 text-xl font-semibold">{clasificacion.tipo_documento}</p>
          <p className="text-sm text-muted-foreground">{clasificacion.especialidad}</p>
        </Panel>
        <Panel>
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Confianza
          </p>
          <p className="mt-1 text-3xl font-bold tabular-nums">
            {Math.round(clasificacion.score_confianza_clasificacion * 100)}%
          </p>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className={cn("h-full rounded-full", requiereAuditoria ? "bg-destructive" : "bg-primary")}
              style={{ width: `${Math.round(clasificacion.score_confianza_clasificacion * 100)}%` }}
            />
          </div>
        </Panel>
      </div>

      <Panel>
        <h2 className="font-semibold">Datos extraídos</h2>
        <dl className="mt-2">
          <Fila letra="P" etiqueta="Paciente" valor={[paciente.nombre, edad].filter(Boolean).join(" · ") || null} />
          <Fila letra="S" etiqueta="Sexo / Documento" valor={[paciente.sexo, paciente.documento_identidad].filter(Boolean).join(" · ") || null} />
          <Fila letra="M" etiqueta="Médico solicitante" valor={medico} />
          <Fila letra="E" etiqueta="Estudio" valor={d.estudio_realizado} />
          <Fila letra="D" etiqueta="Diagnóstico principal" valor={d.diagnostico_principal} />
          <Fila letra="C" etiqueta="CIE-10 sugerido" valor={d.cie10_sugerido} />
        </dl>
      </Panel>

      {d.medicamentos && d.medicamentos.length > 0 && (
        <Panel>
          <h2 className="flex items-center gap-2 font-semibold">
            <Pill className="size-4 text-muted-foreground" />
            Medicamentos
          </h2>
          <ul className="mt-3 space-y-1 text-sm">
            {d.medicamentos.map((m, i) => (
              <li key={`${i}-${m.nombre}`}>
                <span className="font-medium">{m.nombre}</span>
                {m.dosis && ` · ${m.dosis}`}
                {m.frecuencia_diaria && ` · ${m.frecuencia_diaria}`}
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {sv && (
        <Panel>
          <h2 className="flex items-center gap-2 font-semibold">
            <Activity className="size-4 text-muted-foreground" />
            Signos vitales
          </h2>
          <dl className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-5">
            {[
              ["Temperatura (°C)", sv.temperatura],
              ["FC (lpm)", sv.frecuencia_cardiaca],
              ["FR (rpm)", sv.frecuencia_respiratoria],
              ["Presión arterial", sv.presion_arterial],
              ["SpO2 (%)", sv.saturacion_oxigeno],
            ].map(([etiqueta, valor]) => (
              <div key={etiqueta} className="space-y-0.5">
                <dt className="text-xs text-muted-foreground">{etiqueta}</dt>
                <dd className="text-sm font-medium">{valor ?? "—"}</dd>
              </div>
            ))}
          </dl>
        </Panel>
      )}

      <Panel>
        <h2 className="flex items-center gap-2 font-semibold">
          <Route className="size-4 text-muted-foreground" />
          Enrutamiento
        </h2>
        <p className="mt-2 text-sm">
          <span className="text-muted-foreground">Destino: </span>
          <span className="font-medium">{etiquetaDestino(dec.destino_principal)}</span>
        </p>
        <p className="mt-2 text-sm text-muted-foreground">{dec.justificacion_enrutamiento}</p>
        {t.almacenamiento_oci?.ruta_objeto && (
          <p className="mt-3 border-t pt-3 font-mono text-xs text-muted-foreground">
            Guardado en OCI · {t.almacenamiento_oci.ruta_objeto}
          </p>
        )}
      </Panel>
    </main>
  );
}
