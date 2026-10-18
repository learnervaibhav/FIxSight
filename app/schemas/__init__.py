"""Schemas package."""

from app.schemas.service import (
    ServiceCenterCreate,
    ServiceCenterListResponse,
    ServiceCenterOccupancyResponse,
    ServiceCenterResponse,
    ServiceSlotCreate,
    ServiceSlotListResponse,
    ServiceSlotResponse,
)
from app.schemas.telemetry import TelemetryAnalyzeResponse, TelemetryBatchResponse, TelemetryReadingCreate, TelemetryReadingResponse
from app.schemas.vehicle import VehicleCreate, VehicleListResponse, VehicleResponse

__all__ = [
    "VehicleCreate",
    "VehicleResponse",
    "VehicleListResponse",
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
]
