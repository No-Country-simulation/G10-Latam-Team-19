// Tipos derivados de schemas.py (raíz del repo). Mantener sincronizados.
// Optional[T] de Pydantic -> T | null. Los enums son arreglos `as const`
// con su tipo unión derivado.

// -----------------------------
// Enums
// -----------------------------

export const TIPOS_ARCHIVO = ["PDF", "IMAGEN", "TEXTO", "JSON"] as const;
export type TipoArchivo = (typeof TIPOS_ARCHIVO)[number];

export const TIPOS_DOCUMENTO = [
  "Receta Medica",
  "Informe de Estudio",
  "Informe de Laboratorio",
  "Orden de Solicitud de Procedimiento",
  "Epicrisis / Informe de Alta",
  "Certificado Medico",
  "Desconocido",
] as const;
export type TipoDocumento = (typeof TIPOS_DOCUMENTO)[number];

export const NIVELES_PRIORIDAD = ["Rutina", "Prioritario", "Urgente"] as const;
export type NivelPrioridad = (typeof NIVELES_PRIORIDAD)[number];

export const ESTADOS_DOCUMENTO = [
  "recibidos",
  "procesados",
  "auditoria_humana",
  "validados",
] as const;
export type EstadoDocumento = (typeof ESTADOS_DOCUMENTO)[number];

export const DESTINOS_ENRUTAMIENTO = [
  "Cola_Emergencia_Medica",
  "Auditoria_Autorizaciones",
  "Farmacia_Hospitalaria",
  "Cola_Revision_Humana",
  "Historia_Clinica_Electronica",
] as const;
export type DestinoEnrutamiento = (typeof DESTINOS_ENRUTAMIENTO)[number];

export const UNIDADES_EDAD = ["años", "meses", "dias"] as const;
export type UnidadEdad = (typeof UNIDADES_EDAD)[number];

// -----------------------------
// Request
// -----------------------------

export interface DocumentoClinicoRequest {
  documento_id: string;
  tipo_archivo: TipoArchivo;
  /** Mínimo 10 caracteres, no puede estar vacío. */
  documento_texto: string;
  canal_origen: string;
}

// -----------------------------
// Sub-modelos de la respuesta
// -----------------------------

export interface Clasificacion {
  tipo_documento: TipoDocumento;
  especialidad: string;
  nivel_prioridad: NivelPrioridad;
  /** Entre 0 y 1. */
  score_confianza_clasificacion: number;
}

export interface Paciente {
  nombre: string;
  /** 0–130. */
  edad: number | null;
  unidad_edad: UnidadEdad | null;
  /** "M" o "F". */
  sexo: "M" | "F" | null;
  /** 6–12 caracteres [A-Z0-9]. */
  documento_identidad: string | null;
}

export interface MedicoSolicitante {
  nombre: string;
  matricula: string | null;
}

export interface MedicamentoPrescrito {
  nombre: string;
  dosis: string | null;
  frecuencia_diaria: string | null;
}

export interface SignosVitales {
  /** °C, 25–45. */
  temperatura: number | null;
  /** lpm, 0–200. */
  frecuencia_cardiaca: number | null;
  /** rpm, 0–100. */
  frecuencia_respiratoria: number | null;
  /** Formato "120/80". */
  presion_arterial: string | null;
  /** SpO2 %, 0–100. */
  saturacion_oxigeno: number | null;
}

export interface DatosExtraidos {
  paciente: Paciente;
  medico_solicitante: MedicoSolicitante | null;
  estudio_realizado: string | null;
  diagnostico_principal: string | null;
  /** Código CIE-10, ej: "I26.9". */
  cie10_sugerido: string | null;
  medicamentos: MedicamentoPrescrito[] | null;
  signos_vitales: SignosVitales | null;
}

export interface NotificacionGenerada {
  canal: string;
  mensaje: string;
}

export interface DecisionEnrutamiento {
  destino_principal: DestinoEnrutamiento;
  requiere_auditoria_humana: boolean;
  justificacion_enrutamiento: string;
  notificacion_generada: NotificacionGenerada | null;
}

export interface AlmacenamientoOCI {
  bucket: string;
  ruta_objeto: string;
  status_backup: string;
}

// -----------------------------
// Response
// -----------------------------

export interface TriageResponse {
  status: string;
  documento_id: string;
  /** ISO 8601 (datetime serializado por Pydantic). */
  timestamp: string;
  clasificacion: Clasificacion;
  datos_extraidos: DatosExtraidos;
  decision_enrutamiento: DecisionEnrutamiento;
  almacenamiento_oci: AlmacenamientoOCI | null;
  canal_origen: string;
}
