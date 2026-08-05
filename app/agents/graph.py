"""LangGraph wiring for the FixSight agent pipeline."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.alert_dispatcher import alert_dispatcher_node
from app.agents.nodes.fault_diagnosis import fault_diagnosis_node
from app.agents.nodes.llm_reasoner import llm_reasoner_node
from app.agents.nodes.maintenance_advisor import maintenance_advisor_node
from app.agents.nodes.telemetry_ingestor import telemetry_ingestor_node
from app.agents.state import AgentState


@lru_cache(maxsize=1)
def get_agent_graph() -> Any:
    """Build and compile the centralized orchestration graph once."""
    graph = StateGraph(AgentState)
    graph.add_node("telemetry_ingestor", telemetry_ingestor_node)
    graph.add_node("fault_diagnosis", fault_diagnosis_node)
    graph.add_node("llm_reasoner", llm_reasoner_node)
    graph.add_node("maintenance_advisor", maintenance_advisor_node)
    graph.add_node("alert_dispatcher", alert_dispatcher_node)

    graph.add_edge(START, "telemetry_ingestor")
    graph.add_edge("telemetry_ingestor", "fault_diagnosis")
    graph.add_edge("fault_diagnosis", "llm_reasoner")
    graph.add_edge("llm_reasoner", "maintenance_advisor")
    graph.add_edge("maintenance_advisor", "alert_dispatcher")
    graph.add_edge("alert_dispatcher", END)

    return graph.compile()
