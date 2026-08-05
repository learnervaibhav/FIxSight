"""
Seed service centers into the database.
Service centers are distributed across Delhi NCR region.
"""
import uuid
from sqlalchemy.orm import Session
import sys
from pathlib import Path


# resolve the issue of directory structure.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    
from app.core.database import SessionLocal
from app.models import ServiceCenter


# 10 Delhi service centers with realistic locations
DELHI_SERVICE_CENTERS = [
    {
        "center_name": "Delhi Service Hub 1 - Connaught Place",
        "location": "Connaught Place",
        "latitude": 28.6329,
        "longitude": 77.2197,
        "operating_hours_start": 10,
        "operating_hours_end": 17,
        "max_capacity": 6,
    },
    {
        "center_name": "Delhi Service Hub 2 - Dwarka",
        "location": "Dwarka",
        "latitude": 28.5921,
        "longitude": 77.0460,
        "operating_hours_start": 9,
        "operating_hours_end": 19,
        "max_capacity": 8,
    },
    {
        "center_name": "Delhi Service Hub 3 - Noida",
        "location": "Noida",
        "latitude": 28.5355,
        "longitude": 77.3910,
        "operating_hours_start": 10,
        "operating_hours_end": 18,
        "max_capacity": 7,
    },
    {
        "center_name": "Delhi Service Hub 4 - Gurugram",
        "location": "Gurugram",
        "latitude": 28.4595,
        "longitude": 77.0266,
        "operating_hours_start": 9,
        "operating_hours_end": 19,
        "max_capacity": 8,
    },
    {
        "center_name": "Delhi Service Hub 5 - Indirapuram",
        "location": "Indirapuram",
        "latitude": 28.6139,
        "longitude": 77.3823,
        "operating_hours_start": 10,
        "operating_hours_end": 17,
        "max_capacity": 5,
    },
    {
        "center_name": "Delhi Service Hub 6 - Greater Kailash",
        "location": "Greater Kailash",
        "latitude": 28.5244,
        "longitude": 77.2068,
        "operating_hours_start": 10,
        "operating_hours_end": 18,
        "max_capacity": 6,
    },
    {
        "center_name": "Delhi Service Hub 7 - Rohini",
        "location": "Rohini",
        "latitude": 28.7495,
        "longitude": 77.0585,
        "operating_hours_start": 9,
        "operating_hours_end": 19,
        "max_capacity": 7,
    },
    {
        "center_name": "Delhi Service Hub 8 - Vasant Kunj",
        "location": "Vasant Kunj",
        "latitude": 28.5244,
        "longitude": 77.1855,
        "operating_hours_start": 10,
        "operating_hours_end": 17,
        "max_capacity": 6,
    },
    {
        "center_name": "Delhi Service Hub 9 - Lajpat Nagar",
        "location": "Lajpat Nagar",
        "latitude": 28.5621,
        "longitude": 77.2432,
        "operating_hours_start": 10,
        "operating_hours_end": 18,
        "max_capacity": 5,
    },
    {
        "center_name": "Delhi Service Hub 10 - Karol Bagh",
        "location": "Karol Bagh",
        "latitude": 28.6505,
        "longitude": 77.1925,
        "operating_hours_start": 9,
        "operating_hours_end": 19,
        "max_capacity": 8,
    },
]


def seed_service_centers(db: Session) -> dict:
    """
    Seed service centers into the database.
    Returns dict with count of created centers.
    """
    created_count = 0
    center_id_map = {}
    
    for center_data in DELHI_SERVICE_CENTERS:
        center_id = str(uuid.uuid4())
        
        service_center = ServiceCenter(
            center_id=center_id,
            center_name=center_data["center_name"],
            location=center_data["location"],
            latitude=center_data["latitude"],
            longitude=center_data["longitude"],
            operating_hours_start=center_data["operating_hours_start"],
            operating_hours_end=center_data["operating_hours_end"],
            max_capacity=center_data["max_capacity"],
            current_occupancy=0,
        )
        
        db.add(service_center)
        center_id_map[center_data["location"]] = center_id
        created_count += 1
    
    db.commit()
    return {"created": created_count, "center_id_map": center_id_map}


def main():
    """Main entry point for seeding service centers."""
    db = SessionLocal()
    try:
        print("Seeding service centers...")
        result = seed_service_centers(db)
        print(f"✓ Created {result['created']} service centers")
        print("\nService Centers created:")
        for location, center_id in result['center_id_map'].items():
            print(f"  - {location}: {center_id}")
    except Exception as e:
        print(f"✗ Error seeding service centers: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
