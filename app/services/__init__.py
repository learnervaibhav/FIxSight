"""Services package."""

try:
    from app.services.ml_services import MLService
except Exception:  # pragma: no cover - optional dependency guard
    MLService = None  # type: ignore[assignment]

from app.services.service_scheduling_service import ServiceSchedulingService
from app.services.telemetry_service import TelemetryService
from app.services.vehicle_service import VehicleService

__all__ = ["VehicleService", "TelemetryService", "MLService", "ServiceSchedulingService"]
