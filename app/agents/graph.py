"""LangGraph wiring for the FixSight agent pipeline.

telemetry_ingestor → fault_diagnosis → rul_forecast → llm_reasoner → maintenance_advisor
    → [needs service?] service_scheduler → [should alert?] alert_dispatcher → END
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.alert_dispatcher import alert_dispatcher_node, should_alert
from app.agents.nodes.fault_diagnosis import fault_diagnosis_node
from app.agents.nodes.llm_reasoner import llm_reasoner_node
from app.agents.nodes.maintenance_advisor import maintenance_advisor_node
from app.agents.nodes.rul_forecast import rul_forecast_node
from app.agents.nodes.service_scheduler import needs_service, service_scheduler_node
from app.agents.nodes.telemetry_ingestor import telemetry_ingestor_node
from app.agents.state import AgentState


def _route_after_advisor(state: AgentState) -> str:
    if needs_service(state):
        return "service_scheduler"
    return "alert_dispatcher" if should_alert(state) else END


def _route_after_scheduler(state: AgentState) -> str:
    return "alert_dispatcher" if should_alert(state) else END


@lru_cache(maxsize=1)
def get_agent_graph() -> Any:
    """Build and compile the centralized orchestration graph once."""
    graph = StateGraph(AgentState)
    graph.add_node("telemetry_ingestor", telemetry_ingestor_node)
    graph.add_node("fault_diagnosis", fault_diagnosis_node)
    graph.add_node("rul_forecast", rul_forecast_node)
    graph.add_node("llm_reasoner", llm_reasoner_node)
    graph.add_node("maintenance_advisor", maintenance_advisor_node)
    graph.add_node("service_scheduler", service_scheduler_node)
    graph.add_node("alert_dispatcher", alert_dispatcher_node)

    graph.add_edge(START, "telemetry_ingestor")
    graph.add_edge("telemetry_ingestor", "fault_diagnosis")
    graph.add_edge("fault_diagnosis", "rul_forecast")
    graph.add_edge("rul_forecast", "llm_reasoner")
    graph.add_edge("llm_reasoner", "maintenance_advisor")
    graph.add_conditional_edges(
        "maintenance_advisor",
        _route_after_advisor,
        ["service_scheduler", "alert_dispatcher", END],
    )
    graph.add_conditional_edges("service_scheduler", _route_after_scheduler, ["alert_dispatcher", END])
    graph.add_edge("alert_dispatcher", END)

    return graph.compile()
