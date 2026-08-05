"""Vehicle service layer."""

from sqlalchemy.orm import Session

from app.models import Vehicle
from app.schemas.vehicle import VehicleCreate


class VehicleService:
    """Service for vehicle operations."""

    @staticmethod
    def create_vehicle(db: Session, vehicle: VehicleCreate) -> Vehicle:
        """Create a new vehicle."""
        db_vehicle = Vehicle(**vehicle.model_dump())
        db.add(db_vehicle)
        db.commit()
        db.refresh(db_vehicle)
        return db_vehicle

    @staticmethod
    def get_vehicle(db: Session, vehicle_id: str) -> Vehicle | None:
        """Get vehicle by ID."""
        return db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()

    @staticmethod
    def list_vehicles(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Vehicle], int]:
        """List all vehicles with pagination."""
        total = db.query(Vehicle).count()
        vehicles = db.query(Vehicle).offset(skip).limit(limit).all()
        return vehicles, total

    @staticmethod
    def delete_vehicle(db: Session, vehicle_id: str) -> bool:
        """Delete a vehicle."""
        vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
        if not vehicle:
            return False
        db.delete(vehicle)
        db.commit()
        return True
