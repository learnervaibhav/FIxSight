"""Service scheduling endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ServiceCenter, ServiceSlot
from app.schemas import (
    ServiceCenterListResponse,
    ServiceCenterResponse,
    ServiceSlotCreate,
    ServiceSlotListResponse,
    ServiceSlotResponse,
)
from app.services.service_scheduling_service import ServiceSchedulingService

router = APIRouter(prefix="/service", tags=["service"])


@router.get("/centers", response_model=ServiceCenterListResponse)
def list_service_centers(db: Session = Depends(get_db)) -> ServiceCenterListResponse:
    """List available service centers for frontend scheduling."""
    centers = (
        db.query(ServiceCenter)
        .order_by(ServiceCenter.current_occupancy.asc(), ServiceCenter.center_name.asc())
        .all()
    )
    return ServiceCenterListResponse(
        centers=[
            ServiceCenterResponse(
                center_id=center.center_id,
                center_name=center.center_name,
                location=center.location,
                latitude=center.latitude,
                longitude=center.longitude,
                operating_hours_start=center.operating_hours_start,
                operating_hours_end=center.operating_hours_end,
                max_capacity=center.max_capacity,
                current_occupancy=center.current_occupancy,
                created_at=center.created_at,
                updated_at=center.updated_at,
            )
            for center in centers
        ],
        total=len(centers),
    )


@router.post("/schedule", response_model=ServiceSlotResponse, status_code=status.HTTP_201_CREATED)
def schedule_service(
    payload: ServiceSlotCreate,
    db: Session = Depends(get_db),
) -> ServiceSlotResponse:
    """Create a service slot for a vehicle at a selected center."""
    try:
        slot = ServiceSchedulingService.create_service_slot(
            db=db,
            vehicle_id=payload.vehicle_id,
            center_id=payload.center_id,
            scheduled_time=payload.scheduled_time,
            duration_hours=payload.duration_hours,
            slot_status=payload.slot_status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ServiceSlotResponse(
        slot_id=slot.slot_id,
        center_id=slot.center_id,
        vehicle_id=slot.vehicle_id,
        scheduled_time=slot.scheduled_time,
        duration_hours=slot.duration_hours,
        slot_status=slot.slot_status,
        scheduled_at=slot.scheduled_at,
        completed_at=slot.completed_at,
        created_at=slot.created_at,
        updated_at=slot.updated_at,
    )


@router.get("/schedule/{vehicle_id}", response_model=ServiceSlotListResponse)
def get_vehicle_slots(vehicle_id: str, db: Session = Depends(get_db)) -> ServiceSlotListResponse:
    """List scheduled slots for a vehicle."""
    slots = (
        db.query(ServiceSlot)
        .filter(ServiceSlot.vehicle_id == vehicle_id)
        .order_by(ServiceSlot.scheduled_time.asc())
        .all()
    )
    return ServiceSlotListResponse(slots=[ServiceSlotResponse(
        slot_id=slot.slot_id,
        center_id=slot.center_id,
        vehicle_id=slot.vehicle_id,
        scheduled_time=slot.scheduled_time,
        duration_hours=slot.duration_hours,
        slot_status=slot.slot_status,
        scheduled_at=slot.scheduled_at,
        completed_at=slot.completed_at,
        created_at=slot.created_at,
        updated_at=slot.updated_at,
    ) for slot in slots], total=len(slots))
