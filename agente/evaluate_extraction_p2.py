"""Run P2 against the configured provider; uses at most two LLM requests.

Run from agente: python evaluate_extraction_p2.py
This is a live evaluation, not a mocked unit test. Does not call the API/backend,
change routing, or store a clinical document. Exit 0 only if checked fields match.
Review diagnosis wording manually even on success.
"""
import json
import re

from llm_provider import get_llm
from prompts import build_extraction_prompt
from schemas import DatosExtraidos
from langchain_core.utils.function_calling import convert_to_openai_tool
from extraction_validation import validate_extraction
from test_extraction_p2 import EXPECTED, TEXT


def safe_error(exc):
    # Never log exception text/body: it can contain clinical text or credentials.
    result = {"type": type(exc).__name__}
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        result["status"] = status
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error", body)
        code = error.get("code") if isinstance(error, dict) else None
        if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", code):
            result["code"] = code
    return result


def differences(actual, expected=EXPECTED, prefix=""):
    result = []
    for key, value in expected.items():
        path = f"{prefix}.{key}".strip(".")
        observed = actual.get(key) if isinstance(actual, dict) else None
        if isinstance(value, dict):
            result.extend(differences(observed, value, path))
        elif isinstance(value, list):
            if not isinstance(observed, list) or len(observed) != len(value):
                result.append(path)
            else:
                for i, item in enumerate(value):
                    result.extend(differences(observed[i], item, f"{path}.{i}"))
        elif key in ("diagnostico_principal", "estudio_realizado"):
            if not isinstance(observed, str) or not observed.strip():
                result.append(path)
        elif isinstance(value, str) and isinstance(observed, str):
            if " ".join(value.casefold().split()) != " ".join(observed.casefold().split()):
                result.append(path)
        elif observed != value:
            result.append(path)
    return result


def main():
    llm = get_llm()
    messages = build_extraction_prompt(TEXT)
    try:
        result = llm.with_structured_output(convert_to_openai_tool(DatosExtraidos), include_raw=True).invoke(messages)
        raw = result.get("raw")
        metadata = getattr(raw, "response_metadata", {}) or {}
        print("structured finish_reason:", metadata.get("finish_reason"))
        usage = getattr(raw, "usage_metadata", {}) or {}
        print("structured output_tokens:", usage.get("output_tokens"))
        if metadata.get("finish_reason") in ("length", "max_tokens"):
            print("TRUNCATED: check the extraction token budget; no automatic retry.")
            return 1
        if result.get("parsing_error") is not None:
            raise result["parsing_error"]
        data = validate_extraction(result.get("parsed"))
    except Exception as error:
        print("structured error:", json.dumps(safe_error(error)))
        if getattr(error, "status_code", None) in (401, 403, 429) or type(error).__name__ in (
            "APIConnectionError", "APITimeoutError", "RateLimitError",
        ):
            return 1
        try:
            response = llm.invoke(messages)
            metadata = getattr(response, "response_metadata", {}) or {}
            print("fallback finish_reason:", metadata.get("finish_reason"))
            if metadata.get("finish_reason") in ("length", "max_tokens"):
                print("TRUNCATED fallback")
                return 1
            from nodes import _message_content_to_text
            text = _message_content_to_text(response.content).strip()
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = validate_extraction(json.loads(text))
        except Exception as fallback:
            print("fallback error:", json.dumps(safe_error(fallback)))
            return 1
    payload = data.model_dump(mode="json")
    missing = differences(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("Mismatched fields:", missing)
    print("Manual review: ECG study and diagnosis must retain the documented suspicion.")
    return int(bool(missing))


if __name__ == "__main__":
    raise SystemExit(main())
