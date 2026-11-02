"""Remaining-useful-life forecast node for the agent pipeline."""

from __future__ import annotations

from typing import cast

from app.agents.state import AgentState
from app.core.database import SessionLocal


def rul_forecast_node(state: AgentState) -> AgentState:
    """Forecast RUL hours (trained regressor, rule-based fallback) and persist it."""
    from app.services import MLService

    telemetry_row = state.get("telemetry_row")
    if not telemetry_row:
        raise ValueError("telemetry_row is missing in state. Run telemetry_ingestor_node first.")

    with SessionLocal() as db:
        previous = MLService.get_latest_rul_hours(db, state["vehicle_id"])
        forecast = MLService.predict_rul(telemetry_row, previous_rul_hours=previous)

        next_state = {
            **state,
            "rul_hours": float(forecast["rul_hours"]),
            "rul_confidence": float(forecast["rul_confidence"]),
            "rul_source": str(forecast.get("rul_source", "rule")),
        }

        telemetry_reading_id = state.get("telemetry_reading_id")
        if telemetry_reading_id is not None:
            saved = MLService.save_rul_prediction(
                db=db,
                vehicle_id=state["vehicle_id"],
                telemetry_reading_id=int(telemetry_reading_id),
                rul_hours=next_state["rul_hours"],
                rul_confidence=next_state["rul_confidence"],
            )
            next_state["rul_prediction_id"] = int(saved.id)

    return cast(AgentState, next_state)
