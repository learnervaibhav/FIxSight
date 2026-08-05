"""Service layer for executing the agent pipeline."""

from __future__ import annotations

from typing import Any, cast

from app.agents.graph import get_agent_graph
from app.agents.state import AgentState


class AgentService:
    """Centralized orchestration for LangGraph pipeline execution."""

    @staticmethod
    def run_pipeline(vehicle_id: str, telemetry_row: dict[str, Any]) -> AgentState:
        """Run full agent graph and return final pipeline state."""
        if not isinstance(telemetry_row, dict):
            raise ValueError("telemetry_row must be a JSON object")

        initial_state: AgentState = {
            "vehicle_id": vehicle_id,
            "telemetry_payload": telemetry_row,
        }

        graph = get_agent_graph()
        graph_state = graph.invoke(initial_state)
        return cast(AgentState, graph_state)
