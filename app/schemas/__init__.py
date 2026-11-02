"""Schemas package."""

from app.schemas.fleet import (
    AlertLogListResponse,
    AlertLogResponse,
    EventListResponse,
    EventResponse,
    FaultPredictionListResponse,
    FaultPredictionResponse,
    FleetOverviewResponse,
    RULPoint,
    SimulationStartRequest,
    SlotSummary,
    SlotSummaryListResponse,
    VehicleOverview,
    VehiclePredictionsResponse,
)
from app.schemas.service import (
    ServiceCenterCreate,
    ServiceCenterListResponse,
    ServiceCenterOccupancyResponse,
    ServiceCenterResponse,
    ServiceSlotCreate,
    ServiceSlotListResponse,
    ServiceSlotResponse,
    ServiceSlotStatusUpdate,
)
from app.schemas.telemetry import TelemetryAnalyzeResponse, TelemetryBatchResponse, TelemetryReadingCreate, TelemetryReadingResponse
from app.schemas.user import UserCreate, UserListResponse, UserResponse
from app.schemas.vehicle import VehicleCreate, VehicleListResponse, VehicleResponse

__all__ = [
    "VehicleCreate",
    "VehicleResponse",
    "VehicleListResponse",
    "UserCreate",
    "UserResponse",
    "UserListResponse",
    "TelemetryReadingCreate",
    "TelemetryReadingResponse",
    "TelemetryBatchResponse",
    "TelemetryAnalyzeResponse",
    "ServiceCenterCreate",
    "ServiceCenterResponse",
    "ServiceCenterOccupancyResponse",
    "ServiceCenterListResponse",
    "ServiceSlotCreate",
    "ServiceSlotResponse",
    "ServiceSlotListResponse",
    "ServiceSlotStatusUpdate",
    "FleetOverviewResponse",
    "VehicleOverview",
    "FaultPredictionResponse",
    "FaultPredictionListResponse",
    "VehiclePredictionsResponse",
    "RULPoint",
    "SlotSummary",
    "SlotSummaryListResponse",
    "AlertLogResponse",
    "AlertLogListResponse",
    "EventResponse",
    "EventListResponse",
    "SimulationStartRequest",
]
