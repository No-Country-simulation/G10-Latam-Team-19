import type { DestinoEnrutamiento } from "@/types/triage";

const FECHA = new Intl.DateTimeFormat("es", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "UTC",
});

/** Fecha y hora en UTC; devuelve "—" si el backend manda algo que no es una fecha. */
export function formatearFecha(iso: string): string {
  const fecha = new Date(iso);
  return Number.isNaN(fecha.getTime()) ? "—" : FECHA.format(fecha);
}

const DESTINOS: Record<DestinoEnrutamiento, string> = {
  Cola_Emergencia_Medica: "Cola de Emergencia Médica",
  Auditoria_Autorizaciones: "Auditoría de Autorizaciones",
  Farmacia_Hospitalaria: "Farmacia Hospitalaria",
  Cola_Revision_Humana: "Cola de Revisión Humana",
  Historia_Clinica_Electronica: "Historia Clínica Electrónica",
};

/** Nombre legible del destino; si el backend agrega uno nuevo, se muestra sin guiones bajos. */
export function etiquetaDestino(destino: string): string {
  return DESTINOS[destino as DestinoEnrutamiento] ?? destino.replaceAll("_", " ");
}
