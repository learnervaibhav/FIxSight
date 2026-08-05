"""Generate FixSight synthetic dataset CSVs.

Produces three files exactly matching what seed_database.py expects:
    dataset/
        telematics_data.csv       -- per-minute OBD-II readings, 15 vehicles, ~2 months
        vehicle_metadata.csv      -- vehicle profiles (engine type, region, driving style)
        maintenance_logs.csv      -- historical service records with fault labels

Usage:
    python scripts/generate_dataset.py                   # writes to dataset/ (default)
    python scripts/generate_dataset.py --out dataset     # same, explicit path
    python scripts/generate_dataset.py --vehicles 15     # match original DB count
    python scripts/generate_dataset.py --days 60         # match original DB date range
    python scripts/generate_dataset.py --seed 42         # reproducible
    python scripts/generate_dataset.py --sample-every 5  # fewer rows (faster)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Config knobs — matched to original DB snapshot
# ---------------------------------------------------------------------------
DEFAULT_VEHICLES = 15          # 15 vehicles in original DB (V001-V015)
DEFAULT_DAYS     = 60          # Jan 1, 2025 → March 1, 2025 (~60 days)
DEFAULT_SEED     = 42
START_DATE       = "2025-01-01"   # matches earliest timestamp in telemetry_readings

# ── Categorical strings — MUST match DB values exactly ──────────────────────

# vehicle_metadata.csv / vehicles table
ENGINE_TYPES     = ["gasoline", "gasoline_turbo", "diesel", "hybrid"]
DRIVING_PROFILES = ["normal", "highway", "mixed", "aggressive", "gentle"]
REGIONS          = ["Central", "East", "West", "North", "South"]

# maintenance_logs.csv / fault_predictions.fault_label — free-text strings
# taken directly from the live fault_predictions table snapshot
FAULT_LABELS = [
    "Coolant overheating",
    "Low oil pressure detected",
    "Battery voltage drop",
    "Transmission overheat",
    "Abnormal fuel trim drift",
    "EGR valve stuck open",
    "Mass air flow sensor fault",
    "Engine misfire detected",
    "Fuel injector fault",
    "normal",
]

MAINTENANCE_MODES = ["preventive", "reactive"]
MAINTENANCE_ACTIONS = [
    "Coolant flush and thermostat replacement",
    "Oil pump inspection and replacement",
    "Battery cell replacement",
    "Transmission fluid flush",
    "Engine tune-up and injector cleaning",
    "EGR valve cleaning",
    "MAF sensor replacement",
    "Spark plug replacement",
    "Fuel injector replacement",
    "Air filter and throttle body cleaning",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


# ---------------------------------------------------------------------------
# 1.  vehicle_metadata.csv
#     Columns consumed by seed_database.py → seed_vehicles():
#         vehicle_id, manufacture_year, initial_odometer,
#         engine_type, driving_profile, region, average_daily_distance
# ---------------------------------------------------------------------------

def generate_vehicle_metadata(n_vehicles: int, seed: int) -> pd.DataFrame:
    """Return a DataFrame matching seed_database.py Vehicle column expectations.

    Vehicle IDs use the format V001, V002 … to match the original DB snapshot.
    """
    rng_ = rng(seed)

    # Weighted driving profile distribution — 'normal' is most common in DB
    profile_weights = [0.40, 0.25, 0.15, 0.12, 0.08]   # normal, highway, mixed, aggressive, gentle

    rows = []
    for i in range(n_vehicles):
        vehicle_id = f"V{(i + 1):03d}"    # V001, V002, … V015 — matches original DB
        rows.append(
            {
                "vehicle_id":             vehicle_id,
                "manufacture_year":       int(rng_.integers(2019, 2025)),
                "initial_odometer":       int(rng_.integers(0, 70_000)),
                "engine_type":            str(rng_.choice(ENGINE_TYPES)),
                "driving_profile":        str(
                    rng_.choice(DRIVING_PROFILES, p=profile_weights)
                ),
                "region":                 str(rng_.choice(REGIONS)),
                "average_daily_distance": round(float(rng_.uniform(30, 250)), 1),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2.  telematics_data.csv  (the large file)
#     Columns consumed by seed_database.py → telemetry_rows_from_chunk():
#         vehicle_id, timestamp,
#         engine_rpm, engine_load, coolant_temperature, oil_temperature,
#         oil_pressure, fuel_rate, short_term_fuel_trim, long_term_fuel_trim,
#         mass_air_flow, intake_manifold_pressure, battery_voltage,
#         alternator_voltage, gear_position, transmission_temperature,
#         o2_sensor_voltage, egr_position, vehicle_speed, throttle_position,
#         cumulative_engine_hours, rolling_mean_temp, rolling_std_temp,
#         rolling_slope_oil_pressure, harsh_acceleration_count,
#         idle_time_ratio, degradation_index, health_score, rul_hours
# ---------------------------------------------------------------------------

def _sensor_baselines(engine_type: str, driving_profile: str) -> dict:
    """Realistic sensor baselines matching the engine_type strings in the DB."""
    base_rpm = {
        "gasoline":       1800,
        "gasoline_turbo": 2100,
        "diesel":         1500,
        "hybrid":         1400,
    }.get(engine_type, 1700)

    rpm_variance = {
        "aggressive": 650,
        "highway":    200,
        "normal":     350,
        "mixed":      380,
        "gentle":     150,
    }.get(driving_profile, 350)

    coolant_base = {
        "diesel":         93,
        "gasoline":       90,
        "gasoline_turbo": 95,
        "hybrid":         82,
    }.get(engine_type, 90)

    return {
        "base_rpm":     base_rpm,
        "rpm_variance": rpm_variance,
        "coolant_base": coolant_base,
    }


def _generate_vehicle_telemetry(
    vehicle_id:     str,
    engine_type:    str,
    driving_profile: str,
    n_days:         int,
    start:          pd.Timestamp,
    seed:           int,
) -> pd.DataFrame:
    """Generate per-minute telemetry for one vehicle over n_days."""
    rg     = rng(seed)
    p      = _sensor_baselines(engine_type, driving_profile)
    n      = n_days * 24 * 60
    ts     = pd.date_range(start=start, periods=n, freq="min")

    # Slow linear degradation 0 → 1 over the full period
    deg = np.linspace(0, 1, n)

    # ── Sensors ──────────────────────────────────────────────────────────────

    engine_rpm = np.clip(
        p["base_rpm"] + rg.normal(0, p["rpm_variance"], n) + deg * 300,
        600, 5500,
    )

    engine_load = np.clip(
        rg.uniform(15, 85, n) + deg * 10, 10, 100
    )

    coolant_temp = np.clip(
        rg.normal(p["coolant_base"], 5, n) + deg * 20, 60, 130
    )

    oil_temp = np.clip(
        coolant_temp + rg.normal(8, 3, n), 60, 160
    )

    oil_pressure = np.clip(
        rg.normal(45, 8, n) - deg * 15, 10, 80
    )

    fuel_rate = np.clip(
        rg.uniform(2, 20, n) + deg * 3, 0.5, 35
    )

    stft = np.clip(rg.normal(0, 3, n) + deg * 5, -30, 30)
    ltft = np.clip(rg.normal(0, 2, n) + deg * 4, -30, 30)

    maf = np.clip(
        (engine_rpm / 6000) * 200 + rg.normal(0, 15, n), 5, 350
    )

    imp = np.clip(
        rg.normal(85, 20, n) + deg * 10, 30, 200
    )

    battery_voltage = np.clip(
        rg.normal(12.6, 0.3, n) - deg * 1.2, 9.0, 14.8
    )

    alternator_voltage = np.clip(
        rg.normal(14.2, 0.4, n) - deg * 0.5, 12.0, 15.5
    )

    gear_position = rg.choice(
        [1, 2, 3, 4, 5, 6], size=n, p=[0.05, 0.15, 0.25, 0.30, 0.20, 0.05]
    )

    trans_temp = np.clip(
        rg.normal(80, 10, n) + deg * 25, 40, 150
    )

    o2_voltage = np.clip(rg.uniform(0.1, 0.9, n), 0.0, 1.0)

    egr_position = np.clip(rg.uniform(0, 60, n), 0, 100)

    speed_base = {
        "highway":   80,
        "normal":    35,
        "mixed":     50,
        "aggressive": 90,
        "gentle":    30,
    }.get(driving_profile, 40)
    vehicle_speed = np.clip(rg.normal(speed_base, 25, n), 0, 200)

    throttle = np.clip(rg.uniform(5, 75, n), 0, 100)

    cumulative_hours = np.cumsum(np.ones(n) / 60)

    # ── Rolling / time-series engineered features ─────────────────────────
    coolant_s = pd.Series(coolant_temp)
    rolling_mean_temp  = coolant_s.rolling(30, min_periods=1).mean().to_numpy()
    rolling_std_temp   = coolant_s.rolling(30, min_periods=1).std().fillna(0).to_numpy()

    oil_s = pd.Series(oil_pressure)
    rolling_slope_oil_pressure = (
        oil_s.rolling(30, min_periods=2)
        .apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0,
            raw=True,
        )
        .fillna(0)
        .to_numpy()
    )

    rpm_diff         = np.abs(np.diff(engine_rpm, prepend=engine_rpm[0]))
    harsh_events     = (rpm_diff > 400).astype(int)
    harsh_accel_count = (
        pd.Series(harsh_events).rolling(30, min_periods=1).sum().astype(int).to_numpy()
    )

    is_idle        = (vehicle_speed < 5).astype(float)
    idle_time_ratio = (
        pd.Series(is_idle).rolling(30, min_periods=1).mean().to_numpy()
    )

    degradation_index = np.clip(
        deg ** 0.7 + rg.normal(0, 0.02, n), 0, 1
    )

    health_score = np.clip(
        100 - degradation_index * 60 + rg.normal(0, 2, n), 20, 100
    )

    max_rul = n_days * 24
    rul_hours = np.clip(
        max_rul * (1 - degradation_index) + rg.normal(0, 20, n), 0, max_rul
    )

    return pd.DataFrame(
        {
            "vehicle_id":                 vehicle_id,
            "timestamp":                  ts,
            "engine_rpm":                 np.round(engine_rpm, 2),
            "engine_load":                np.round(engine_load, 2),
            "coolant_temperature":        np.round(coolant_temp, 2),
            "oil_temperature":            np.round(oil_temp, 2),
            "oil_pressure":               np.round(oil_pressure, 2),
            "fuel_rate":                  np.round(fuel_rate, 3),
            "short_term_fuel_trim":       np.round(stft, 4),
            "long_term_fuel_trim":        np.round(ltft, 4),
            "mass_air_flow":              np.round(maf, 3),
            "intake_manifold_pressure":   np.round(imp, 2),
            "battery_voltage":            np.round(battery_voltage, 3),
            "alternator_voltage":         np.round(alternator_voltage, 3),
            "gear_position":              gear_position,
            "transmission_temperature":   np.round(trans_temp, 2),
            "o2_sensor_voltage":          np.round(o2_voltage, 4),
            "egr_position":               np.round(egr_position, 2),
            "vehicle_speed":              np.round(vehicle_speed, 2),
            "throttle_position":          np.round(throttle, 2),
            "cumulative_engine_hours":    np.round(cumulative_hours, 2),
            "rolling_mean_temp":          np.round(rolling_mean_temp, 2),
            "rolling_std_temp":           np.round(rolling_std_temp, 3),
            "rolling_slope_oil_pressure": np.round(rolling_slope_oil_pressure, 4),
            "harsh_acceleration_count":   harsh_accel_count,
            "idle_time_ratio":            np.round(idle_time_ratio, 4),
            "degradation_index":          np.round(degradation_index, 4),
            "health_score":               np.round(health_score, 2),
            "rul_hours":                  np.round(rul_hours, 2),
        }
    )


def generate_telematics_data(
    metadata:     pd.DataFrame,
    n_days:       int,
    seed:         int,
    out_csv:      Path,
    sample_every: int = 1,
) -> int:
    """Stream-write telemetry CSV vehicle by vehicle. Returns total row count."""
    start = pd.Timestamp(START_DATE)
    first = True
    total = 0

    for i, row in metadata.iterrows():
        vehicle_seed = seed + i * 31
        df = _generate_vehicle_telemetry(
            vehicle_id=     str(row["vehicle_id"]),
            engine_type=    str(row["engine_type"]),
            driving_profile=str(row["driving_profile"]),
            n_days=         n_days,
            start=          start,
            seed=           vehicle_seed,
        )

        if sample_every > 1:
            df = df.iloc[::sample_every].reset_index(drop=True)

        df.to_csv(out_csv, mode="w" if first else "a", index=False, header=first)
        first = False
        total += len(df)
        print(f"  telemetry: {row['vehicle_id']}  {len(df):,} rows")

    return total


# ---------------------------------------------------------------------------
# 3.  maintenance_logs.csv
#     Columns consumed by seed_database.py → seed_fault_predictions():
#         vehicle_id, service_date, fault_detected,
#         preventive_or_reactive, downtime_hours
#     (extra descriptive columns are harmless — seeder ignores them)
#
#     fault_detected strings MUST match the real fault_predictions.fault_label
#     values observed in the live DB snapshot:
#         "Coolant overheating", "Low oil pressure detected",
#         "Battery voltage drop", "Transmission overheat",
#         "Abnormal fuel trim drift", "EGR valve stuck open",
#         "Mass air flow sensor fault", "Engine misfire detected",
#         "Fuel injector fault"
# ---------------------------------------------------------------------------

def generate_maintenance_logs(
    metadata: pd.DataFrame, n_days: int, seed: int
) -> pd.DataFrame:
    rg    = rng(seed + 7777)
    start = pd.Timestamp(START_DATE)
    end   = start + pd.Timedelta(days=n_days)
    rows  = []

    fault_options = [lbl for lbl in FAULT_LABELS if lbl != "normal"]

    for _, row in metadata.iterrows():
        vid      = str(row["vehicle_id"])
        n_events = int(rg.integers(1, 5))   # 1–4 events per vehicle

        for evt_idx in range(n_events):
            event_date = start + pd.Timedelta(
                seconds=int(
                    rg.integers(0, int((end - start).total_seconds()))
                )
            )
            fault    = str(rg.choice(fault_options))
            mode     = str(rg.choice(MAINTENANCE_MODES))
            downtime = round(float(rg.uniform(1.0, 16.0)), 1)

            rows.append(
                {
                    "vehicle_id":            vid,
                    "service_date":          event_date.date().isoformat(),
                    "fault_detected":        fault,
                    "preventive_or_reactive": mode,
                    "downtime_hours":        downtime,
                    "action_taken":          str(rg.choice(MAINTENANCE_ACTIONS)),
                    "technician_notes":      (
                        f"Addressed '{fault}' during {mode} service. "
                        f"Downtime: {downtime}h."
                    ),
                    "parts_replaced": f"Part #{int(rg.integers(1000, 9999))}",
                    "cost_inr":       round(float(rg.uniform(500, 25_000)), 2),
                }
            )

    return (
        pd.DataFrame(rows)
        .sort_values(["vehicle_id", "service_date"])
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate FixSight synthetic dataset CSVs")
    p.add_argument("--out",          default="dataset",          help="Output directory (default: dataset/)")
    p.add_argument("--vehicles",     type=int, default=DEFAULT_VEHICLES, help=f"Number of vehicles (default: {DEFAULT_VEHICLES})")
    p.add_argument("--days",         type=int, default=DEFAULT_DAYS,     help=f"Days to simulate (default: {DEFAULT_DAYS})")
    p.add_argument("--seed",         type=int, default=DEFAULT_SEED,     help="Random seed (default: 42)")
    p.add_argument(
        "--sample-every", type=int, default=1,
        help="Keep 1-in-N telemetry rows (e.g. --sample-every 5 = 5× smaller file). Default: 1",
    )
    return p.parse_args()


def main() -> None:
    args    = parse_args()
    out_dir = PROJECT_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[generate_dataset] output dir  : {out_dir}")
    print(f"[generate_dataset] vehicles    : {args.vehicles}  (IDs: V001 … V{args.vehicles:03d})")
    print(f"[generate_dataset] days        : {args.days}  ({START_DATE} onward)")
    print(f"[generate_dataset] seed        : {args.seed}")
    print(f"[generate_dataset] sample_every: {args.sample_every}")
    print()

    # 1. Vehicle metadata
    print("Generating vehicle_metadata.csv …")
    metadata      = generate_vehicle_metadata(args.vehicles, args.seed)
    metadata_path = out_dir / "vehicle_metadata.csv"
    metadata.to_csv(metadata_path, index=False)
    print(f"  ✓ {metadata_path}  ({len(metadata)} rows)")
    print()

    # 2. Telemetry (written incrementally to keep RAM low)
    telem_path = out_dir / "telematics_data.csv"
    print(f"Generating telematics_data.csv …")
    total_telem = generate_telematics_data(
        metadata=    metadata,
        n_days=      args.days,
        seed=        args.seed,
        out_csv=     telem_path,
        sample_every=args.sample_every,
    )
    print(f"  ✓ {telem_path}  ({total_telem:,} rows)")
    print()

    # 3. Maintenance logs
    print("Generating maintenance_logs.csv …")
    maintenance      = generate_maintenance_logs(metadata, args.days, args.seed)
    maintenance_path = out_dir / "maintenance_logs.csv"
    maintenance.to_csv(maintenance_path, index=False)
    print(f"  ✓ {maintenance_path}  ({len(maintenance)} rows)")
    print()

    print("=" * 60)
    print("Dataset generation complete.")
    print(f"  {metadata_path.name:<35}  {len(metadata):>6} rows")
    print(f"  {telem_path.name:<35}  {total_telem:>6,} rows")
    print(f"  {maintenance_path.name:<35}  {len(maintenance):>6} rows")
    print()
    print("Next step:")
    print("  python scripts/seed_database.py")


if __name__ == "__main__":
    main()
