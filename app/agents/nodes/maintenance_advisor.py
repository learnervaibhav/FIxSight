"""Maintenance advisor node for structured action planning."""

from __future__ import annotations

from typing import cast

from app.agents.state import AgentState


def _priority_from_severity(severity: str) -> str:
    level = severity.upper().strip()
    if level == "HIGH":
        return "P1"
    if level == "MEDIUM":
        return "P2"
    return "P3"


def _service_window_hours(severity: str, probability: float) -> int:
    level = severity.upper().strip()
    if level == "HIGH" or probability >= 0.9:
        return 24
    if level == "MEDIUM" or probability >= 0.7:
        return 72
    return 168


def maintenance_advisor_node(state: AgentState) -> AgentState:
    """Convert predictions into structured and actionable maintenance items."""
    fault_label = str(state.get("fault_label", "Unknown fault"))
    severity = str(state.get("severity", "LOW"))
    probability = float(state.get("fault_probability", 0.0))

    priority = _priority_from_severity(severity)
    window_hours = _service_window_hours(severity, probability)

    action_items = [
        {
            "title": "Confirm diagnostic trouble codes",
            "owner": "technician",
            "priority": priority,
            "due_in_hours": 4,
            "notes": f"Validate fault pattern for '{fault_label}' using scan tool and freeze-frame data.",
        },
        {
            "title": "Perform targeted subsystem inspection",
            "owner": "service_team",
            "priority": priority,
            "due_in_hours": min(window_hours, 24),
            "notes": "Check connectors, sensors, fluid quality, and thermal conditions related to predicted fault.",
        },
        {
            "title": "Schedule maintenance appointment",
            "owner": "advisor",
            "priority": priority,
            "due_in_hours": window_hours,
            "notes": f"Recommended maintenance window is within {window_hours} hours.",
        },
    ]

    next_state = {
        **state,
        "maintenance_priority": priority,
        "recommended_service_window_hours": window_hours,
        "maintenance_action_items": action_items,
    }
    return cast(AgentState, next_state)
