"""Service scheduling helpers for creating slots and selecting centers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import ServiceCenter, ServiceSlot, Vehicle


class ServiceSchedulingService:
    """Create and manage service scheduling for vehicles."""

    @staticmethod
    def get_vehicle(db: Session, vehicle_id: str) -> Vehicle | None:
        return db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()

    @staticmethod
    def get_available_center(db: Session, vehicle_id: str) -> ServiceCenter | None:
        vehicle = ServiceSchedulingService.get_vehicle(db, vehicle_id)
        if not vehicle:
            return None

        return (
            db.query(ServiceCenter)
            .filter(ServiceCenter.current_occupancy < ServiceCenter.max_capacity)
            .order_by(ServiceCenter.current_occupancy.asc(), ServiceCenter.center_name.asc())
            .first()
        )

    @staticmethod
    def create_service_slot(
        db: Session,
        *,
        vehicle_id: str,
        center_id: str,
        scheduled_time: datetime,
        duration_hours: float = 2.0,
        slot_status: str = "PENDING",
    ) -> ServiceSlot:
        vehicle = ServiceSchedulingService.get_vehicle(db, vehicle_id)
        if not vehicle:
            raise ValueError(f"Vehicle {vehicle_id} not found")

        center = db.query(ServiceCenter).filter(ServiceCenter.center_id == center_id).first()
        if not center:
            raise ValueError(f"Service center {center_id} not found")

        if center.current_occupancy >= center.max_capacity:
            raise ValueError(f"Service center {center_id} is at capacity")

        slot = ServiceSlot(
            slot_id=str(uuid4()),
            center_id=center.center_id,
            vehicle_id=vehicle.vehicle_id,
            scheduled_time=scheduled_time,
            duration_hours=duration_hours,
            slot_status=slot_status,
        )
        db.add(slot)
        center.current_occupancy += 1
        db.commit()
        db.refresh(slot)
        return slot

    @staticmethod
    def create_slot_for_vehicle(
        db: Session,
        *,
        vehicle_id: str,
        preferred_time: datetime | None = None,
        duration_hours: float = 2.0,
        center_id: str | None = None,
        slot_status: str = "PENDING",
    ) -> dict[str, Any]:
        if preferred_time is None:
            preferred_time = datetime.utcnow()

        selected_center = None
        if center_id:
            selected_center = db.query(ServiceCenter).filter(ServiceCenter.center_id == center_id).first()
        else:
            selected_center = ServiceSchedulingService.get_available_center(db, vehicle_id)

        if not selected_center:
            raise ValueError("No available service center found")

        slot = ServiceSchedulingService.create_service_slot(
            db,
            vehicle_id=vehicle_id,
            center_id=selected_center.center_id,
            scheduled_time=preferred_time,
            duration_hours=duration_hours,
            slot_status=slot_status,
        )

        return {
            "slot_id": slot.slot_id,
            "vehicle_id": slot.vehicle_id,
            "center_id": slot.center_id,
            "scheduled_time": slot.scheduled_time.isoformat(),
            "duration_hours": slot.duration_hours,
            "slot_status": slot.slot_status,
        }
