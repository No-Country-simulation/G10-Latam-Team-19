import type { TriageResponse } from "@/types/triage";

/** Respuesta mínima válida del backend para las pruebas. */
export function triageDePrueba(cambios: Partial<TriageResponse> = {}): TriageResponse {
  return {
    status: "procesado",
    documento_id: "DOC-TEST-1",
    timestamp: "2026-10-01T10:00:00Z",
    canal_origen: "Laboratorio",
    clasificacion: {
      tipo_documento: "Receta Medica",
      especialidad: "Clínica Médica",
      nivel_prioridad: "Rutina",
      score_confianza_clasificacion: 0.9,
    },
    datos_extraidos: {
      paciente: {
        nombre: "Ana Pérez",
        edad: 40,
        unidad_edad: "años",
        sexo: "F",
        documento_identidad: null,
      },
      medico_solicitante: null,
      estudio_realizado: null,
      diagnostico_principal: null,
      cie10_sugerido: null,
      medicamentos: null,
      signos_vitales: null,
    },
    decision_enrutamiento: {
      destino_principal: "Farmacia_Hospitalaria",
      requiere_auditoria_humana: false,
      justificacion_enrutamiento: "Receta estándar.",
      notificacion_generada: null,
    },
    almacenamiento_oci: null,
    ...cambios,
  };
}

export function conAuditoria(cambios: Partial<TriageResponse> = {}): TriageResponse {
  const base = triageDePrueba(cambios);
  return {
    ...base,
    decision_enrutamiento: { ...base.decision_enrutamiento, requiere_auditoria_humana: true },
  };
}
