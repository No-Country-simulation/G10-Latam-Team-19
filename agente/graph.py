#
# Versión actual: flujo LINEAL (sin ramas condicionales)
# clasificación -> extracción -> score_confianza -> FIN
#
# Las ramas condicionales se agregarán en una segunda iteración, una vez que los 3 nodos básicos
# funcionen de manera aislada y el equipo de Datos haya definido los umbrales y reglas de decisión.
#

from langgraph.graph import END, StateGraph

from nodes import classification_node, extraction_node, confidence_node
from state import AgentState

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("clasificación", classification_node)
    graph.add_node("extracción", extraction_node)
    graph.add_node("score_confianza", confidence_node)

    graph.set_entry_point("clasificación")
    graph.add_edge("clasificación", "extracción")
    graph.add_edge("extracción", "score_confianza")
    graph.add_edge("score_confianza", END)

    return graph.compile()
