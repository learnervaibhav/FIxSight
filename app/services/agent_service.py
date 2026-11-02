"""Service layer for executing the agent pipeline."""

from __future__ import annotations

from typing import Any, cast

from app.agents.graph import get_agent_graph
from app.agents.state import AgentState


class AgentService:
    """Centralized orchestration for LangGraph pipeline execution."""

    @staticmethod
    def run_pipeline(
        vehicle_id: str,
        telemetry_row: dict[str, Any] | None = None,
        *,
        telemetry_reading_id: int | None = None,
        alert_mode: str = "mock",
        schedule_service: bool = False,
        auto_schedule: bool = True,
        preferred_time: str | None = None,
        duration_hours: float | None = None,
        llm_enabled: bool = True,
        alert_suppressed: bool = False,
        allow_real_sms: bool = True,
        simulation_time: str | None = None,
        explanation_hint: str | None = None,
    ) -> AgentState:
        """Run full agent graph and return final pipeline state."""
        if telemetry_row is None and telemetry_reading_id is None:
            raise ValueError("Provide telemetry_row or telemetry_reading_id")
        if telemetry_row is not None and not isinstance(telemetry_row, dict):
            raise ValueError("telemetry_row must be a JSON object")
        if alert_mode not in {"mock", "real"}:
            raise ValueError("alert_mode must be 'mock' or 'real'")

        initial_state: AgentState = {
            "vehicle_id": vehicle_id,
            "alert_mode": alert_mode,
            "schedule_service": schedule_service,
            "auto_schedule": auto_schedule,
            "llm_enabled": llm_enabled,
            "alert_suppressed": alert_suppressed,
            "allow_real_sms": allow_real_sms,
            "errors": [],
        }
        if telemetry_row is not None:
            initial_state["telemetry_payload"] = telemetry_row
        else:
            initial_state["telemetry_reading_id"] = int(cast(int, telemetry_reading_id))
        if duration_hours is not None:
            initial_state["service_duration_minutes"] = int(duration_hours * 60)
        if preferred_time is not None:
            initial_state["user_preferred_date"] = preferred_time
        if simulation_time is not None:
            initial_state["simulation_time"] = simulation_time
        if explanation_hint:
            initial_state["explanation_hint"] = explanation_hint

        graph = get_agent_graph()
        return cast(AgentState, graph.invoke(initial_state))
