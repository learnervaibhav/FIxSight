"""Idempotent first-run setup: users, vehicles, service centers and a little telemetry history.

Safe to run repeatedly (Docker runs it on every start). Only missing data is added,
so an existing database seeded from the CSV dataset is left untouched apart from
adding service centers if none exist.

Usage:
    python scripts/bootstrap.py                 # after `alembic upgrade head`
    python scripts/bootstrap.py --vehicles 15 --history-hours 24
"""

from __future__ import annotations

import argparse
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import SessionLocal  # noqa: E402
from app.models import TelemetryReading, User, Vehicle  # noqa: E402
from app.services import ServiceSchedulingService  # noqa: E402
from app.simulation.telemetry_generator import VehicleSim, generate_reading  # noqa: E402
from scripts.generate_dataset import generate_vehicle_metadata  # noqa: E402
from scripts.seed_database import DELHI_USERS  # noqa: E402
from scripts.seed_service_centers import seed_service_centers  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap FixSight demo data")
    parser.add_argument("--vehicles", type=int, default=15, help="Vehicles to create when none exist (default 15)")
    parser.add_argument("--history-hours", type=int, default=24, help="Hourly telemetry rows per new vehicle (default 24)")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)

    with SessionLocal() as db:
        users = db.query(User).order_by(User.email).all()
        if not users:
            for data in DELHI_USERS:
                db.add(User(user_id=str(uuid.uuid4()), **data))
            db.commit()
            users = db.query(User).order_by(User.email).all()
            print(f"users: created {len(users)}")
        else:
            print(f"users: {len(users)} present")
        users_by_email = {user.email: user for user in users}
        ordered_users = [users_by_email[u["email"]] for u in DELHI_USERS if u["email"] in users_by_email] or users

        new_vehicle_ids: list[str] = []
        if db.query(Vehicle).count() == 0:
            metadata = generate_vehicle_metadata(args.vehicles, args.seed)
            for idx, row in metadata.iterrows():
                owner = ordered_users[int(idx) % len(ordered_users)]
                db.add(
                    Vehicle(
                        vehicle_id=str(row["vehicle_id"]),
                        user_id=owner.user_id,
                        location=owner.location,
                        manufacture_year=int(row["manufacture_year"]),
                        initial_odometer=int(row["initial_odometer"]),
                        engine_type=str(row["engine_type"]),
                        driving_profile=str(row["driving_profile"]),
                        region=str(row["region"]),
                        average_daily_distance=float(row["average_daily_distance"]),
                    )
                )
                new_vehicle_ids.append(str(row["vehicle_id"]))
            db.commit()
            print(f"vehicles: created {len(new_vehicle_ids)}")
        else:
            print(f"vehicles: {db.query(Vehicle).count()} present")

        # Short telemetry history so charts are not empty before the first simulation.
        start = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=args.history_hours)
        for vehicle_id in new_vehicle_ids:
            vehicle = db.get(Vehicle, vehicle_id)
            sim = VehicleSim(
                vehicle_id=vehicle_id,
                engine_type=vehicle.engine_type,
                driving_profile=vehicle.driving_profile,
                engine_hours=rng.uniform(200, 1500),
                wear=rng.uniform(0.05, 0.25),
            )
            for hour in range(args.history_hours):
                payload = generate_reading(sim, start + timedelta(hours=hour), rng)
                payload["timestamp"] = datetime.fromisoformat(payload["timestamp"])
                db.add(TelemetryReading(vehicle_id=vehicle_id, **payload))
        if new_vehicle_ids:
            db.commit()
            print(f"telemetry: {args.history_hours} rows for each new vehicle")

        result = seed_service_centers(db)
        print(f"service centers: created {result['created']}, skipped {result['skipped']} existing")
        ServiceSchedulingService.recompute_occupancy(db)

    print("bootstrap complete")


if __name__ == "__main__":
    main()
