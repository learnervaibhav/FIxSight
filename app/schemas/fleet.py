"""Pydantic schemas for fleet, prediction, alert, event and simulation endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LatestReading(BaseModel):
    id: int
    timestamp: datetime
    engine_rpm: float | None
    coolant_temperature: float | None
    oil_pressure: float | None
    battery_voltage: float | None
    transmission_temperature: float | None
    vehicle_speed: float | None
    health_score: float | None
    degradation_index: float | None


class FaultPredictionResponse(BaseModel):
    id: int
    vehicle_id: str
    telemetry_reading_id: int | None
    fault_label: str
    fault_probability: float
    severity: str
    llm_explanation: str | None
    maintenance_priority: str
    recommended_service_window_hours: int
    created_at: datetime


class FaultPredictionListResponse(BaseModel):
    predictions: list[FaultPredictionResponse]
    total: int


class RULPoint(BaseModel):
    id: int
    rul_hours: float
    confidence_score: float | None
    created_at: datetime


class VehiclePredictionsResponse(BaseModel):
    vehicle_id: str
    faults: list[FaultPredictionResponse]
    rul: list[RULPoint]


class SlotSummary(BaseModel):
    slot_id: str
    vehicle_id: str
    center_id: str
    center_name: str | None
    center_latitude: float | None
    center_longitude: float | None
    scheduled_time: datetime
    duration_hours: float
    slot_status: str
    reason: str | None
    completed_at: datetime | None
    created_at: datetime | None


class SlotSummaryListResponse(BaseModel):
    slots: list[SlotSummary]
    total: int


class VehicleOverview(BaseModel):
    vehicle_id: str
    engine_type: str
    driving_profile: str
    manufacture_year: int
    region: str
    location: str
    owner_name: str | None
    owner_phone: str | None
    latitude: float | None
    longitude: float | None
    health_status: Literal["healthy", "warning", "critical", "unknown"]
    service_status: Literal["none", "scheduled", "in_service"]
    latest_reading: LatestReading | None
    latest_fault: FaultPredictionResponse | None
    rul_hours: float | None
    open_slot: SlotSummary | None


class FleetSummary(BaseModel):
    total_vehicles: int
    healthy: int
    warning: int
    critical: int
    scheduled: int
    in_service: int
    service_centers: int
    total_capacity: int
    occupied_bays: int
    alerts_total: int
    average_health: float | None


class FleetOverviewResponse(BaseModel):
    summary: FleetSummary
    vehicles: list[VehicleOverview]


class AlertLogResponse(BaseModel):
    id: int
    vehicle_id: str
    fault_prediction_id: int | None
    alert_type: str
    channel: str
    recipient: str | None
    status: str
    alert_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertLogListResponse(BaseModel):
    alerts: list[AlertLogResponse]
    total: int


class EventResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    severity: str
    vehicle_id: str | None
    created_at: str
    data: dict[str, Any]


class EventListResponse(BaseModel):
    events: list[EventResponse]
    last_id: int


class SimulationStartRequest(BaseModel):
    mode: Literal["mock", "real"] = "mock"
    tick_seconds: float = Field(3.0, ge=0.5, le=60)
    sim_minutes_per_tick: int = Field(20, ge=1, le=240)
    vehicles_per_tick: int = Field(5, ge=1, le=100)
    fault_rate: float = Field(0.04, ge=0, le=1)
    use_llm: bool = True
    seed: int | None = None
