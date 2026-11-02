"""Service scheduling endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.events import event_bus
from app.models import ServiceCenter, ServiceSlot
from app.schemas import (
    ServiceCenterListResponse,
    ServiceCenterOccupancyResponse,
    ServiceCenterResponse,
    ServiceSlotCreate,
    ServiceSlotListResponse,
    ServiceSlotResponse,
    ServiceSlotStatusUpdate,
    SlotSummary,
    SlotSummaryListResponse,
)
from app.services import FleetService
from app.services.service_scheduling_service import ServiceSchedulingService

router = APIRouter(prefix="/service", tags=["service"])


def _center_response(center: ServiceCenter, distance_km: float | None = None) -> ServiceCenterResponse:
    return ServiceCenterResponse(
        center_id=center.center_id,
        center_name=center.center_name,
        location=center.location,
        latitude=center.latitude,
        longitude=center.longitude,
        operating_hours_start=center.operating_hours_start,
        operating_hours_end=center.operating_hours_end,
        max_capacity=center.max_capacity,
        current_occupancy=center.current_occupancy,
        available_slots=max(0, center.max_capacity - center.current_occupancy),
        distance_km=round(distance_km, 2) if distance_km is not None else None,
        created_at=center.created_at,
        updated_at=center.updated_at,
    )


@router.get("/centers", response_model=ServiceCenterListResponse)
def list_service_centers(db: Session = Depends(get_db)) -> ServiceCenterListResponse:
    """List service centers with live occupancy."""
    centers = db.query(ServiceCenter).order_by(ServiceCenter.center_name.asc()).all()
    return ServiceCenterListResponse(centers=[_center_response(center) for center in centers], total=len(centers))


@router.get("/centers/nearby", response_model=ServiceCenterListResponse)
def nearby_service_centers(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0, le=500),
    only_available: bool = False,
    db: Session = Depends(get_db),
) -> ServiceCenterListResponse:
    """Centers within `radius_km`, nearest first."""
    ranked = [
        (center, distance)
        for center, distance in ServiceSchedulingService.centers_by_distance(db, latitude, longitude)
        if distance <= radius_km and (not only_available or center.current_occupancy < center.max_capacity)
    ]
    return ServiceCenterListResponse(
        centers=[_center_response(center, distance) for center, distance in ranked],
        total=len(ranked),
    )


@router.get("/centers/{center_id}/occupancy", response_model=ServiceCenterOccupancyResponse)
def center_occupancy(center_id: str, db: Session = Depends(get_db)) -> ServiceCenterOccupancyResponse:
    center = db.get(ServiceCenter, center_id)
    if center is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service center not found")
    counts = dict(
        db.query(ServiceSlot.slot_status, func.count(ServiceSlot.slot_id))
        .filter(ServiceSlot.center_id == center_id)
        .group_by(ServiceSlot.slot_status)
        .all()
    )
    return ServiceCenterOccupancyResponse(
        center_id=center.center_id,
        center_name=center.center_name,
        location=center.location,
        latitude=center.latitude,
        longitude=center.longitude,
        current_occupancy=center.current_occupancy,
        max_capacity=center.max_capacity,
        available_slots=max(0, center.max_capacity - center.current_occupancy),
        pending_slots=int(counts.get("PENDING", 0)),
        active_slots=int(counts.get("ACTIVE", 0)),
    )


@router.post("/schedule", response_model=ServiceSlotResponse, status_code=status.HTTP_201_CREATED)
def schedule_service(payload: ServiceSlotCreate, db: Session = Depends(get_db)) -> ServiceSlotResponse:
    """Create a service slot for a vehicle at a selected center."""
    try:
        slot = ServiceSchedulingService.create_service_slot(
            db=db,
            vehicle_id=payload.vehicle_id,
            center_id=payload.center_id,
            scheduled_time=payload.scheduled_time,
            duration_hours=payload.duration_hours,
            slot_status=payload.slot_status,
            reason=payload.reason or "Manual booking",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    event_bus.publish(
        "service_booked",
        "Service booked",
        f"{slot.vehicle_id} booked at {slot.service_center.center_name} for {slot.scheduled_time:%Y-%m-%d %H:%M}",
        severity="success",
        vehicle_id=slot.vehicle_id,
        data={"slot_id": slot.slot_id, "center_id": slot.center_id},
    )
    return ServiceSlotResponse.model_validate(slot)


@router.get("/schedule/{vehicle_id}", response_model=ServiceSlotListResponse)
def get_vehicle_slots(vehicle_id: str, db: Session = Depends(get_db)) -> ServiceSlotListResponse:
    """List scheduled slots for a vehicle."""
    slots = (
        db.query(ServiceSlot)
        .filter(ServiceSlot.vehicle_id == vehicle_id)
        .order_by(ServiceSlot.scheduled_time.desc())
        .all()
    )
    return ServiceSlotListResponse(slots=[ServiceSlotResponse.model_validate(slot) for slot in slots], total=len(slots))


@router.get("/slots", response_model=SlotSummaryListResponse)
def list_slots(
    slot_status: str | None = Query(None, description="Comma-separated, e.g. PENDING,ACTIVE"),
    center_id: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> SlotSummaryListResponse:
    """All service slots (newest first) with center details."""
    query = db.query(ServiceSlot)
    if slot_status:
        query = query.filter(ServiceSlot.slot_status.in_([s.strip().upper() for s in slot_status.split(",")]))
    if center_id:
        query = query.filter(ServiceSlot.center_id == center_id)
    total = query.count()
    slots = query.order_by(ServiceSlot.created_at.desc(), ServiceSlot.scheduled_time.desc()).limit(limit).all()
    return SlotSummaryListResponse(slots=[SlotSummary(**FleetService.slot_to_dict(slot)) for slot in slots], total=total)


@router.patch("/slots/{slot_id}", response_model=ServiceSlotResponse)
def update_slot(slot_id: str, payload: ServiceSlotStatusUpdate, db: Session = Depends(get_db)) -> ServiceSlotResponse:
    """Start, complete or cancel a slot; occupancy is recomputed."""
    try:
        slot = ServiceSchedulingService.update_slot_status(db, slot_id, payload.slot_status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    event_bus.publish(
        f"service_{payload.slot_status.lower()}",
        f"Service {payload.slot_status.lower()}",
        f"{slot.vehicle_id} at {slot.service_center.center_name}",
        severity="success" if payload.slot_status == "COMPLETED" else "info",
        vehicle_id=slot.vehicle_id,
        data={"slot_id": slot.slot_id},
    )
    return ServiceSlotResponse.model_validate(slot)

