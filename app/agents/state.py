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

    # Run controls
    llm_enabled: bool  # False skips the Gemini call (deterministic explanation instead)
    auto_schedule: bool  # book a service slot automatically when the fault warrants it
    schedule_service: bool  # force a booking regardless of severity
    alert_suppressed: bool  # True when this fault episode was already notified
    allow_real_sms: bool  # False when a real-SMS budget is exhausted
    simulation_time: str  # ISO datetime; "now" for scheduling in simulations
    explanation_hint: str  # explanation from earlier in the same fault episode, reused instead of re-asking the LLM

    # Data created/normalized by ingestion
    telemetry_row: dict[str, float | int]

    # Fault diagnosis outputs
    fault_prediction_id: int
    fault_class_id: int
    fault_label: str
    fault_probability: float
    is_fault: bool
    severity: str

    # RUL forecast outputs
    rul_prediction_id: int
    rul_hours: float
    rul_confidence: float
    rul_source: str

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
    alert_mode: str
    alert_message: str

    # Service scheduler inputs
    user_location: dict[str, float]  # {"latitude": ..., "longitude": ...}
    user_preferred_date: str  # ISO format date
    service_duration_minutes: int

    # Service scheduler outputs
    service_booking_status: str  # booked / existing / unavailable
    selected_service_center: dict[str, Any]  # {"center_id", "center_name", "location", ...}
    scheduled_slot_time: str  # ISO format datetime
    service_slot_id: str
    service_slot_status: str

    # Operational metadata
    errors: list[str]
