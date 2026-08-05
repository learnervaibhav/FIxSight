"""Fault prediction ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.alert_log import AlertLog
    from app.models.telemetry_reading import TelemetryReading
    from app.models.vehicle import Vehicle


class FaultPrediction(Base):
    __tablename__ = "fault_predictions"
    __table_args__ = (
        Index("ix_fault_predictions_vehicle_id_created_at", "vehicle_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.vehicle_id"), nullable=False, index=True)
    telemetry_reading_id: Mapped[int | None] = mapped_column(ForeignKey("telemetry_readings.id"), nullable=True, index=True)

    fault_label: Mapped[str] = mapped_column(String(128), nullable=False)
    fault_probability: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    llm_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    vehicle: Mapped["Vehicle"] = relationship(back_populates="fault_predictions")
    telemetry_reading: Mapped["TelemetryReading | None"] = relationship(back_populates="fault_predictions")
    alerts: Mapped[list["AlertLog"]] = relationship(back_populates="fault_prediction")
