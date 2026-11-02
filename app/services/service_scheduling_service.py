"""Service scheduling helpers for creating slots and selecting centers."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ServiceCenter, ServiceSlot, User, Vehicle
from app.models.service_slot import OPEN_SLOT_STATUSES

EARTH_RADIUS_KM = 6371.0
DEFAULT_SEARCH_RADIUS_KM = 10.0
SLOT_STATUSES = ("PENDING", "ACTIVE", "COMPLETED", "CANCELLED")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two coordinates in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def next_opening(center: ServiceCenter, after: datetime, duration_hours: float) -> datetime:
    """Earliest whole-hour start >= `after` where the service fits inside operating hours."""
    start = after.replace(minute=0, second=0, microsecond=0)
    if start < after:
        start += timedelta(hours=1)

    for _ in range(24 * 8):
        fits = center.operating_hours_start <= start.hour and start.hour + duration_hours <= center.operating_hours_end
        if fits:
            return start
        if start.hour < center.operating_hours_start:
            start = start.replace(hour=center.operating_hours_start)
        else:
            start = (start + timedelta(days=1)).replace(hour=center.operating_hours_start)
    raise ValueError(f"Service center {center.center_id} cannot fit a {duration_hours}h service")


class ServiceSchedulingService:
    """Create and manage service scheduling for vehicles."""

    @staticmethod
    def get_vehicle(db: Session, vehicle_id: str) -> Vehicle | None:
        return db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()

    @staticmethod
    def vehicle_coordinates(db: Session, vehicle: Vehicle) -> tuple[float, float] | None:
        owner = db.get(User, vehicle.user_id)
        if owner is None:
            return None
        return float(owner.latitude), float(owner.longitude)

    @staticmethod
    def get_open_slot(db: Session, vehicle_id: str) -> ServiceSlot | None:
        return (
            db.query(ServiceSlot)
            .filter(ServiceSlot.vehicle_id == vehicle_id, ServiceSlot.slot_status.in_(OPEN_SLOT_STATUSES))
            .order_by(ServiceSlot.scheduled_time.asc())
            .first()
        )

    @staticmethod
    def centers_by_distance(db: Session, latitude: float, longitude: float) -> list[tuple[ServiceCenter, float]]:
        centers = db.query(ServiceCenter).all()
        ranked = [(center, haversine_km(latitude, longitude, center.latitude, center.longitude)) for center in centers]
        return sorted(ranked, key=lambda item: item[1])

    @staticmethod
    def get_available_center(
        db: Session,
        vehicle_id: str,
        radius_km: float = DEFAULT_SEARCH_RADIUS_KM,
    ) -> tuple[ServiceCenter, float] | None:
        """Nearest center with free capacity, preferring those within `radius_km`."""
        vehicle = ServiceSchedulingService.get_vehicle(db, vehicle_id)
        if not vehicle:
            return None

        coords = ServiceSchedulingService.vehicle_coordinates(db, vehicle)
        if coords is None:
            center = (
                db.query(ServiceCenter)
                .filter(ServiceCenter.current_occupancy < ServiceCenter.max_capacity)
                .order_by(ServiceCenter.current_occupancy.asc(), ServiceCenter.center_name.asc())
                .first()
            )
            return (center, 0.0) if center else None

        available = [
            (center, distance)
            for center, distance in ServiceSchedulingService.centers_by_distance(db, *coords)
            if center.current_occupancy < center.max_capacity
        ]
        if not available:
            return None
        within_radius = [item for item in available if item[1] <= radius_km]
        return (within_radius or available)[0]

    @staticmethod
    def recompute_occupancy(db: Session, center_id: str | None = None) -> None:
        """Set current_occupancy to the number of PENDING/ACTIVE slots (single source of truth)."""
        counts = dict(
            db.query(ServiceSlot.center_id, func.count(ServiceSlot.slot_id))
            .filter(ServiceSlot.slot_status.in_(OPEN_SLOT_STATUSES))
            .group_by(ServiceSlot.center_id)
            .all()
        )
        query = db.query(ServiceCenter)
        if center_id:
            query = query.filter(ServiceCenter.center_id == center_id)
        for center in query.all():
            center.current_occupancy = int(counts.get(center.center_id, 0))
        db.commit()

    @staticmethod
    def create_service_slot(
        db: Session,
        *,
        vehicle_id: str,
        center_id: str,
        scheduled_time: datetime | None = None,
        duration_hours: float = 2.0,
        slot_status: str = "PENDING",
        reason: str | None = None,
    ) -> ServiceSlot:
        vehicle = ServiceSchedulingService.get_vehicle(db, vehicle_id)
        if not vehicle:
            raise ValueError(f"Vehicle {vehicle_id} not found")

        center = db.query(ServiceCenter).filter(ServiceCenter.center_id == center_id).first()
        if not center:
            raise ValueError(f"Service center {center_id} not found")

        if center.current_occupancy >= center.max_capacity:
            raise ValueError(f"Service center {center.center_name} is at capacity")

        if slot_status not in SLOT_STATUSES:
            raise ValueError(f"Invalid slot status {slot_status}")

        if scheduled_time is None:
            scheduled_time = next_opening(center, datetime.now() + timedelta(hours=1), duration_hours)
        else:
            scheduled_time = scheduled_time.replace(tzinfo=None)
            if not (
                center.operating_hours_start <= scheduled_time.hour
                and scheduled_time.hour + duration_hours <= center.operating_hours_end
            ):
                raise ValueError(
                    f"{center.center_name} is open {center.operating_hours_start}:00-{center.operating_hours_end}:00; "
                    f"a {duration_hours}h service at {scheduled_time:%H:%M} does not fit"
                )

        slot = ServiceSlot(
            slot_id=str(uuid4()),
            center_id=center.center_id,
            vehicle_id=vehicle.vehicle_id,
            scheduled_time=scheduled_time,
            duration_hours=duration_hours,
            slot_status=slot_status,
            reason=reason,
        )
        db.add(slot)
        db.commit()
        ServiceSchedulingService.recompute_occupancy(db, center.center_id)
        db.refresh(slot)
        return slot

    @staticmethod
    def update_slot_status(db: Session, slot_id: str, slot_status: str, at: datetime | None = None) -> ServiceSlot:
        slot = db.get(ServiceSlot, slot_id)
        if slot is None:
            raise ValueError(f"Service slot {slot_id} not found")
        if slot_status not in SLOT_STATUSES:
            raise ValueError(f"Invalid slot status {slot_status}")
        if slot.slot_status in {"COMPLETED", "CANCELLED"}:
            raise ValueError(f"Slot is already {slot.slot_status}")

        slot.slot_status = slot_status
        if slot_status == "COMPLETED":
            slot.completed_at = at or datetime.now()
        db.commit()
        ServiceSchedulingService.recompute_occupancy(db, slot.center_id)
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
        reason: str | None = None,
        radius_km: float = DEFAULT_SEARCH_RADIUS_KM,
    ) -> dict[str, Any]:
        """Book the nearest available center at its next opening after `preferred_time`."""
        if preferred_time is None:
            preferred_time = datetime.now()
        preferred_time = preferred_time.replace(tzinfo=None)

        distance_km = 0.0
        if center_id:
            selected_center = db.query(ServiceCenter).filter(ServiceCenter.center_id == center_id).first()
        else:
            found = ServiceSchedulingService.get_available_center(db, vehicle_id, radius_km=radius_km)
            selected_center, distance_km = found if found else (None, 0.0)

        if not selected_center:
            raise ValueError("No available service center found")

        slot = ServiceSchedulingService.create_service_slot(
            db,
            vehicle_id=vehicle_id,
            center_id=selected_center.center_id,
            scheduled_time=next_opening(selected_center, preferred_time, duration_hours),
            duration_hours=duration_hours,
            slot_status=slot_status,
            reason=reason,
        )

        return {
            "slot_id": slot.slot_id,
            "vehicle_id": slot.vehicle_id,
            "center_id": slot.center_id,
            "center_name": selected_center.center_name,
            "location": selected_center.location,
            "latitude": selected_center.latitude,
            "longitude": selected_center.longitude,
            "distance_km": round(distance_km, 2),
            "scheduled_time": slot.scheduled_time.isoformat(),
            "duration_hours": slot.duration_hours,
            "slot_status": slot.slot_status,
        }
