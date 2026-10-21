"""Normalize known LLM key suffixes before Pydantic can discard them.

Only accepts an exact schema field or that field followed by ONE underscore.
Does not infer values, repair types or change the shared response models.
"""
from typing import get_args, get_origin

from pydantic import BaseModel

from schemas import DatosExtraidos


def _nested_model(annotation):
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    for item in get_args(annotation):
        nested = _nested_model(item)
        if nested is not None:
            return nested
    return None


def _normalize(payload, model):
    if isinstance(payload, BaseModel):
        payload = payload.model_dump()
    if not isinstance(payload, dict):
        raise ValueError("Extraction object must be a dictionary.")
    normalized = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            raise ValueError("Extraction field names must be strings.")
        target = key if key in model.model_fields else key.removesuffix("_")
        if target not in model.model_fields:
            raise ValueError("Unknown extraction field; refusing silent data loss.")
        if target in normalized:
            raise ValueError("Duplicate extraction field after normalization.")
        annotation = model.model_fields[target].annotation
        nested = _nested_model(annotation)
        if nested is not None and value is not None:
            # Preserve container types; Pydantic still rejects malformed shapes.
            is_list = get_origin(annotation) is list or any(
                get_origin(arg) is list for arg in get_args(annotation)
            )
            if is_list and isinstance(value, list):
                value = [_normalize(item, nested) for item in value]
            elif not is_list and isinstance(value, (dict, BaseModel)):
                value = _normalize(value, nested)
        normalized[target] = value
    return normalized


def validate_extraction(payload):
    return DatosExtraidos.model_validate(_normalize(payload, DatosExtraidos))
