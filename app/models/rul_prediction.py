"""RUL(Remaining useful life) prediction ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.telemetry_reading import TelemetryReading
    from app.models.vehicle import Vehicle


class RULPrediction(Base):
    __tablename__ = "rul_predictions"
    __table_args__ = (
        Index("ix_rul_predictions_vehicle_id_created_at", "vehicle_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.vehicle_id"), nullable=False, index=True)
    telemetry_reading_id: Mapped[int | None] = mapped_column(ForeignKey("telemetry_readings.id"), nullable=True, index=True)

    rul_hours: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    vehicle: Mapped[Vehicle] = relationship(back_populates="rul_predictions")
    telemetry_reading: Mapped[TelemetryReading | None] = relationship(back_populates="rul_predictions")
