import type { TriageResponse } from "@/types/triage";

// Datos de prueba que cubren los 3 escenarios de la demo del hackathon:
// urgencia médica, flujo estándar (rutina) y caso ambiguo -> auditoría humana.
export const TRIAJES_MOCK: TriageResponse[] = [
  {
    // Escenario 1: urgencia médica
    status: "procesado",
    documento_id: "DOC-CLIN-2026-8942",
    timestamp: "2026-09-29T14:32:10Z",
    canal_origen: "Guardia_Emergencias",
    clasificacion: {
      tipo_documento: "Informe de Estudio",
      especialidad: "Radiología / Neumonología",
      nivel_prioridad: "Urgente",
      score_confianza_clasificacion: 0.99,
    },
    datos_extraidos: {
      paciente: {
        nombre: "Carlos Eduardo Mendes",
        edad: 52,
        unidad_edad: "años",
        sexo: "M",
        documento_identidad: "AB123456",
      },
      medico_solicitante: { nombre: "Dra. Renata Silveira", matricula: "145892" },
      estudio_realizado: "Tomografia de Torax con contraste",
      diagnostico_principal: "Tromboembolismo Pulmonar Agudo (TEP)",
      cie10_sugerido: "I26.9",
      medicamentos: [
        { nombre: "Enoxaparina", dosis: "80 mg", frecuencia_diaria: "2 veces al día" },
      ],
      signos_vitales: {
        temperatura: 37.5,
        frecuencia_cardiaca: 115,
        frecuencia_respiratoria: 28,
        presion_arterial: "140/90",
        saturacion_oxigeno: 88,
      },
    },
    decision_enrutamiento: {
      destino_principal: "Cola_Emergencia_Medica",
      requiere_auditoria_humana: false,
      justificacion_enrutamiento:
        "Hallazgo critico de alta gravedad (TEP agudo) y desaturación (88%).",
      notificacion_generada: {
        canal: "Alerta_Guardia_Medica",
        mensaje: "ALERTA URGENTE: TEP Agudo para Carlos Eduardo Mendes.",
      },
    },
    almacenamiento_oci: {
      bucket: "mediflow-documentos-clinicos",
      ruta_objeto: "procesados/urgentes/DOC-CLIN-2026-8942.json",
      status_backup: "exito",
    },
  },
  {
    // Escenario 2: flujo estándar (rutina)
    status: "procesado",
    documento_id: "DOC-CLIN-2026-8950",
    timestamp: "2026-09-29T15:05:41Z",
    canal_origen: "Consultorio_Externo",
    clasificacion: {
      tipo_documento: "Receta Medica",
      especialidad: "Clínica Médica",
      nivel_prioridad: "Rutina",
      score_confianza_clasificacion: 0.96,
    },
    datos_extraidos: {
      paciente: {
        nombre: "María Fernanda Ortiz",
        edad: 34,
        unidad_edad: "años",
        sexo: "F",
        documento_identidad: "CD789012",
      },
      medico_solicitante: { nombre: "Dr. Andrés Paredes", matricula: "203311" },
      estudio_realizado: null,
      diagnostico_principal: "Hipertensión arterial esencial",
      cie10_sugerido: "I10",
      medicamentos: [
        { nombre: "Losartán", dosis: "50 mg", frecuencia_diaria: "1 vez al día" },
      ],
      signos_vitales: null,
    },
    decision_enrutamiento: {
      destino_principal: "Farmacia_Hospitalaria",
      requiere_auditoria_humana: false,
      justificacion_enrutamiento:
        "Receta de medicación crónica sin interacciones ni datos faltantes.",
      notificacion_generada: null,
    },
    almacenamiento_oci: {
      bucket: "mediflow-documentos-clinicos",
      ruta_objeto: "procesados/DOC-CLIN-2026-8950.json",
      status_backup: "exito",
    },
  },
  {
    // Escenario 3: caso ambiguo -> auditoría humana
    status: "procesado",
    documento_id: "DOC-CLIN-2026-8957",
    timestamp: "2026-09-29T16:20:03Z",
    canal_origen: "Mesa_Entradas",
    clasificacion: {
      tipo_documento: "Desconocido",
      especialidad: "Sin determinar",
      nivel_prioridad: "Prioritario",
      score_confianza_clasificacion: 0.41,
    },
    datos_extraidos: {
      paciente: {
        nombre: "J. Ramírez (ilegible)",
        edad: null,
        unidad_edad: null,
        sexo: null,
        documento_identidad: null,
      },
      medico_solicitante: null,
      estudio_realizado: null,
      diagnostico_principal: null,
      cie10_sugerido: null,
      medicamentos: [{ nombre: "Posible amoxicilina", dosis: null, frecuencia_diaria: null }],
      signos_vitales: null,
    },
    decision_enrutamiento: {
      destino_principal: "Cola_Revision_Humana",
      requiere_auditoria_humana: true,
      justificacion_enrutamiento:
        "Texto ilegible, confianza baja (0.41) y datos del paciente incompletos.",
      notificacion_generada: null,
    },
    almacenamiento_oci: {
      bucket: "mediflow-documentos-clinicos",
      ruta_objeto: "auditoria_humana/DOC-CLIN-2026-8957.json",
      status_backup: "exito",
    },
  },
  {
    // Pediatría + laboratorio (prioritario)
    status: "procesado",
    documento_id: "DOC-CLIN-2026-8961",
    timestamp: "2026-09-30T09:12:27Z",
    canal_origen: "Laboratorio_Central",
    clasificacion: {
      tipo_documento: "Informe de Laboratorio",
      especialidad: "Pediatría / Hematología",
      nivel_prioridad: "Prioritario",
      score_confianza_clasificacion: 0.88,
    },
    datos_extraidos: {
      paciente: {
        nombre: "Mateo Gómez",
        edad: 8,
        unidad_edad: "meses",
        sexo: "M",
        documento_identidad: null,
      },
      medico_solicitante: { nombre: "Dra. Lucía Benítez", matricula: "178204" },
      estudio_realizado: "Hemograma completo",
      diagnostico_principal: "Anemia ferropénica",
      cie10_sugerido: "D50.9",
      medicamentos: null,
      signos_vitales: {
        temperatura: 38.1,
        frecuencia_cardiaca: 150,
        frecuencia_respiratoria: 40,
        presion_arterial: null,
        saturacion_oxigeno: 96,
      },
    },
    decision_enrutamiento: {
      destino_principal: "Historia_Clinica_Electronica",
      requiere_auditoria_humana: false,
      justificacion_enrutamiento: "Resultado de laboratorio completo; se archiva en la historia clínica.",
      notificacion_generada: null,
    },
    almacenamiento_oci: {
      bucket: "mediflow-documentos-clinicos",
      ruta_objeto: "procesados/DOC-CLIN-2026-8961.json",
      status_backup: "exito",
    },
  },
  {
    // Segundo caso para auditoría: confianza media, falta matrícula
    status: "procesado",
    documento_id: "DOC-CLIN-2026-8966",
    timestamp: "2026-09-30T10:47:55Z",
    canal_origen: "Autorizaciones",
    clasificacion: {
      tipo_documento: "Orden de Solicitud de Procedimiento",
      especialidad: "Cardiología",
      nivel_prioridad: "Prioritario",
      score_confianza_clasificacion: 0.62,
    },
    datos_extraidos: {
      paciente: {
        nombre: "Rosa Elena Castillo",
        edad: 67,
        unidad_edad: "años",
        sexo: "F",
        documento_identidad: "EF345678",
      },
      medico_solicitante: { nombre: "Dr. Héctor Vidal", matricula: null },
      estudio_realizado: "Cateterismo cardíaco",
      diagnostico_principal: "Angina inestable",
      cie10_sugerido: "I20.0",
      medicamentos: null,
      signos_vitales: null,
    },
    decision_enrutamiento: {
      destino_principal: "Cola_Revision_Humana",
      requiere_auditoria_humana: true,
      justificacion_enrutamiento:
        "Procedimiento de alto costo sin matrícula del médico solicitante.",
      notificacion_generada: null,
    },
    almacenamiento_oci: {
      bucket: "mediflow-documentos-clinicos",
      ruta_objeto: "auditoria_humana/DOC-CLIN-2026-8966.json",
      status_backup: "exito",
    },
  },
];
