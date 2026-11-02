"""Fleet overview, prediction history, alerts and users endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AlertLog, FaultPrediction, RULPrediction, User, Vehicle
from app.schemas import (
    AlertLogListResponse,
    AlertLogResponse,
    FaultPredictionListResponse,
    FaultPredictionResponse,
    FleetOverviewResponse,
    RULPoint,
    UserListResponse,
    UserResponse,
    VehiclePredictionsResponse,
)
from app.services import FleetService

router = APIRouter(tags=["fleet"])


@router.get("/fleet/overview", response_model=FleetOverviewResponse)
def fleet_overview(db: Session = Depends(get_db)) -> FleetOverviewResponse:
    """Latest health, predictions, RUL and service state for every vehicle."""
    return FleetOverviewResponse(**FleetService.overview(db))


@router.get("/predictions/faults", response_model=FaultPredictionListResponse)
def recent_faults(
    vehicle_id: str | None = None,
    severity: str | None = Query(None, description="Comma-separated, e.g. HIGH,MEDIUM"),
    include_normal: bool = False,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> FaultPredictionListResponse:
    """Fleet-wide fault predictions, newest first."""
    query = db.query(FaultPrediction)
    if vehicle_id:
        query = query.filter(FaultPrediction.vehicle_id == vehicle_id)
    if severity:
        query = query.filter(FaultPrediction.severity.in_([s.strip().upper() for s in severity.split(",")]))
    if not include_normal:
        query = query.filter(FaultPrediction.fault_label != "normal")
    total = query.count()
    rows = query.order_by(FaultPrediction.id.desc()).limit(limit).all()
    return FaultPredictionListResponse(
        predictions=[FaultPredictionResponse(**FleetService.fault_to_dict(row)) for row in rows],
        total=total,
    )


@router.get("/vehicles/{vehicle_id}/predictions", response_model=VehiclePredictionsResponse)
def vehicle_predictions(
    vehicle_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> VehiclePredictionsResponse:
    """Fault and RUL history for one vehicle (newest first)."""
    if db.get(Vehicle, vehicle_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    faults = (
        db.query(FaultPrediction)
        .filter(FaultPrediction.vehicle_id == vehicle_id)
        .order_by(FaultPrediction.id.desc())
        .limit(limit)
        .all()
    )
    ruls = (
        db.query(RULPrediction)
        .filter(RULPrediction.vehicle_id == vehicle_id)
        .order_by(RULPrediction.created_at.desc(), RULPrediction.id.desc())
        .limit(limit)
        .all()
    )
    return VehiclePredictionsResponse(
        vehicle_id=vehicle_id,
        faults=[FaultPredictionResponse(**FleetService.fault_to_dict(row)) for row in faults],
        rul=[
            RULPoint(
                id=row.id,
                rul_hours=float(row.rul_hours),
                confidence_score=float(row.confidence_score) if row.confidence_score is not None else None,
                created_at=row.created_at,
            )
            for row in ruls
        ],
    )


@router.get("/alerts", response_model=AlertLogListResponse)
def list_alerts(
    vehicle_id: str | None = None,
    alert_type: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> AlertLogListResponse:
    """Alert / notification log, newest first."""
    query = db.query(AlertLog)
    if vehicle_id:
        query = query.filter(AlertLog.vehicle_id == vehicle_id)
    if alert_type:
        query = query.filter(AlertLog.alert_type == alert_type)
    total = query.count()
    rows = query.order_by(AlertLog.id.desc()).limit(limit).all()
    return AlertLogListResponse(alerts=[AlertLogResponse.model_validate(row) for row in rows], total=total)


@router.get("/alerts/{vehicle_id}", response_model=AlertLogListResponse)
def vehicle_alerts(vehicle_id: str, limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)) -> AlertLogListResponse:
    return list_alerts(vehicle_id=vehicle_id, alert_type=None, limit=limit, db=db)


@router.get("/users", response_model=UserListResponse)
def list_users(db: Session = Depends(get_db)) -> UserListResponse:
    users = db.query(User).order_by(User.name).all()
    return UserListResponse(users=[UserResponse.model_validate(user) for user in users], total=len(users))


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)) -> UserResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)
