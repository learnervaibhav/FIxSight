"""Telemetry reading ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.fault_prediction import FaultPrediction
    from app.models.rul_prediction import RULPrediction
    from app.models.vehicle import Vehicle


class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"
    __table_args__ = (
        Index("ix_telemetry_readings_vehicle_id_timestamp", "vehicle_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.vehicle_id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, index=True)

    engine_rpm: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    engine_load: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    coolant_temperature: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    oil_temperature: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    oil_pressure: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    fuel_rate: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    short_term_fuel_trim: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    long_term_fuel_trim: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    mass_air_flow: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    intake_manifold_pressure: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    battery_voltage: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    alternator_voltage: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    gear_position: Mapped[int] = mapped_column(Integer, nullable=False)
    transmission_temperature: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    o2_sensor_voltage: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    egr_position: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    vehicle_speed: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    throttle_position: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    cumulative_engine_hours: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    rolling_mean_temp: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    rolling_std_temp: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    rolling_slope_oil_pressure: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    harsh_acceleration_count: Mapped[int] = mapped_column(Integer, nullable=False)
    idle_time_ratio: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    degradation_index: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    health_score: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    rul_hours: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="telemetry_readings")
    fault_predictions: Mapped[list["FaultPrediction"]] = relationship(back_populates="telemetry_reading")
    rul_predictions: Mapped[list["RULPrediction"]] = relationship(back_populates="telemetry_reading")
