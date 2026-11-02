"""Pydantic schemas for service center and slot endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ServiceCenterCreate(BaseModel):
    """Schema for creating a new service center."""

    center_id: str = Field(..., min_length=1, max_length=36)
    center_name: str = Field(..., min_length=1, max_length=256)
    location: str = Field(..., min_length=1, max_length=256)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    operating_hours_start: int = Field(..., ge=0, le=23)
    operating_hours_end: int = Field(..., ge=0, le=24)
    max_capacity: int = Field(..., gt=0)


class ServiceCenterResponse(ServiceCenterCreate):
    """Schema for service center response."""

    current_occupancy: int
    available_slots: int = 0
    distance_km: float | None = None
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
    pending_slots: int = 0
    active_slots: int = 0

    class Config:
        from_attributes = True


class ServiceSlotCreate(BaseModel):
    """Schema for creating a new service slot.

    `slot_id` is ignored (server generates a UUID). When `scheduled_time` is omitted
    the center's next opening is used.
    """

    slot_id: str | None = Field(default=None, max_length=36)
    center_id: str = Field(..., min_length=1, max_length=36)
    vehicle_id: str = Field(..., min_length=1, max_length=16)
    scheduled_time: datetime | None = None
    duration_hours: float = Field(2.0, gt=0, le=12)
    slot_status: str = Field(default="PENDING")
    reason: str | None = Field(default=None, max_length=128)


class ServiceSlotStatusUpdate(BaseModel):
    slot_status: Literal["ACTIVE", "COMPLETED", "CANCELLED"]


class ServiceSlotResponse(BaseModel):
    """Schema for service slot response."""

    slot_id: str
    center_id: str
    vehicle_id: str
    scheduled_time: datetime
    duration_hours: float
    slot_status: str
    reason: str | None = None
    scheduled_at: datetime | None
    completed_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None

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
