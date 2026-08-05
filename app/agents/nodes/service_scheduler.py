from __future__ import annotations

from app.agents.state import AgentState
from app.core.database import SessionLocal
from app.services.ml_services import MLService

from sklearn.metrics.pairwise import haversine_distances
from math import radians

def service_agent(state: AgentState) -> AgentState:
    """Analyze the service center workflow"""
    
    
    userrow = state.get("telemetry_row")
    if not telemetry_row:
        raise ValueError("telemetry_row is missing in state. Run telemetry_ingestor_node first.")

    prediction = MLService.predict_fault(telemetry_row)
    probability = float(prediction["fault_probability"])
    severity = MLService.derive_severity(probability)

    next_state: AgentState = {
        **state,
        "fault_class_id": int(prediction["fault_class_id"]),
        "fault_label": str(prediction["fault_label"]),
        "fault_probability": probability,
        "severity": severity,
    }

    telemetry_reading_id = state.get("telemetry_reading_id")
    if telemetry_reading_id is not None:
        with SessionLocal() as db:
            saved = MLService.save_fault_prediction(
                db=db,
                vehicle_id=state["vehicle_id"],
                telemetry_reading_id=int(telemetry_reading_id),
                fault_label=next_state["fault_label"],
                fault_probability=next_state["fault_probability"],
            )
        next_state["fault_prediction_id"] = int(saved.id)

    return next_state
