"""Telemetry ingestion node for the agent pipeline."""

from __future__ import annotations

from typing import Any, cast

from app.agents.state import AgentState
from app.core.database import SessionLocal
from app.schemas.telemetry import TelemetryReadingCreate


def _to_feature_row(reading: Any) -> dict[str, float | int]:
    """Extract model-ready telemetry fields from a DB reading."""
    return {
        "engine_rpm": float(reading.engine_rpm),
        "engine_load": float(reading.engine_load),
        "coolant_temperature": float(reading.coolant_temperature),
        "oil_temperature": float(reading.oil_temperature),
        "oil_pressure": float(reading.oil_pressure),
        "fuel_rate": float(reading.fuel_rate),
        "short_term_fuel_trim": float(reading.short_term_fuel_trim),
        "long_term_fuel_trim": float(reading.long_term_fuel_trim),
        "mass_air_flow": float(reading.mass_air_flow),
        "intake_manifold_pressure": float(reading.intake_manifold_pressure),
        "battery_voltage": float(reading.battery_voltage),
        "alternator_voltage": float(reading.alternator_voltage),
        "gear_position": int(reading.gear_position),
        "transmission_temperature": float(reading.transmission_temperature),
        "o2_sensor_voltage": float(reading.o2_sensor_voltage),
        "egr_position": float(reading.egr_position),
        "vehicle_speed": float(reading.vehicle_speed),
        "throttle_position": float(reading.throttle_position),
        "cumulative_engine_hours": float(reading.cumulative_engine_hours),
        "rolling_mean_temp": float(reading.rolling_mean_temp),
        "rolling_std_temp": float(reading.rolling_std_temp),
        "rolling_slope_oil_pressure": float(reading.rolling_slope_oil_pressure),
        "harsh_acceleration_count": int(reading.harsh_acceleration_count),
        "idle_time_ratio": float(reading.idle_time_ratio),
        "degradation_index": float(reading.degradation_index),
        "health_score": float(reading.health_score),
    }


def telemetry_ingestor_node(state: AgentState) -> AgentState:
    """Ingest telemetry into DB or load an existing reading, then normalize for ML."""
    from app.services import TelemetryService, VehicleService
    
    with SessionLocal() as db:
        vehicle = VehicleService.get_vehicle(db, state["vehicle_id"])
        if not vehicle:
            raise ValueError(f"Vehicle {state['vehicle_id']} not found")

        reading = None
        if "telemetry_payload" in state:
            payload = dict(state["telemetry_payload"])
            payload.setdefault("vehicle_id", state["vehicle_id"])
            telemetry_create = TelemetryReadingCreate(**payload)
            reading = TelemetryService.create_reading(db, telemetry_create)
        elif "telemetry_reading_id" in state:
            reading = TelemetryService.get_reading_by_id(db, int(state["telemetry_reading_id"]))
            if reading is None:
                raise ValueError(f"Telemetry reading {state['telemetry_reading_id']} not found")
            if reading.vehicle_id != state["vehicle_id"]:
                raise ValueError("Telemetry reading does not belong to the vehicle in state")
        else:
            raise ValueError("Provide either telemetry_payload or telemetry_reading_id in agent state")

    assert reading is not None
    next_state = {
        **state,
        "telemetry_reading_id": int(reading.id),
        "telemetry_row": _to_feature_row(reading),
    }
    return cast(AgentState, next_state)
