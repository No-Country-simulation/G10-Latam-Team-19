import Link from "next/link";
import { notFound } from "next/navigation";
import { Activity, ArrowLeft, BellRing, Pill, Route, Stethoscope, User } from "lucide-react";
import { obtenerTriaje } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Confianza } from "@/components/confianza";
import { EstadoBadge } from "@/components/estado-badge";
import { PrioridadBadge } from "@/components/prioridad-badge";

export const dynamic = "force-dynamic";

function Campo({ etiqueta, valor }: { etiqueta: string; valor: string | number | null }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{etiqueta}</dt>
      <dd className="text-sm">{valor ?? "—"}</dd>
    </div>
  );
}

function Seccion({
  titulo,
  icono: Icono,
  children,
}: {
  titulo: string;
  icono: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icono className="size-4 text-muted-foreground" />
          {titulo}
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export default async function TriajePage({ params }: PageProps<"/triaje/[id]">) {
  const { id } = await params;
  const t = await obtenerTriaje(id);
  if (!t) notFound();

  const { clasificacion, datos_extraidos: d, decision_enrutamiento: dec } = t;
  const { paciente, signos_vitales: sv } = d;
  const requiereAuditoria = dec.requiere_auditoria_humana;

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 space-y-6 px-4 py-10">
      <div className="space-y-3">
        <Link
          href="/historial"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Historial
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">{t.documento_id}</h1>
            <p className="text-muted-foreground">
              {clasificacion.tipo_documento} · {clasificacion.especialidad} · {t.canal_origen}
            </p>
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
      </div>

      {dec.notificacion_generada && (
        <Card className="ring-destructive/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <BellRing className="size-4" />
              {dec.notificacion_generada.canal}
            </CardTitle>
            <CardDescription className="text-foreground">
              {dec.notificacion_generada.mensaje}
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {requiereAuditoria && (
        <Card>
          <CardHeader>
            <CardTitle>Requiere auditoría humana</CardTitle>
            <CardDescription>{dec.justificacion_enrutamiento}</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/auditoria" className="text-sm underline underline-offset-4">
              Ir a la cola de auditoría
            </Link>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Seccion titulo="Paciente" icono={User}>
          <dl className="grid grid-cols-2 gap-4">
            <Campo etiqueta="Nombre" valor={paciente.nombre} />
            <Campo
              etiqueta="Edad"
              valor={paciente.edad === null ? null : `${paciente.edad} ${paciente.unidad_edad ?? ""}`.trim()}
            />
            <Campo etiqueta="Sexo" valor={paciente.sexo} />
            <Campo etiqueta="Documento" valor={paciente.documento_identidad} />
          </dl>
        </Seccion>

        <Seccion titulo="Clasificación" icono={Stethoscope}>
          <dl className="grid grid-cols-2 gap-4">
            <Campo etiqueta="Tipo de documento" valor={clasificacion.tipo_documento} />
            <Campo etiqueta="Especialidad" valor={clasificacion.especialidad} />
            <div className="col-span-2 space-y-1">
              <dt className="text-xs text-muted-foreground">Confianza de la clasificación</dt>
              <dd>
                <Confianza
                  valor={clasificacion.score_confianza_clasificacion}
                  enRiesgo={requiereAuditoria}
                />
              </dd>
            </div>
          </dl>
        </Seccion>
      </div>

      <Seccion titulo="Datos clínicos" icono={Pill}>
        <dl className="grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Diagnóstico principal" valor={d.diagnostico_principal} />
          <Campo etiqueta="CIE-10 sugerido" valor={d.cie10_sugerido} />
          <Campo etiqueta="Estudio realizado" valor={d.estudio_realizado} />
          <Campo
            etiqueta="Médico solicitante"
            valor={
              d.medico_solicitante
                ? `${d.medico_solicitante.nombre}${d.medico_solicitante.matricula ? ` (MP ${d.medico_solicitante.matricula})` : ""}`
                : null
            }
          />
        </dl>
        {d.medicamentos && d.medicamentos.length > 0 && (
          <div className="mt-4 space-y-2 border-t pt-4">
            <p className="text-xs text-muted-foreground">Medicamentos</p>
            <ul className="space-y-1 text-sm">
              {d.medicamentos.map((m) => (
                <li key={m.nombre}>
                  <span className="font-medium">{m.nombre}</span>
                  {m.dosis && ` · ${m.dosis}`}
                  {m.frecuencia_diaria && ` · ${m.frecuencia_diaria}`}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Seccion>

      {sv && (
        <Seccion titulo="Signos vitales" icono={Activity}>
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <Campo etiqueta="Temperatura (°C)" valor={sv.temperatura} />
            <Campo etiqueta="FC (lpm)" valor={sv.frecuencia_cardiaca} />
            <Campo etiqueta="FR (rpm)" valor={sv.frecuencia_respiratoria} />
            <Campo etiqueta="Presión arterial" valor={sv.presion_arterial} />
            <Campo etiqueta="SpO2 (%)" valor={sv.saturacion_oxigeno} />
          </dl>
        </Seccion>
      )}

      <Seccion titulo="Enrutamiento" icono={Route}>
        <dl className="grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Destino" valor={dec.destino_principal} />
          <Campo etiqueta="Ruta en OCI" valor={t.almacenamiento_oci?.ruta_objeto ?? null} />
        </dl>
        <p className="mt-4 border-t pt-4 text-sm text-muted-foreground">
          {dec.justificacion_enrutamiento}
        </p>
      </Seccion>
    </main>
  );
}
