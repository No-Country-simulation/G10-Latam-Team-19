"""Completitud de extracción únicamente; no define el score final ni enrutamiento."""
from types import MappingProxyType

from schemas import DatosExtraidos, TipoDocumento


# PROVISIONAL (Datos): Michelle indicó bajar el score por ausencias, no estos pesos.
# Centralizarlos permite calibrarlos sin cambiar la extracción ni el nodo final.
MISSING_FIELD_PENALTIES = MappingProxyType({
    "paciente.nombre": 0.15,
    "paciente.edad": 0.10,
    "medico_solicitante.nombre": 0.10,
    "diagnostico_principal": 0.20,
    "estudio_realizado": 0.10,
    "medicamentos": 0.10,
    "dosis": 0.05,
})
# EXTRACCIÓN: normalizar marcadores evita contar "Desconocido" como dato presente.
MISSING_TEXT_VALUES = frozenset({
    "", "desconocido", "desconocida", "null", "none", "n/a",
    "no consta", "no consignado", "no consignada", "no informado", "no informada",
})
STUDY_DOCUMENT_TYPES = frozenset({
    TipoDocumento.INFORME_ESTUDIO, TipoDocumento.INFORME_LABORATORIO,
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
    # EXTRACCIÓN: registrar ausencias explica el descuento sin rechazar campos opcionales.
    fields = {
        "paciente.nombre": data.paciente.nombre,
        "paciente.edad": data.paciente.edad,
        "medico_solicitante.nombre": (
            data.medico_solicitante.nombre if data.medico_solicitante else None
        ),
        "diagnostico_principal": data.diagnostico_principal,
    }
    # No exigir estudios ni tratamiento en documentos donde pueden no aplicar.
    if document_type in STUDY_DOCUMENT_TYPES:
        fields["estudio_realizado"] = data.estudio_realizado
    if document_type == TipoDocumento.RECETA_MEDICA:
        fields["medicamentos"] = data.medicamentos
    if document_type == TipoDocumento.RECETA_MEDICA or not is_missing(data.medicamentos):
        fields["dosis"] = data.dosis
    # Matrícula y CIE-10 siguen siendo opcionales sin penalización.
    return [name for name, value in fields.items() if is_missing(value)]


def confidence_score(
    data: DatosExtraidos,
    document_type: TipoDocumento | None = None,
) -> float:
    """Score provisional de extracción: base fija 1 menos ausencias, en [0, 1]."""
    # EXTRACCIÓN: cálculo local posterior a Pydantic; no añade llamadas al LLM.
    # La base fija evita descontar otra vez un score de una ejecución anterior.
    # Este indicador de completitud no mide exactitud clínica ni decide el destino.
    penalty = sum(
        MISSING_FIELD_PENALTIES[name]
        for name in missing_relevant_fields(data, document_type)
    )
    return round(max(0.0, min(1.0, 1.0 - penalty)), 6)
