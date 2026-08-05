"""Vehicle routers."""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import TelemetryBatchResponse, TelemetryReadingResponse, VehicleCreate, VehicleListResponse, VehicleResponse
from app.services import TelemetryService, VehicleService

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(vehicle: VehicleCreate, db: Session = Depends(get_db)) -> VehicleResponse:
    """Register a new vehicle."""
    existing = VehicleService.get_vehicle(db, vehicle.vehicle_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Vehicle {vehicle.vehicle_id} already exists",
        )
    return cast(VehicleResponse, VehicleService.create_vehicle(db, vehicle))


@router.get("", response_model=VehicleListResponse)
def list_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> VehicleListResponse:
    """List all vehicles."""
    vehicles, total = VehicleService.list_vehicles(db, skip, limit)
    return VehicleListResponse(vehicles=cast(list[VehicleResponse], vehicles), total=total)


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: str, db: Session = Depends(get_db)) -> VehicleResponse:
    """Get vehicle by ID."""
    vehicle = VehicleService.get_vehicle(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return cast(VehicleResponse, vehicle)


@router.get("/{vehicle_id}/telemetry", response_model=TelemetryBatchResponse)
def get_vehicle_telemetry(
    vehicle_id: str,
    hours: int | None = Query(None, ge=1, le=8760),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> TelemetryBatchResponse:
    """Compatibility endpoint matching documented API path."""
    vehicle = VehicleService.get_vehicle(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    readings = TelemetryService.get_recent_readings(db, vehicle_id, hours, limit)
    total = TelemetryService.count_readings(db, vehicle_id, hours)
    return TelemetryBatchResponse(vehicle_id=vehicle_id, readings=cast(list[TelemetryReadingResponse], readings), total=total)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: str, db: Session = Depends(get_db)) -> None:
    """Delete a vehicle."""
    if not VehicleService.delete_vehicle(db, vehicle_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
