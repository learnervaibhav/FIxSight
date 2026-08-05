"""Pydantic schemas for telemetry endpoints."""

from datetime import datetime

from pydantic import BaseModel


class TelemetryReadingCreate(BaseModel):
    """Schema for creating a telemetry reading."""

    vehicle_id: str
    timestamp: datetime
    engine_rpm: float
    engine_load: float
    coolant_temperature: float
    oil_temperature: float
    oil_pressure: float
    fuel_rate: float
    short_term_fuel_trim: float
    long_term_fuel_trim: float
    mass_air_flow: float
    intake_manifold_pressure: float
    battery_voltage: float
    alternator_voltage: float
    gear_position: int
    transmission_temperature: float
    o2_sensor_voltage: float
    egr_position: float
    vehicle_speed: float
    throttle_position: float
    cumulative_engine_hours: float
    rolling_mean_temp: float
    rolling_std_temp: float
    rolling_slope_oil_pressure: float
    harsh_acceleration_count: int
    idle_time_ratio: float
    degradation_index: float
    health_score: float
    rul_hours: float


class TelemetryReadingResponse(TelemetryReadingCreate):
    """Schema for telemetry reading response."""

    id: int

    class Config:
        from_attributes = True              # When we deal with sqlAlchemy kind of orms it will give output as dict but pydantic not clearly 
                                            # dealt with dict kind of things so it will convert to object and attribute so pydantic will access it easily 


class TelemetryBatchResponse(BaseModel):
    """Response for batch telemetry retrieval."""

    vehicle_id: str
    readings: list[TelemetryReadingResponse]
    total: int


class TelemetryAnalyzeResponse(BaseModel):
    """Response for telemetry ML analysis."""

    telemetry_id: int
    vehicle_id: str
    fault_label: str
    fault_probability: float
    severity: str
    rul_hours: float
    rul_confidence: float
    wear_rate: float
    update_interval_hours: float
