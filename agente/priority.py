"""Nodo 2: prioridad por reglas. Funciones puras; los umbrales viven en priority_config.json."""

import json
import re
import unicodedata
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("priority_config.json")


def load_config(path: Path = CONFIG_PATH) -> dict:
    # Sin try/except a propósito: un default vacío ocultaría medicamentos restringidos.
    with path.open(mode="r", encoding="utf-8") as config_file:
        return json.load(config_file)


def normalize(text: str) -> str:
    # Se conserva U+0303 (tilde de ñ, ã, õ) para no confundir 'año' con 'ano'.
    decomposed = unicodedata.normalize("NFD", text.casefold().strip())
    clean_text = "".join(
        c
        for c in decomposed
        if unicodedata.combining(c) == 0 or c == "̃"
    )
    return unicodedata.normalize("NFC", clean_text)


def contains_term(text: str, term: str) -> bool:
    # \b evita que 'tep' coincida dentro de otra palabra.
    pattern = rf"\b{re.escape(normalize(term))}\b"
    return re.search(pattern, normalize(text)) is not None


def evaluate_medications(medication_names: list[str] | None, config: dict) -> dict:
    restricted_found = []

    for name in medication_names or []:
        for family, terms in config["medicamentos_restringidos"].items():
            if any(contains_term(name, term) for term in terms):
                restricted_found.append({"medicamento": name, "familia": family})
                break

    return {
        "force_audit": bool(restricted_found),
        "restricted_found": restricted_found,
    }


def evaluate_keywords(diagnosis: str | None, config: dict) -> dict:
    if not diagnosis:
        return {"level": None, "matched": []}

    # De la más grave a la más leve: la primera banda con coincidencia gana.
    for level in reversed(config["orden_gravedad"]):
        matched = [
            term
            for term in config["palabras_clave"][level.lower()]
            if contains_term(diagnosis, term)
        ]
        if matched:
            return {"level": level, "matched": matched}

    return {"level": None, "matched": []}




def value_matches(value: float, condition: dict) -> bool:
    operator, limit = next(iter(condition.items()))
    if operator == "lt":
        return value < limit
    if operator == "gt":
        return value > limit
    if operator == "between":
        low, high = limit
        return low <= value <= high
    raise ValueError(f"Operador desconocido en la configuración: {operator}")


def classify_value(value: float, bands: dict) -> str | None:
    # Urgente se revisa primero: si un valor cae en dos bandas, gana la más grave.
    for key in ("urgente", "prioritario"):
        if any(value_matches(value, condition) for condition in bands[key]):
            return key.capitalize()
    return None

def age_group(age: int | None, age_unit: str | None, config: dict) -> str | None:
    if age_unit in ("meses", "dias"):
        return "pediatrico_meses_dias"
    if age_unit == "años" and age is not None:
        return "pediatrico_anos" if age <= config["edad_pediatrica_maxima_anos"] else "adulto"
    return None


def most_severe(levels: list[str], config: dict) -> str | None:
    return max(levels, key=config["orden_gravedad"].index, default=None)


def classify_blood_pressure(value: str, bands: dict, config: dict) -> str | None:
    match = re.fullmatch(r"(\d{2,3})/(\d{2,3})", value)
    if match is None:
        raise ValueError(f"Presión arterial con formato inválido: {value!r}")

    systolic, diastolic = int(match.group(1)), int(match.group(2))
    levels = [
        classify_value(
            number,
            {key: bands[key][part] for key in ("urgente", "prioritario")},
        )
        for number, part in ((systolic, "sistolica"), (diastolic, "diastolica"))
    ]
    return most_severe([level for level in levels if level], config)


def evaluate_vitals(
    vitals: dict | None, age: int | None, age_unit: str | None, config: dict
) -> dict:
    group = age_group(age, age_unit, config)
    missing = []
    if vitals is None:
        missing.append("signos_vitales")
    if group is None:
        missing.append("paciente.edad" if age_unit == "años" else "paciente.unidad_edad")
    if missing:
        return {"level": None, "triggered": [], "missing": missing}

    levels = []
    triggered = []
    for sign, bands_by_group in config["signos_vitales"].items():
        value = vitals.get(sign)
        if value is None:
            missing.append(f"signos_vitales.{sign}")
            continue

        bands = bands_by_group[group]
        if sign == "presion_arterial":
            level = classify_blood_pressure(value, bands, config)
        else:
            level = classify_value(value, bands)

        if level:
            levels.append(level)
            triggered.append({"signo": sign, "valor": value, "nivel": level})

    return {
        "level": most_severe(levels, config),
        "triggered": triggered,
        "missing": missing,
    }


def evaluate_priority(extracted_data: dict, config: dict) -> dict:
    patient = extracted_data.get("paciente") or {}
    medication_names = [m["nombre"] for m in extracted_data.get("medicamentos") or []]

    keywords = evaluate_keywords(extracted_data.get("diagnostico_principal"), config)
    vitals = evaluate_vitals(
        extracted_data.get("signos_vitales"),
        patient.get("edad"),
        patient.get("unidad_edad"),
        config,
    )
    medications = evaluate_medications(medication_names, config)

    levels = [result["level"] for result in (keywords, vitals) if result["level"]]
    # Sin ninguna señal el caso queda en la banda más leve; los faltantes quedan registrados.
    level = most_severe(levels, config) or config["orden_gravedad"][0]

    # La urgencia gana sobre el destino por contenido; un fármaco restringido fuerza Auditoría.
    destinations = config["destinos"]
    if level == "Urgente":
        destination = destinations["emergencia"]
    elif medications["force_audit"]:
        destination = destinations["auditoria"]
    elif level == "Prioritario" and medication_names:
        destination = destinations["farmacia"]
    else:
        destination = destinations["historia_clinica"]

    return {
        "nivel_prioridad": level,
        "destino_principal": destination,
        "disparar_alerta": level == "Urgente",
        "forzar_auditoria": medications["force_audit"],
        "datos_faltantes": vitals["missing"],
    }
