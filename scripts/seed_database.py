"""Seed FixSight PostgreSQL tables from CSV datasets.

Usage examples:
1) Seed vehicles + telemetry + maintenance-derived fault predictions:
   python scripts/seed_database.py

2) Clear existing data first, then seed:
   python scripts/seed_database.py --truncate

3) Also generate RUL predictions from telemetry rows:
   python scripts/seed_database.py --seed-rul-from-telemetry
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import delete, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

# Make sibling package `app` importable when running this file directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import SessionLocal
from app.models import AlertLog, FaultPrediction, RULPrediction, TelemetryReading, User, Vehicle


@dataclass
class SeedStats:
    users_upserted: int = 0
    vehicles_upserted: int = 0
    telemetry_inserted: int = 0
    faults_inserted: int = 0
    rul_inserted: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed database from FixSight CSV files")
    parser.add_argument(
        "--dataset",
        "--dataset-dir",
        dest="dataset",
        default="dataset",
        help="Path to dataset folder (default: dataset)",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=5000,
        help="Telemetry CSV chunk size (default: 5000)",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete existing rows before seeding",
    )
    parser.add_argument(
        "--skip-faults",
        action="store_true",
        help="Skip maintenance -> fault_predictions seed",
    )
    parser.add_argument(
        "--seed-rul-from-telemetry",
        action="store_true",
        help="Create rul_predictions from telemetry CSV rows",
    )
    return parser.parse_args()


def dataset_path(dataset_arg: str) -> Path:
    dataset = Path(dataset_arg)
    if dataset.is_absolute():
        return dataset

    # Prefer project-root relative path so script works from any cwd.
    candidate = PROJECT_ROOT / dataset
    if candidate.exists():
        return candidate

    # Fallback to current working directory resolution.
    return dataset.resolve()


def normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "none" or text.lower() == "nan":
        return None
    return text


def infer_severity(downtime_hours: float, mode: str | None) -> str:
    if (mode or "").lower() == "reactive" and downtime_hours >= 8:
        return "HIGH"
    if downtime_hours >= 8:
        return "HIGH"
    if downtime_hours >= 4:
        return "MEDIUM"
    return "LOW"


def infer_probability(downtime_hours: float, mode: str | None) -> float:
    base = 0.65 if (mode or "").lower() == "preventive" else 0.82
    bonus = min(downtime_hours / 100.0, 0.15)
    return round(min(base + bonus, 0.99), 4)


def truncate_tables(db: Session) -> None:
    # Child tables first because of foreign keys.
    db.execute(delete(AlertLog))
    db.execute(delete(FaultPrediction))
    db.execute(delete(RULPrediction))
    db.execute(delete(TelemetryReading))
    db.execute(delete(Vehicle))
    db.execute(delete(User))
    db.commit()


# Delhi region coordinates (approximate centers of key areas)
DELHI_USERS = [
    {
        "name": "Rajesh Kumar",
        "email": "rajesh.kumar@email.com",
        "phone": "9811234567",
        "location": "Connaught Place, Delhi",
        "latitude": 28.6329,
        "longitude": 77.2197,
    },
    {
        "name": "Priya Singh",
        "email": "priya.singh@email.com",
        "phone": "9822345678",
        "location": "Dwarka, Delhi",
        "latitude": 28.5921,
        "longitude": 77.0460,
    },
    {
        "name": "Amit Verma",
        "email": "amit.verma@email.com",
        "phone": "9833456789",
        "location": "Noida, Uttar Pradesh",
        "latitude": 28.5355,
        "longitude": 77.3910,
    },
    {
        "name": "Neha Gupta",
        "email": "neha.gupta@email.com",
        "phone": "9844567890",
        "location": "Gurugram, Haryana",
        "latitude": 28.4595,
        "longitude": 77.0266,
    },
    {
        "name": "Vikas Sharma",
        "email": "vikas.sharma@email.com",
        "phone": "9855678901",
        "location": "Indirapuram, Ghaziabad",
        "latitude": 28.6139,
        "longitude": 77.3823,
    },
    {
        "name": "Anjali Patel",
        "email": "anjali.patel@email.com",
        "phone": "9866789012",
        "location": "Greater Kailash, Delhi",
        "latitude": 28.5244,
        "longitude": 77.2068,
    },
    {
        "name": "Arjun Desai",
        "email": "arjun.desai@email.com",
        "phone": "9877890123",
        "location": "Rohini, Delhi",
        "latitude": 28.7495,
        "longitude": 77.0585,
    },
    {
        "name": "Divya Nair",
        "email": "divya.nair@email.com",
        "phone": "9888901234",
        "location": "Vasant Kunj, Delhi",
        "latitude": 28.5244,
        "longitude": 77.1855,
    },
    {
        "name": "Rohit Jain",
        "email": "rohit.jain@email.com",
        "phone": "9899012345",
        "location": "Lajpat Nagar, Delhi",
        "latitude": 28.5621,
        "longitude": 77.2432,
    },
    {
        "name": "Sneha Reddy",
        "email": "sneha.reddy@email.com",
        "phone": "9800123456",
        "location": "Karol Bagh, Delhi",
        "latitude": 28.6505,
        "longitude": 77.1925,
    },
]


def seed_users(db: Session, stats: SeedStats) -> dict[int, str]:
    """Seed users with Delhi region locations. Returns mapping of user index to user_id."""
    user_records = []
    user_id_map = {}

    for idx, user_data in enumerate(DELHI_USERS):
        user_id = str(uuid.uuid4())
        user_records.append({**user_data, "user_id": user_id})
        user_id_map[idx] = user_id

    if user_records:
        stmt = pg_insert(User).values(user_records)
        stmt = stmt.on_conflict_do_update(
            index_elements=[User.email],
            set_={
                "name": stmt.excluded.name,
                "phone": stmt.excluded.phone,
                "location": stmt.excluded.location,
                "latitude": stmt.excluded.latitude,
                "longitude": stmt.excluded.longitude,
            },
        )
        db.execute(stmt)
        db.commit()
    stats.users_upserted += len(user_records)
    return user_id_map


def seed_vehicles(db: Session, dataset: Path, stats: SeedStats, user_id_map: dict[int, str]) -> None:
    vehicle_csv = dataset / "vehicle_metadata.csv"
    if not vehicle_csv.exists():
        raise FileNotFoundError(f"Missing file: {vehicle_csv}")

    df = pd.read_csv(vehicle_csv)
    records = []
    
    for idx, (_, row) in enumerate(df.iterrows()):
        # Cycle through users if there are more vehicles than users
        user_idx = idx % len(user_id_map)
        user_id = user_id_map[user_idx]
        
        # Get user location from DELHI_USERS
        user_location = DELHI_USERS[user_idx]["location"]
        
        records.append(
            {
                "vehicle_id": str(row["vehicle_id"]).strip(),
                "user_id": user_id,
                "location": user_location,
                "manufacture_year": int(row["manufacture_year"]),
                "initial_odometer": int(row["initial_odometer"]),
                "engine_type": str(row["engine_type"]).strip(),
                "driving_profile": str(row["driving_profile"]).strip(),
                "region": str(row["region"]).strip(),
                "average_daily_distance": float(row["average_daily_distance"]),
            }
        )

    stmt = pg_insert(Vehicle).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Vehicle.vehicle_id],
        set_={
            "user_id": stmt.excluded.user_id,
            "location": stmt.excluded.location,
            "manufacture_year": stmt.excluded.manufacture_year,
            "initial_odometer": stmt.excluded.initial_odometer,
            "engine_type": stmt.excluded.engine_type,
            "driving_profile": stmt.excluded.driving_profile,
            "region": stmt.excluded.region,
            "average_daily_distance": stmt.excluded.average_daily_distance,
        },
    )
    db.execute(stmt)
    db.commit()
    stats.vehicles_upserted += len(records)


def telemetry_rows_from_chunk(chunk: pd.DataFrame) -> list[dict[str, Any]]:
    chunk["timestamp"] = pd.to_datetime(chunk["timestamp"], errors="coerce")
    chunk = chunk.dropna(subset=["vehicle_id", "timestamp"])

    numeric_cols = [
        "engine_rpm",
        "engine_load",
        "coolant_temperature",
        "oil_temperature",
        "oil_pressure",
        "fuel_rate",
        "short_term_fuel_trim",
        "long_term_fuel_trim",
        "mass_air_flow",
        "intake_manifold_pressure",
        "battery_voltage",
        "alternator_voltage",
        "gear_position",
        "transmission_temperature",
        "o2_sensor_voltage",
        "egr_position",
        "vehicle_speed",
        "throttle_position",
        "cumulative_engine_hours",
        "rolling_mean_temp",
        "rolling_std_temp",
        "rolling_slope_oil_pressure",
        "harsh_acceleration_count",
        "idle_time_ratio",
        "degradation_index",
        "health_score",
        "rul_hours",
    ]

    for col in numeric_cols:
        chunk[col] = pd.to_numeric(chunk[col], errors="coerce")

    chunk = chunk.dropna(subset=numeric_cols)

    rows: list[dict[str, Any]] = []
    for _, row in chunk.iterrows():
        rows.append(
            {
                "vehicle_id": str(row["vehicle_id"]).strip(),
                "timestamp": row["timestamp"].to_pydatetime(),
                "engine_rpm": float(row["engine_rpm"]),
                "engine_load": float(row["engine_load"]),
                "coolant_temperature": float(row["coolant_temperature"]),
                "oil_temperature": float(row["oil_temperature"]),
                "oil_pressure": float(row["oil_pressure"]),
                "fuel_rate": float(row["fuel_rate"]),
                "short_term_fuel_trim": float(row["short_term_fuel_trim"]),
                "long_term_fuel_trim": float(row["long_term_fuel_trim"]),
                "mass_air_flow": float(row["mass_air_flow"]),
                "intake_manifold_pressure": float(row["intake_manifold_pressure"]),
                "battery_voltage": float(row["battery_voltage"]),
                "alternator_voltage": float(row["alternator_voltage"]),
                "gear_position": int(row["gear_position"]),
                "transmission_temperature": float(row["transmission_temperature"]),
                "o2_sensor_voltage": float(row["o2_sensor_voltage"]),
                "egr_position": float(row["egr_position"]),
                "vehicle_speed": float(row["vehicle_speed"]),
                "throttle_position": float(row["throttle_position"]),
                "cumulative_engine_hours": float(row["cumulative_engine_hours"]),
                "rolling_mean_temp": float(row["rolling_mean_temp"]),
                "rolling_std_temp": float(row["rolling_std_temp"]),
                "rolling_slope_oil_pressure": float(row["rolling_slope_oil_pressure"]),
                "harsh_acceleration_count": int(row["harsh_acceleration_count"]),
                "idle_time_ratio": float(row["idle_time_ratio"]),
                "degradation_index": float(row["degradation_index"]),
                "health_score": float(row["health_score"]),
                "rul_hours": float(row["rul_hours"]),
            }
        )

    return rows


def seed_telemetry(
    db: Session,
    dataset: Path,
    chunksize: int,
    stats: SeedStats,
    seed_rul_from_telemetry: bool,
) -> None:
    telemetry_csv = dataset / "telematics_data.csv"
    if not telemetry_csv.exists():
        raise FileNotFoundError(f"Missing file: {telemetry_csv}")

    for chunk in pd.read_csv(telemetry_csv, chunksize=chunksize):
        rows = telemetry_rows_from_chunk(chunk)
        if not rows:
            continue

        db.execute(insert(TelemetryReading), rows)
        stats.telemetry_inserted += len(rows)

        if seed_rul_from_telemetry:
            rul_rows = [
                {
                    "vehicle_id": row["vehicle_id"],
                    "telemetry_reading_id": None,
                    "rul_hours": row["rul_hours"],
                    "confidence_score": None,
                    "created_at": row["timestamp"],
                }
                for row in rows
            ]
            db.execute(insert(RULPrediction), rul_rows)
            stats.rul_inserted += len(rul_rows)

        db.commit()


def seed_fault_predictions(db: Session, dataset: Path, stats: SeedStats) -> None:
    maintenance_csv = dataset / "maintenance_logs.csv"
    if not maintenance_csv.exists():
        raise FileNotFoundError(f"Missing file: {maintenance_csv}")

    df = pd.read_csv(maintenance_csv)
    df["service_date"] = pd.to_datetime(df["service_date"], errors="coerce")
    df["downtime_hours"] = pd.to_numeric(df["downtime_hours"], errors="coerce").fillna(0.0)

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        fault_text = normalize_optional_text(row.get("fault_detected"))
        if not fault_text:
            continue

        mode = normalize_optional_text(row.get("preventive_or_reactive"))
        downtime = float(row.get("downtime_hours", 0.0) or 0.0)
        created_at = row.get("service_date")
        if pd.isna(created_at):
            continue

        rows.append(
            {
                "vehicle_id": str(row["vehicle_id"]).strip(),
                "telemetry_reading_id": None,
                "fault_label": fault_text,
                "fault_probability": infer_probability(downtime, mode),
                "severity": infer_severity(downtime, mode),
                "llm_explanation": None,
                "created_at": created_at.to_pydatetime(),
            }
        )

    if rows:
        db.execute(insert(FaultPrediction), rows)
        db.commit()
    stats.faults_inserted += len(rows)


def main() -> None:
    args = parse_args()
    dataset = dataset_path(args.dataset)

    if not dataset.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset}")

    stats = SeedStats()

    db = SessionLocal()
    try:
        if args.truncate:
            truncate_tables(db)

        user_id_map = seed_users(db, stats)
        seed_vehicles(db, dataset, stats, user_id_map)
        seed_telemetry(
            db,
            dataset,
            args.chunksize,
            stats,
            seed_rul_from_telemetry=args.seed_rul_from_telemetry,
        )

        if not args.skip_faults:
            seed_fault_predictions(db, dataset, stats)

    finally:
        db.close()

    print("\nSeeding completed successfully:")
    print(f"  users upserted: {stats.users_upserted}")
    print(f"  vehicles upserted: {stats.vehicles_upserted}")
    print(f"  telemetry inserted: {stats.telemetry_inserted}")
    print(f"  fault predictions inserted: {stats.faults_inserted}")
    print(f"  rul predictions inserted: {stats.rul_inserted}")


if __name__ == "__main__":
    main()
