import Link from "next/link";
import { notFound } from "next/navigation";
import { obtenerTriaje } from "@/lib/api";

export const dynamic = "force-dynamic";

function Campo({ etiqueta, valor }: { etiqueta: string; valor: string | number | null }) {
  return (
    <div>
      <dt className="text-sm text-muted-foreground">{etiqueta}</dt>
      <dd>{valor ?? "—"}</dd>
    </div>
  );
}

export default async function TriajePage({ params }: PageProps<"/triaje/[id]">) {
  const { id } = await params;
  const t = await obtenerTriaje(id);
  if (!t) notFound();

  const { clasificacion, datos_extraidos: d, decision_enrutamiento: dec } = t;
  const { paciente, signos_vitales: sv } = d;

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 space-y-8 px-4 py-8">
      <div className="space-y-1">
        <Link href="/historial" className="text-sm text-muted-foreground hover:text-foreground">
          ← Historial
        </Link>
        <h1 className="text-2xl font-semibold">{t.documento_id}</h1>
        <p className="text-muted-foreground">
          {clasificacion.tipo_documento} · {t.canal_origen}
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Clasificación</h2>
        <dl className="grid gap-4 sm:grid-cols-3">
          <Campo etiqueta="Especialidad" valor={clasificacion.especialidad} />
          <Campo etiqueta="Prioridad" valor={clasificacion.nivel_prioridad} />
          <Campo
            etiqueta="Confianza"
            valor={`${Math.round(clasificacion.score_confianza_clasificacion * 100)}%`}
          />
        </dl>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Paciente</h2>
        <dl className="grid gap-4 sm:grid-cols-4">
          <Campo etiqueta="Nombre" valor={paciente.nombre} />
          <Campo
            etiqueta="Edad"
            valor={paciente.edad === null ? null : `${paciente.edad} ${paciente.unidad_edad ?? ""}`.trim()}
          />
          <Campo etiqueta="Sexo" valor={paciente.sexo} />
          <Campo etiqueta="Documento" valor={paciente.documento_identidad} />
        </dl>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Datos clínicos</h2>
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
        {d.medicamentos && (
          <ul className="list-disc pl-5 text-sm">
            {d.medicamentos.map((m) => (
              <li key={m.nombre}>
                {m.nombre}
                {m.dosis && ` · ${m.dosis}`}
                {m.frecuencia_diaria && ` · ${m.frecuencia_diaria}`}
              </li>
            ))}
          </ul>
        )}
      </section>

      {sv && (
        <section className="space-y-3">
          <h2 className="text-lg font-medium">Signos vitales</h2>
          <dl className="grid gap-4 sm:grid-cols-5">
            <Campo etiqueta="Temperatura (°C)" valor={sv.temperatura} />
            <Campo etiqueta="FC (lpm)" valor={sv.frecuencia_cardiaca} />
            <Campo etiqueta="FR (rpm)" valor={sv.frecuencia_respiratoria} />
            <Campo etiqueta="Presión arterial" valor={sv.presion_arterial} />
            <Campo etiqueta="SpO2 (%)" valor={sv.saturacion_oxigeno} />
          </dl>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Enrutamiento</h2>
        <dl className="grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Destino" valor={dec.destino_principal} />
          <Campo
            etiqueta="Auditoría humana"
            valor={dec.requiere_auditoria_humana ? "Requerida" : "No requerida"}
          />
          <Campo etiqueta="Estado" valor={t.estado} />
          <Campo etiqueta="Ruta en OCI" valor={t.almacenamiento_oci?.ruta_objeto ?? null} />
        </dl>
        <p className="text-sm">{dec.justificacion_enrutamiento}</p>
        {dec.notificacion_generada && (
          <p className="rounded-lg border p-3 text-sm">
            <span className="font-medium">{dec.notificacion_generada.canal}:</span>{" "}
            {dec.notificacion_generada.mensaje}
          </p>
        )}
      </section>
    </main>
  );
}
