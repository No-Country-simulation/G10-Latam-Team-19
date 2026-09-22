#
# Los nodos por ahora son placeholders (levantan NotImplementedError a propósito)
# Hasta que cada responsable complete su prompt real.
#

from graph import build_graph

if __name__ == "__main__":
    graph = build_graph()

    initial_state = {
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

    result = graph.invoke(initial_state)
    print(result)