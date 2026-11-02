"""Synthetic OBD-II telemetry with scripted fault scenarios for live simulation.

Baselines mirror scripts/generate_dataset.py. Each scenario ramps the sensors that
the fault classifier keys on (see scripts/train_model._derive_fault_label) past
their thresholds as `progress` goes 0 → 1.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

# Only faults the shipped classifier can actually detect. The training dataset never
# produces fuel-trim / EGR / injector readings past their rule thresholds, so those
# classes exist only as label noise and are not learned (see ml-models skill).
SCENARIOS = (
    "Coolant overheating",
    "Low oil pressure detected",
    "Battery voltage drop",
    "Transmission overheat",
    "Mass air flow sensor fault",
)

ROLLING_WINDOW = 30

_BASE_RPM = {"gasoline": 1800, "gasoline_turbo": 2100, "diesel": 1500, "hybrid": 1400}
_RPM_VARIANCE = {"aggressive": 650, "highway": 200, "normal": 350, "mixed": 380, "gentle": 150}
_COOLANT_BASE = {"diesel": 93, "gasoline": 90, "gasoline_turbo": 95, "hybrid": 82}
_SPEED_BASE = {"highway": 80, "normal": 35, "mixed": 50, "aggressive": 90, "gentle": 30}


def _ramp(progress: float) -> float:
    """Smoothstep so faults build gradually, then cross thresholds decisively."""
    p = min(max(progress, 0.0), 1.0)
    return p * p * (3 - 2 * p)


@dataclass
class VehicleSim:
    vehicle_id: str
    engine_type: str = "gasoline"
    driving_profile: str = "normal"
    engine_hours: float = 0.0
    wear: float = 0.1  # slow background degradation, 0..1
    scenario: str | None = None
    progress: float = 0.0
    notified: bool = False  # current fault episode already alerted/booked
    explanation: str | None = None  # LLM explanation for the current episode
    in_service: bool = False
    readings: int = 0
    coolant_hist: deque[float] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))
    oil_pressure_hist: deque[float] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))
    harsh_hist: deque[int] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))
    idle_hist: deque[float] = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))
    last_rpm: float | None = None

    def start_scenario(self, scenario: str, progress: float = 0.0) -> None:
        self.scenario = scenario
        self.progress = progress
        self.notified = False
        self.explanation = None

    def repair(self) -> None:
        """Called when a service completes: clear fault, partially restore wear."""
        self.scenario = None
        self.progress = 0.0
        self.notified = False
        self.explanation = None
        self.in_service = False
        self.wear = max(0.03, self.wear * 0.5)
        self.coolant_hist.clear()
        self.oil_pressure_hist.clear()

    def to_status(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "scenario": self.scenario,
            "progress": round(self.progress, 2),
            "notified": self.notified,
            "in_service": self.in_service,
            "readings": self.readings,
        }


def generate_reading(
    sim: VehicleSim,
    at: datetime,
    rng: random.Random,
    *,
    hours_elapsed: float = 1.0,
    progress_step: float = 0.15,
) -> dict[str, Any]:
    """Produce one telemetry payload (all TelemetryReadingCreate fields) and advance the sim."""
    nrng = np.random.default_rng(rng.randrange(2**32))
    s = _ramp(sim.progress) if sim.scenario else 0.0
    w = sim.wear

    base_rpm = _BASE_RPM.get(sim.engine_type, 1700)
    rpm = float(np.clip(base_rpm + nrng.normal(0, _RPM_VARIANCE.get(sim.driving_profile, 350) * 0.6) + w * 200, 800, 5000))
    engine_load = float(np.clip(nrng.uniform(25, 70) + w * 8, 10, 100))
    coolant = float(np.clip(nrng.normal(_COOLANT_BASE.get(sim.engine_type, 90), 2.5) + w * 6, 60, 130))
    oil_pressure = float(np.clip(nrng.normal(46, 3) - w * 5, 10, 80))
    fuel_rate = float(np.clip(nrng.uniform(4, 16) + w * 2, 0.5, 35))
    stft = float(np.clip(nrng.normal(0, 2) + w * 2, -30, 30))
    ltft = float(np.clip(nrng.normal(0, 1.5) + w * 2, -30, 30))
    maf = float(np.clip((rpm / 6000) * 200 + nrng.normal(0, 8), 10, 350))
    imp = float(np.clip(nrng.normal(85, 12) + w * 5, 30, 200))
    battery = float(np.clip(nrng.normal(12.6, 0.15) - w * 0.4, 9.0, 14.8))
    alternator = float(np.clip(nrng.normal(14.2, 0.2) - w * 0.2, 12.0, 15.5))
    gear = int(nrng.choice([1, 2, 3, 4, 5, 6], p=[0.05, 0.15, 0.25, 0.30, 0.20, 0.05]))
    trans_temp = float(np.clip(nrng.normal(80, 5) + w * 8, 40, 150))
    egr = float(np.clip(nrng.uniform(5, 50), 0, 100))

    scenario = sim.scenario
    if scenario == "Coolant overheating":
        coolant += 32 * s
    elif scenario == "Low oil pressure detected":
        oil_pressure = 46 - 30 * s + float(nrng.normal(0, 1))
    elif scenario == "Battery voltage drop":
        battery = 12.6 - 2.0 * s + float(nrng.normal(0, 0.05))
        alternator -= 1.0 * s
    elif scenario == "Transmission overheat":
        trans_temp = 80 + 52 * s + float(nrng.normal(0, 2))
        if s > 0.5:
            gear = max(gear, 3)
    elif scenario == "Mass air flow sensor fault":
        maf = maf * (1 - s) + 3.5 * s
        rpm = max(rpm, 1200.0)

    oil_temp = float(np.clip(coolant + nrng.normal(8, 2), 60, 160))
    speed = float(np.clip(nrng.normal(_SPEED_BASE.get(sim.driving_profile, 40), 15), 0, 200))
    throttle = float(np.clip(nrng.uniform(10, 60), 0, 100))

    sim.engine_hours += hours_elapsed
    sim.coolant_hist.append(coolant)
    sim.oil_pressure_hist.append(oil_pressure)
    rpm_jump = abs(rpm - sim.last_rpm) if sim.last_rpm is not None else 0.0
    sim.last_rpm = rpm
    sim.harsh_hist.append(1 if rpm_jump > 400 else 0)
    sim.idle_hist.append(1.0 if speed < 5 else 0.0)

    coolant_arr = np.array(sim.coolant_hist)
    oil_arr = np.array(sim.oil_pressure_hist)
    slope = float(np.polyfit(range(len(oil_arr)), oil_arr, 1)[0]) if len(oil_arr) > 1 else 0.0

    degradation = float(np.clip(w + 0.35 * s + nrng.normal(0, 0.01), 0, 1))
    health = float(np.clip(100 - degradation * 60 + nrng.normal(0, 1), 20, 100))

    sim.readings += 1
    sim.wear = min(0.6, sim.wear + 0.002 * hours_elapsed)
    if sim.scenario:
        sim.progress = min(1.0, sim.progress + progress_step)

    return {
        "timestamp": at.isoformat(),
        "engine_rpm": round(rpm, 2),
        "engine_load": round(engine_load, 2),
        "coolant_temperature": round(coolant, 2),
        "oil_temperature": round(oil_temp, 2),
        "oil_pressure": round(oil_pressure, 2),
        "fuel_rate": round(fuel_rate, 3),
        "short_term_fuel_trim": round(stft, 4),
        "long_term_fuel_trim": round(ltft, 4),
        "mass_air_flow": round(maf, 3),
        "intake_manifold_pressure": round(imp, 2),
        "battery_voltage": round(battery, 3),
        "alternator_voltage": round(alternator, 3),
        "gear_position": gear,
        "transmission_temperature": round(trans_temp, 2),
        "o2_sensor_voltage": round(float(nrng.uniform(0.1, 0.9)), 4),
        "egr_position": round(egr, 2),
        "vehicle_speed": round(speed, 2),
        "throttle_position": round(throttle, 2),
        "cumulative_engine_hours": round(sim.engine_hours, 2),
        "rolling_mean_temp": round(float(coolant_arr.mean()), 2),
        "rolling_std_temp": round(float(coolant_arr.std()) if len(coolant_arr) > 1 else 0.0, 3),
        "rolling_slope_oil_pressure": round(slope, 4),
        "harsh_acceleration_count": int(sum(sim.harsh_hist)),
        "idle_time_ratio": round(float(np.mean(sim.idle_hist)), 4),
        "degradation_index": round(degradation, 4),
        "health_score": round(health, 2),
        "rul_hours": 0.0,  # filled by the RUL model in the pipeline
    }
