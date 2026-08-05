"""Telemetry service layer."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import TelemetryReading
from app.schemas.telemetry import TelemetryReadingCreate


class TelemetryService:
    """Service for telemetry operations."""

    @staticmethod
    def create_reading(db: Session, reading: TelemetryReadingCreate) -> TelemetryReading:
        """Create a new telemetry reading."""
        db_reading = TelemetryReading(**reading.model_dump())
        db.add(db_reading)
        db.commit()
        db.refresh(db_reading)
        return db_reading

    @staticmethod
    def get_reading_by_id(db: Session, telemetry_id: int) -> TelemetryReading | None:
        """Get a telemetry reading by primary key."""
        return db.query(TelemetryReading).filter(TelemetryReading.id == telemetry_id).first()

    @staticmethod
    def get_recent_readings(
        db: Session,
        vehicle_id: str,
        hours: int | None = 24,
        limit: int = 100,
    ) -> list[TelemetryReading]:
        """Get telemetry readings for a vehicle, optionally limited by recent hours."""
        query = db.query(TelemetryReading).filter(TelemetryReading.vehicle_id == vehicle_id)

        if hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            query = query.filter(TelemetryReading.timestamp >= cutoff)

        return query.order_by(TelemetryReading.timestamp.desc()).limit(limit).all()

    @staticmethod
    def count_readings(db: Session, vehicle_id: str, hours: int | None = 24) -> int:
        """Count telemetry readings for a vehicle, optionally limited by recent hours."""
        query = db.query(TelemetryReading).filter(TelemetryReading.vehicle_id == vehicle_id)

        if hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            query = query.filter(TelemetryReading.timestamp >= cutoff)

        return query.count()
