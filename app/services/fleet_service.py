"""Fleet-wide read models for the dashboard and map."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.nodes.maintenance_advisor import priority_from_severity, service_window_hours
from app.models import AlertLog, FaultPrediction, RULPrediction, ServiceCenter, ServiceSlot, TelemetryReading, User, Vehicle
from app.models.service_slot import OPEN_SLOT_STATUSES

HEALTH_STATUS_BY_SEVERITY = {"HIGH": "critical", "MEDIUM": "warning", "LOW": "healthy"}


def _float(value: Any) -> float | None:
    return float(value) if value is not None else None


class FleetService:
    """Aggregate latest telemetry, predictions and service state per vehicle."""

    @staticmethod
    def latest_reading(db: Session, vehicle_id: str) -> TelemetryReading | None:
        return (
            db.query(TelemetryReading)
            .filter(TelemetryReading.vehicle_id == vehicle_id)
            .order_by(TelemetryReading.timestamp.desc())
            .first()
        )

    @staticmethod
    def latest_fault(db: Session, vehicle_id: str) -> FaultPrediction | None:
        return (
            db.query(FaultPrediction)
            .filter(FaultPrediction.vehicle_id == vehicle_id)
            .order_by(FaultPrediction.id.desc())
            .first()
        )

    @staticmethod
    def latest_rul(db: Session, vehicle_id: str) -> RULPrediction | None:
        return (
            db.query(RULPrediction)
            .filter(RULPrediction.vehicle_id == vehicle_id)
            .order_by(RULPrediction.created_at.desc(), RULPrediction.id.desc())
            .first()
        )

    @staticmethod
    def fault_to_dict(fault: FaultPrediction) -> dict[str, Any]:
        severity = fault.severity or "LOW"
        probability = float(fault.fault_probability)
        return {
            "id": fault.id,
            "vehicle_id": fault.vehicle_id,
            "telemetry_reading_id": fault.telemetry_reading_id,
            "fault_label": fault.fault_label,
            "fault_probability": probability,
            "severity": severity,
            "llm_explanation": fault.llm_explanation,
            "maintenance_priority": priority_from_severity(severity),
            "recommended_service_window_hours": service_window_hours(severity, probability),
            "created_at": fault.created_at,
        }

    @staticmethod
    def slot_to_dict(slot: ServiceSlot) -> dict[str, Any]:
        center = slot.service_center
        return {
            "slot_id": slot.slot_id,
            "vehicle_id": slot.vehicle_id,
            "center_id": slot.center_id,
            "center_name": center.center_name if center else None,
            "center_latitude": center.latitude if center else None,
            "center_longitude": center.longitude if center else None,
            "scheduled_time": slot.scheduled_time,
            "duration_hours": float(slot.duration_hours),
            "slot_status": slot.slot_status,
            "reason": slot.reason,
            "completed_at": slot.completed_at,
            "created_at": slot.created_at,
        }

    @staticmethod
    def vehicle_overview(db: Session, vehicle: Vehicle, owner: User | None) -> dict[str, Any]:
        reading = FleetService.latest_reading(db, vehicle.vehicle_id)
        fault = FleetService.latest_fault(db, vehicle.vehicle_id)
        rul = FleetService.latest_rul(db, vehicle.vehicle_id)
        open_slot = (
            db.query(ServiceSlot)
            .filter(ServiceSlot.vehicle_id == vehicle.vehicle_id, ServiceSlot.slot_status.in_(OPEN_SLOT_STATUSES))
            .order_by(ServiceSlot.scheduled_time.asc())
            .first()
        )

        if fault is None:
            health_status = "unknown"
        elif fault.fault_label == "normal":
            health_status = "healthy"
        else:
            health_status = HEALTH_STATUS_BY_SEVERITY.get(fault.severity or "LOW", "healthy")

        service_status = "none"
        if open_slot is not None:
            service_status = "in_service" if open_slot.slot_status == "ACTIVE" else "scheduled"

        return {
            "vehicle_id": vehicle.vehicle_id,
            "engine_type": vehicle.engine_type,
            "driving_profile": vehicle.driving_profile,
            "manufacture_year": vehicle.manufacture_year,
            "region": vehicle.region,
            "location": vehicle.location,
            "owner_name": owner.name if owner else None,
            "owner_phone": owner.phone if owner else None,
            "latitude": owner.latitude if owner else None,
            "longitude": owner.longitude if owner else None,
            "health_status": health_status,
            "service_status": service_status,
            "latest_reading": None
            if reading is None
            else {
                "id": reading.id,
                "timestamp": reading.timestamp,
                "engine_rpm": _float(reading.engine_rpm),
                "coolant_temperature": _float(reading.coolant_temperature),
                "oil_pressure": _float(reading.oil_pressure),
                "battery_voltage": _float(reading.battery_voltage),
                "transmission_temperature": _float(reading.transmission_temperature),
                "vehicle_speed": _float(reading.vehicle_speed),
                "health_score": _float(reading.health_score),
                "degradation_index": _float(reading.degradation_index),
            },
            "latest_fault": FleetService.fault_to_dict(fault) if fault else None,
            "rul_hours": _float(rul.rul_hours) if rul else None,
            "open_slot": FleetService.slot_to_dict(open_slot) if open_slot else None,
        }

    @staticmethod
    def overview(db: Session) -> dict[str, Any]:
        owners = {user.user_id: user for user in db.query(User).all()}
        vehicles = db.query(Vehicle).order_by(Vehicle.vehicle_id).all()
        items = [FleetService.vehicle_overview(db, vehicle, owners.get(vehicle.user_id)) for vehicle in vehicles]

        centers = db.query(ServiceCenter).order_by(ServiceCenter.center_name).all()
        summary = {
            "total_vehicles": len(items),
            "healthy": sum(1 for item in items if item["health_status"] in {"healthy", "unknown"}),
            "warning": sum(1 for item in items if item["health_status"] == "warning"),
            "critical": sum(1 for item in items if item["health_status"] == "critical"),
            "scheduled": sum(1 for item in items if item["service_status"] == "scheduled"),
            "in_service": sum(1 for item in items if item["service_status"] == "in_service"),
            "service_centers": len(centers),
            "total_capacity": sum(center.max_capacity for center in centers),
            "occupied_bays": sum(center.current_occupancy for center in centers),
            "alerts_total": db.query(AlertLog).count(),
        }
        health_scores = [
            item["latest_reading"]["health_score"]
            for item in items
            if item["latest_reading"] and item["latest_reading"]["health_score"] is not None
        ]
        summary["average_health"] = round(sum(health_scores) / len(health_scores), 1) if health_scores else None
        return {"summary": summary, "vehicles": items}
