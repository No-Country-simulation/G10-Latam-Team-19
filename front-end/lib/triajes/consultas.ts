import type { EstadoDocumento } from "@/types/triage";
import type { Triaje } from "./tipos";

/** Estado que ve el usuario: agrega "rechazados", que en el backend sigue en auditoria_humana. */
export type EstadoVisible = EstadoDocumento | "rechazados";

export function estadoVisible(t: Pick<Triaje, "estado" | "decision_auditoria">): EstadoVisible {
  return t.estado === "auditoria_humana" && t.decision_auditoria === "rechazado" ? "rechazados" : t.estado;
}

/** Casos que esperan una decisión humana (los rechazados ya fueron resueltos). */
export function filtrarPendientesAuditoria(triajes: Triaje[]): Triaje[] {
  return triajes.filter(
    (t) => t.estado === "auditoria_humana" && t.decision_auditoria !== "rechazado",
  );
}

/** Búsqueda sin distinguir mayúsculas por ID, paciente o tipo de documento. */
export function buscarTriajes(triajes: Triaje[], consulta: string): Triaje[] {
  const q = consulta.trim().toLowerCase();
  if (!q) return triajes;
  return triajes.filter((t) =>
    [t.documento_id, t.datos_extraidos.paciente.nombre, t.clasificacion.tipo_documento]
      .join(" ")
      .toLowerCase()
      .includes(q),
  );
}

export function contarPor<T>(items: T[], clave: (item: T) => string): Map<string, number> {
  const conteo = new Map<string, number>();
  for (const item of items) {
    const k = clave(item);
    conteo.set(k, (conteo.get(k) ?? 0) + 1);
  }
  return conteo;
}

/** Porcentaje entero de `parte` sobre `total`; 0 si no hay total. */
export function porcentaje(parte: number, total: number): number {
  return total === 0 ? 0 : Math.round((parte / total) * 100);
}

export interface ResumenTriajes {
  total: number;
  urgentes: number;
  pendientesAuditoria: number;
  /** % de documentos que el agente enrutó sin pedir auditoría humana. */
  pctResueltosPorAgente: number;
  pctConIntervencion: number;
  /** Confianza media de la clasificación, de 0 a 100. */
  confianzaMedia: number;
}

export function resumirTriajes(triajes: Triaje[]): ResumenTriajes {
  const total = triajes.length;
  const conIntervencion = triajes.filter(
    (t) => t.estado === "auditoria_humana" || t.decision_auditoria !== null,
  ).length;
  const sumaConfianza = triajes.reduce(
    (acc, t) => acc + t.clasificacion.score_confianza_clasificacion,
    0,
  );

  return {
    total,
    urgentes: triajes.filter((t) => t.clasificacion.nivel_prioridad === "Urgente").length,
    pendientesAuditoria: filtrarPendientesAuditoria(triajes).length,
    pctResueltosPorAgente: porcentaje(total - conIntervencion, total),
    pctConIntervencion: porcentaje(conIntervencion, total),
    confianzaMedia: total === 0 ? 0 : Math.round((sumaConfianza / total) * 100),
  };
}
