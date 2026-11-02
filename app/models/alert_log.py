"""Alert log ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.fault_prediction import FaultPrediction
    from app.models.vehicle import Vehicle


class AlertLog(Base):
    __tablename__ = "alert_logs"
    __table_args__ = (
        Index("ix_alert_logs_vehicle_id_created_at", "vehicle_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.vehicle_id"), nullable=False, index=True)
    fault_prediction_id: Mapped[int | None] = mapped_column(ForeignKey("fault_predictions.id"), nullable=True, index=True)

    alert_type: Mapped[str] = mapped_column(String(32), nullable=False, default="fault")  # fault/booking/service_completed
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="sms")
    recipient: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    alert_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())

    vehicle: Mapped[Vehicle] = relationship(back_populates="alert_logs")
    fault_prediction: Mapped[FaultPrediction | None] = relationship(back_populates="alerts")
