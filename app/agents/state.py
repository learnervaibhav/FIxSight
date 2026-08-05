"""State contracts for the agent pipeline."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentStateRequired(TypedDict):
    """Fields required to start the agent pipeline."""

    vehicle_id: str


class MaintenanceActionItem(TypedDict):
    """One structured maintenance task produced by the advisor node."""

    title: str
    owner: str
    priority: str
    due_in_hours: int
    notes: str


class AgentState(AgentStateRequired, total=False):
    """Shared mutable state that flows through LangGraph nodes.

    Keep this structure as your single source of truth for node I/O:
    - `telemetry_payload` or `telemetry_reading_id` is expected as input.
    - `telemetry_row` is produced by telemetry ingestion.
    - fault-related fields are produced by fault diagnosis.
    """

    # Input options
    telemetry_payload: dict[str, Any]
    telemetry_reading_id: int

    # Data created/normalized by ingestion
    telemetry_row: dict[str, float | int]

    # Fault diagnosis outputs
    fault_prediction_id: int
    fault_class_id: int
    fault_label: str
    fault_probability: float
    severity: str

    # LLM reasoner outputs
    llm_status: str
    llm_model: str
    llm_explanation: str

    # Maintenance advisor outputs
    maintenance_priority: str
    recommended_service_window_hours: int
    maintenance_action_items: list[MaintenanceActionItem]

    # Alert dispatcher outputs
    alert_log_id: int
    alert_status: str
    alert_dispatched: bool
    alert_provider_message_id: str | None

    # Service scheduler inputs
    user_location: dict[str, float]  # {"latitude": ..., "longitude": ...}
    user_preferred_date: str  # ISO format date
    service_duration_minutes: int

    # Service scheduler outputs
    selected_service_center: dict[str, Any]  # {"center_id", "center_name", "location", ...}
    scheduled_slot_time: str  # ISO format datetime
    service_slot_id: str
    service_slot_status: str

    # Operational metadata
    errors: list[str]


