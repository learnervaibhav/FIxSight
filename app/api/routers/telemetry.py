"""Telemetry routers."""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import TelemetryAnalyzeResponse, TelemetryBatchResponse, TelemetryReadingCreate, TelemetryReadingResponse
from app.services import MLService, TelemetryService, VehicleService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("", response_model=TelemetryReadingResponse, status_code=status.HTTP_201_CREATED)
def create_telemetry(reading: TelemetryReadingCreate, db: Session = Depends(get_db)) -> TelemetryReadingResponse:
    """Ingest a sensor reading."""
    # Verify vehicle exists
    vehicle = VehicleService.get_vehicle(db, reading.vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {reading.vehicle_id} not found",
        )
    return cast(TelemetryReadingResponse, TelemetryService.create_reading(db, reading))


@router.get("/{telemetry_id}", response_model=TelemetryReadingResponse)
def get_telemetry_reading(telemetry_id: int, db: Session = Depends(get_db)) -> TelemetryReadingResponse:
    """Fetch one telemetry reading by id."""
    reading = TelemetryService.get_reading_by_id(db, telemetry_id)
    if not reading:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telemetry reading not found")
    return cast(TelemetryReadingResponse, reading)


@router.get("/vehicles/{vehicle_id}", response_model=TelemetryBatchResponse)
def get_vehicle_telemetry(
    vehicle_id: str,
    hours: int | None = Query(None, ge=1, le=8760),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> TelemetryBatchResponse:
    """Fetch telemetry for a vehicle. If hours is omitted, returns latest rows across all history."""
    # Verify vehicle exists
    vehicle = VehicleService.get_vehicle(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    readings = TelemetryService.get_recent_readings(db, vehicle_id, hours, limit)
    total = TelemetryService.count_readings(db, vehicle_id, hours)
    return TelemetryBatchResponse(vehicle_id=vehicle_id, readings=cast(list[TelemetryReadingResponse], readings), total=total)


@router.post("/{telemetry_id}/analyze", response_model=TelemetryAnalyzeResponse)
def analyze_telemetry(
    telemetry_id: int,
    hours_elapsed: float = Query(1.0, gt=0.0, le=24.0),
    db: Session = Depends(get_db),
) -> TelemetryAnalyzeResponse:
    """Run fault + hourly RUL prediction for a telemetry row and persist outputs."""
    reading = TelemetryService.get_reading_by_id(db, telemetry_id)
    if not reading:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telemetry reading not found")

    row = {
        "engine_rpm": reading.engine_rpm,
        "engine_load": reading.engine_load,
        "coolant_temperature": reading.coolant_temperature,
        "oil_temperature": reading.oil_temperature,
        "oil_pressure": reading.oil_pressure,
        "fuel_rate": reading.fuel_rate,
        "short_term_fuel_trim": reading.short_term_fuel_trim,
        "long_term_fuel_trim": reading.long_term_fuel_trim,
        "mass_air_flow": reading.mass_air_flow,
        "intake_manifold_pressure": reading.intake_manifold_pressure,
        "battery_voltage": reading.battery_voltage,
        "alternator_voltage": reading.alternator_voltage,
        "gear_position": reading.gear_position,
        "transmission_temperature": reading.transmission_temperature,
        "o2_sensor_voltage": reading.o2_sensor_voltage,
        "egr_position": reading.egr_position,
        "vehicle_speed": reading.vehicle_speed,
        "throttle_position": reading.throttle_position,
        "cumulative_engine_hours": reading.cumulative_engine_hours,
        "rolling_mean_temp": reading.rolling_mean_temp,
        "rolling_std_temp": reading.rolling_std_temp,
        "rolling_slope_oil_pressure": reading.rolling_slope_oil_pressure,
        "harsh_acceleration_count": reading.harsh_acceleration_count,
        "idle_time_ratio": reading.idle_time_ratio,
        "degradation_index": reading.degradation_index,
        "health_score": reading.health_score,
    }

    previous_rul = MLService.get_latest_rul_hours(db, reading.vehicle_id)
    analysis = MLService.analyze(row, previous_rul_hours=previous_rul, hours_elapsed=hours_elapsed)

    fault = MLService.save_fault_prediction(
        db=db,
        vehicle_id=reading.vehicle_id,
        telemetry_reading_id=reading.id,
        fault_label=analysis["fault_label"],
        fault_probability=analysis["fault_probability"],
    )
    rul = MLService.save_rul_prediction(
        db=db,
        vehicle_id=reading.vehicle_id,
        telemetry_reading_id=reading.id,
        rul_hours=analysis["rul_hours"],
        rul_confidence=analysis["rul_confidence"],
    )

    return TelemetryAnalyzeResponse(
        telemetry_id=reading.id,
        vehicle_id=reading.vehicle_id,
        fault_label=fault.fault_label,
        fault_probability=float(fault.fault_probability),
        severity=str(fault.severity or "LOW"),
        rul_hours=float(rul.rul_hours),
        rul_confidence=float(rul.confidence_score or 0.0),
        wear_rate=float(analysis["wear_rate"]),
        update_interval_hours=float(analysis["update_interval_hours"]),
    )
