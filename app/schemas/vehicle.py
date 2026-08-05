"""Pydantic schemas for vehicle endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class VehicleCreate(BaseModel):
    """Schema for creating a new vehicle."""

    vehicle_id: str = Field(..., min_length=1, max_length=16)
    user_id: str = Field(..., min_length=1, max_length=36)
    location: str = Field(..., min_length=1, max_length=256)
    manufacture_year: int
    initial_odometer: int
    engine_type: str
    driving_profile: str
    region: str
    average_daily_distance: float


class VehicleResponse(VehicleCreate):
    """Schema for vehicle response."""

    class Config:
        from_attributes = True


class VehicleListResponse(BaseModel):
    """List of vehicles."""

    vehicles: list[VehicleResponse]
    total: int
