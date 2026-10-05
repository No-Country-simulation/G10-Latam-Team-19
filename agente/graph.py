#
# Flujo real:
#
#   clasificación -> extracción -> score_confianza (Nodo 1)
#         |
#         v
#   ¿score < 0.75?
#     SI -> corte_revision_humana -> FIN
#     NO -> nodo_2 (prioridad, Natalia) -> enrutamiento_final -> FIN
#
# El score que decide el gate es el determinístico de Extracción
# (extraction_confidence_score).
#

from langgraph.graph import END, StateGraph

from nodes import (
    classification_node,
    extraction_node,
    confidence_node,
    corte_revision_humana_node,
    priority_node,
    enrutamiento_final_node,
)
from state import AgentState


def gate_score_confianza(state: AgentState) -> str:
    """Decide si el flujo se corta en banda Baja o avanza al Nodo 2."""
    if state["final_confidence_score"] < 0.75:
        return "corte_revision_humana"
    return "nodo_2"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("clasificación", classification_node)
    graph.add_node("extracción", extraction_node)
    graph.add_node("score_confianza", confidence_node)
    graph.add_node("corte_revision_humana", corte_revision_humana_node)
    graph.add_node("nodo_2", priority_node)
    graph.add_node("enrutamiento_final", enrutamiento_final_node)

    graph.set_entry_point("clasificación")
    graph.add_edge("clasificación", "extracción")
    graph.add_edge("extracción", "score_confianza")

    graph.add_conditional_edges(
        "score_confianza",
        gate_score_confianza,
        {
            "corte_revision_humana": "corte_revision_humana",
            "nodo_2": "nodo_2",
        },
    )

    graph.add_edge("corte_revision_humana", END)
    graph.add_edge("nodo_2", "enrutamiento_final")
    graph.add_edge("enrutamiento_final", END)

    return graph.compile()
