
import argparse
import sys
from pathlib import Path

from graph import build_graph

_graph = None


def _get_graph():
    """Compila el grafo una sola vez y lo reutiliza entre invocaciones."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def procesar_documento(document_id: str, document_text: str, origin_channel: str) -> dict:
    """Ejecuta el grafo real sobre un documento y devuelve el estado final (AgentState)."""
    initial_state = {
        "document_id": document_id,
        "document_text": document_text,
        "origin_channel": origin_channel,
    }
    return _get_graph().invoke(initial_state)


# Documento de prueba (solo si el script se corre sin --texto/--archivo).
DEMO_DOCUMENT = {
    "document_id": "DOC-CLIN-2026-8942",
    "document_text": (
        "HOSPITAL SANTA LUCIA - INFORME DE ESTUDIO RADIOLOGICO. "
        "Paciente: Carlos Eduardo Mendes, 52 años. "
        "Medico Solicitante: Dra. Renata Silveira MP 145892. "
        "Estudio: Tomografía de Torax con contraste. "
        "Hallazgos: Defecto de llenado en arteria pulmonar principal "
        "derecha compatible con TEP agudo."
    ),
    "origin_channel": "Guardia_Emergencias",
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Corre el grafo del agente sobre un documento.")
    parser.add_argument("--id", dest="document_id", help="ID del documento (ej. DOC-CLIN-2026-0001)")
    parser.add_argument("--canal", dest="origin_channel", help="Canal de origen (ej. Guardia_Emergencias)")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--texto", dest="document_text", help="Texto del documento")
    source.add_argument("--archivo", help="Ruta a un archivo de texto UTF-8 con el documento")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()

    if args.archivo:
        text = Path(args.archivo).read_text(encoding="utf-8")
    else:
        text = args.document_text

    if text is None:
        document = DEMO_DOCUMENT
    else:
        if not args.document_id:
            sys.exit("Falta --id cuando se pasa --texto o --archivo.")
        document = {
            "document_id": args.document_id,
            "document_text": text,
            "origin_channel": args.origin_channel or "Desconocido",
        }

    result = procesar_documento(**document)
    print(result)
