"""Service Slot ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.service_center import ServiceCenter
    from app.models.vehicle import Vehicle

OPEN_SLOT_STATUSES = ("PENDING", "ACTIVE")


class ServiceSlot(Base):
    __tablename__ = "service_slots"

    slot_id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    center_id: Mapped[str] = mapped_column(String(36), ForeignKey("service_centers.center_id"), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(String(16), ForeignKey("vehicles.vehicle_id"), nullable=False, index=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_hours: Mapped[float] = mapped_column(nullable=False)  # Service duration in hours
    slot_status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)  # PENDING/ACTIVE/COMPLETED/CANCELLED
    reason: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g. predicted fault that triggered booking
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    service_center: Mapped["ServiceCenter"] = relationship(back_populates="service_slots")
    vehicle: Mapped["Vehicle"] = relationship(back_populates="service_slots")
