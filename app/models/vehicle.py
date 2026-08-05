"""Vehicle ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.alert_log import AlertLog
    from app.models.fault_prediction import FaultPrediction
    from app.models.rul_prediction import RULPrediction
    from app.models.telemetry_reading import TelemetryReading
    from app.models.user import User


class Vehicle(Base):
    __tablename__ = "vehicles"

    vehicle_id: Mapped[str] = mapped_column(String(16), primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(256), nullable=False)
    manufacture_year: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_odometer: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_type: Mapped[str] = mapped_column(String(64), nullable=False)
    driving_profile: Mapped[str] = mapped_column(String(32), nullable=False)
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    average_daily_distance: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="vehicles")
    telemetry_readings: Mapped[list["TelemetryReading"]] = relationship(back_populates="vehicle")
    fault_predictions: Mapped[list["FaultPrediction"]] = relationship(back_populates="vehicle")
    rul_predictions: Mapped[list["RULPrediction"]] = relationship(back_populates="vehicle")
    alert_logs: Mapped[list["AlertLog"]] = relationship(back_populates="vehicle")
