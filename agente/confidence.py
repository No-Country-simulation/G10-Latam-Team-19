"""Completitud de extracción únicamente; no define el score final ni enrutamiento."""
from types import MappingProxyType

from schemas import DatosExtraidos, TipoDocumento


# Fuente: Proyecto alura_Data_UmbralScoreyReglas.pdf, pp. 10-11.
# Condiciones pendientes y decisiones temporales: PESOS_PENDIENTES.md.
MISSING_FIELD_PENALTIES = MappingProxyType({
    "paciente.nombre": 0.30,
    "medicamentos_o_dosis": 0.30,
    "paciente.unidad_edad": 0.30,  # Pendiente: señal explícita de pediatría.
    "diagnostico_o_cie10": 0.15,
    "paciente.edad": 0.15,
    "signos_vitales": 0.10,
    "paciente.sexo": 0.05,
    "frecuencia_diaria": 0.05,
})
# EXTRACCIÓN: normalizar marcadores evita contar "Desconocido" como dato presente.
MISSING_TEXT_VALUES = frozenset({
    "", "desconocido", "desconocida", "null", "none", "n/a",
    "no consta", "no consignado", "no consignada", "no informado", "no informada",
})


def is_missing(value: object) -> bool:
    """Edad cero es válida; texto vacío/marcadores y listas vacías no aportan datos."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in MISSING_TEXT_VALUES
    if isinstance(value, (list, tuple)):
        return not value or all(is_missing(item) for item in value)
    return False


def missing_relevant_fields(
    data: DatosExtraidos, document_type: TipoDocumento | None = None,
) -> list[str]:
    # Mantener nombre y edad como críticos, sin inferirlos del documento.
    fields = {
        "paciente.nombre": data.paciente.nombre,
        "paciente.edad": data.paciente.edad,
        "diagnostico_o_cie10": (
            None if is_missing(data.diagnostico_principal) and is_missing(data.cie10_sugerido)
            else True
        ),
        "paciente.sexo": data.paciente.sexo,
    }
    if document_type == TipoDocumento.RECETA_MEDICA:
        medications = data.medicamentos or []
        # Una penalización por categoría, no por medicamento o subcampo.
        # La vía no existe en el contrato actual y no se inventa.
        fields["medicamentos_o_dosis"] = (
            None if not medications or any(
                is_missing(m.nombre) or is_missing(m.dosis) for m in medications
            ) else True
        )
        fields["frecuencia_diaria"] = (
            None if not medications or any(is_missing(m.frecuencia_diaria) for m in medications)
            else True
        )
    # Un objeto presente permite detectar incompletitud; null no permite
    # distinguir entre «no aplica» y «faltan todos». Pendiente de Datos.
    if data.signos_vitales is not None:
        fields["signos_vitales"] = (
            None if any(is_missing(v) for v in data.signos_vitales.model_dump().values())
            else True
        )
    # Unidad de edad: peso documentado pero sin activar hasta contar con
    # evidencia de pediatría independiente de la unidad que falta.
    return [name for name, value in fields.items() if is_missing(value)]


def confidence_score(
    data: DatosExtraidos,
    document_type: TipoDocumento | None = None,
) -> float:
    """Score de completitud con pesos de Datos: base fija 1 menos ausencias, en [0, 1]."""
    # EXTRACCIÓN: cálculo local posterior a Pydantic; no añade llamadas al LLM.
    # La base fija evita descontar otra vez un score de una ejecución anterior.
    # Este indicador de completitud no mide exactitud clínica ni decide el destino.
    penalty = sum(
        MISSING_FIELD_PENALTIES[name]
        for name in missing_relevant_fields(data, document_type)
    )
    return round(max(0.0, min(1.0, 1.0 - penalty)), 6)
