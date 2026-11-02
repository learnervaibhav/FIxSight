"""Fault diagnosis node for the agent pipeline."""

from __future__ import annotations

from app.agents.state import AgentState
from app.core.database import SessionLocal
from app.core.events import event_bus


def fault_diagnosis_node(state: AgentState) -> AgentState:
    """Run fault prediction and persist it when telemetry id is available."""
    from app.services import MLService

    telemetry_row = state.get("telemetry_row")
    if not telemetry_row:
        raise ValueError("telemetry_row is missing in state. Run telemetry_ingestor_node first.")

    prediction = MLService.predict_fault(telemetry_row)
    label = str(prediction["fault_label"])
    probability = float(prediction["fault_probability"])
    severity = MLService.derive_severity(probability, label)

    next_state: AgentState = {
        **state,
        "fault_class_id": int(prediction["fault_class_id"]),
        "fault_label": label,
        "fault_probability": probability,
        "is_fault": bool(prediction["is_fault"]),
        "severity": severity,
    }

    telemetry_reading_id = state.get("telemetry_reading_id")
    if telemetry_reading_id is not None:
        with SessionLocal() as db:
            saved = MLService.save_fault_prediction(
                db=db,
                vehicle_id=state["vehicle_id"],
                telemetry_reading_id=int(telemetry_reading_id),
                fault_label=label,
                fault_probability=probability,
            )
        next_state["fault_prediction_id"] = int(saved.id)

    # Announce only the first detection of an episode (repeats are suppressed upstream).
    if next_state["is_fault"] and severity != "LOW" and not state.get("alert_suppressed"):
        event_bus.publish(
            "fault_detected",
            f"{severity.title()} fault detected",
            f"{state['vehicle_id']}: {label} ({probability:.0%})",
            severity="critical" if severity == "HIGH" else "warning",
            vehicle_id=state["vehicle_id"],
            data={"fault_label": label, "fault_probability": probability, "severity": severity},
        )

    return next_state
