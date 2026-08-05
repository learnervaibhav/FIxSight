"""Pydantic schemas for service center and slot endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class ServiceCenterCreate(BaseModel):
    """Schema for creating a new service center."""

    center_id: str = Field(..., min_length=1, max_length=36)
    center_name: str = Field(..., min_length=1, max_length=256)
    location: str = Field(..., min_length=1, max_length=256)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    operating_hours_start: int = Field(..., ge=0, le=23)
    operating_hours_end: int = Field(..., ge=0, le=23)
    max_capacity: int = Field(..., gt=0)


class ServiceCenterResponse(ServiceCenterCreate):
    """Schema for service center response."""

    current_occupancy: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceCenterOccupancyResponse(BaseModel):
    """Schema for service center occupancy info."""

    center_id: str
    center_name: str
    location: str
    latitude: float
    longitude: float
    current_occupancy: int
    max_capacity: int
    available_slots: int

    class Config:
        from_attributes = True


class ServiceSlotCreate(BaseModel):
    """Schema for creating a new service slot."""

    slot_id: str = Field(..., min_length=1, max_length=36)
    center_id: str = Field(..., min_length=1, max_length=36)
    vehicle_id: str = Field(..., min_length=1, max_length=16)
    scheduled_time: datetime
    duration_hours: float = Field(..., gt=0)
    slot_status: str = Field(default="PENDING")


class ServiceSlotResponse(ServiceSlotCreate):
    """Schema for service slot response."""

    scheduled_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServiceSlotListResponse(BaseModel):
    """List of service slots."""

    slots: list[ServiceSlotResponse]
    total: int


class ServiceCenterListResponse(BaseModel):
    """List of service centers."""

    centers: list[ServiceCenterResponse]
    total: int
