"""Service Center ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.service_slot import ServiceSlot


class ServiceCenter(Base):
    __tablename__ = "service_centers"

    center_id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    center_name: Mapped[str] = mapped_column(String(256), nullable=False)
    location: Mapped[str] = mapped_column(String(256), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    operating_hours_start: Mapped[int] = mapped_column(Integer, nullable=False)  # 24-hour format (e.g., 10 for 10 AM)
    operating_hours_end: Mapped[int] = mapped_column(Integer, nullable=False)    # 24-hour format (e.g., 17 for 5 PM)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False)           # Total slots available
    current_occupancy: Mapped[int] = mapped_column(Integer, default=0)           # Currently scheduled slots
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    service_slots: Mapped[list["ServiceSlot"]] = relationship(back_populates="service_center")