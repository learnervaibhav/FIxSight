"""Model package exports."""

from app.models.alert_log import AlertLog
from app.models.fault_prediction import FaultPrediction
from app.models.rul_prediction import RULPrediction
from app.models.service_center import ServiceCenter
from app.models.service_slot import ServiceSlot
from app.models.telemetry_reading import TelemetryReading
from app.models.user import User
from app.models.vehicle import Vehicle

__all__ = [
    "AlertLog",
    "FaultPrediction",
    "RULPrediction",
    "ServiceCenter",
    "ServiceSlot",
    "TelemetryReading",
    "User",
    "Vehicle",
]
