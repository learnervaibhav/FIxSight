"""Live fleet simulation: round-robin telemetry through the real agent pipeline.

Each tick advances a simulated clock, progresses service slots (PENDING → ACTIVE →
COMPLETED), then sends one generated reading for the next batch of vehicles through
AgentService. A *round* is complete when every vehicle has reported once.

Modes:
- ``mock``: SMS are logged and pushed to the dashboard as dev notifications.
- ``real``: SMS go through Twilio, capped by ``SIM_REAL_SMS_LIMIT`` per run.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.core.database import SessionLocal
from app.core.events import event_bus
from app.models import ServiceSlot, TelemetryReading, Vehicle
from app.models.service_slot import OPEN_SLOT_STATUSES
from app.simulation.telemetry_generator import SCENARIOS, VehicleSim, generate_reading

logger = logging.getLogger(__name__)

MODES = ("mock", "real")


@dataclass
class SimulationConfig:
    mode: str = "mock"
    tick_seconds: float = 3.0
    sim_minutes_per_tick: int = 20
    vehicles_per_tick: int = 5
    fault_rate: float = 0.04  # chance per reading that a healthy vehicle starts a fault scenario
    initial_fault_share: float = 0.3  # share of vehicles that start with a developing fault
    use_llm: bool = True
    seed: int | None = None


class SimulationEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._task: asyncio.Task[None] | None = None
        self.config = SimulationConfig()
        self.running = False
        self.vehicles: dict[str, VehicleSim] = {}
        self._order: list[str] = []
        self._cursor = 0
        self._rng = random.Random()
        self._reset_counters()

    # ------------------------------------------------------------------ state
    def _reset_counters(self) -> None:
        self.tick = 0
        self.round = 0
        self.sim_time: datetime | None = None
        self.started_at: datetime | None = None
        self.current_batch: list[str] = []
        self.last_tick_ms = 0
        self.last_error: str | None = None
        self.last_sms_error: str | None = None  # last Twilio failure, shown on the dashboard
        self.stats = {
            "readings": 0,
            "faults_detected": 0,
            "services_booked": 0,
            "services_started": 0,
            "services_completed": 0,
            "sms_sent": 0,
            "sms_mock": 0,
            "sms_failed": 0,
        }

    @staticmethod
    def sms_limit() -> int:
        return int(os.getenv("SIM_REAL_SMS_LIMIT", "10"))

    def status(self) -> dict[str, Any]:
        from app.agents.nodes.llm_reasoner import llm_configured
        from app.services.notification_service import twilio_configured

        with self._lock:
            n = len(self._order)
            return {
                "running": self.running,
                "mode": self.config.mode,
                "tick": self.tick,
                "round": self.round,
                "round_progress": round(self._cursor / n, 2) if n else 0.0,
                "sim_time": self.sim_time.isoformat() if self.sim_time else None,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "tick_seconds": self.config.tick_seconds,
                "sim_minutes_per_tick": self.config.sim_minutes_per_tick,
                "vehicles_per_tick": self.config.vehicles_per_tick,
                "use_llm": self.config.use_llm,
                "current_batch": list(self.current_batch),
                "last_tick_ms": self.last_tick_ms,
                "last_error": self.last_error,
                "last_sms_error": self.last_sms_error,
                "stats": dict(self.stats),
                "sms_limit": self.sms_limit(),
                "twilio_configured": twilio_configured(),
                "llm_configured": llm_configured(),
                "vehicles": [sim.to_status() for sim in self.vehicles.values()],
            }

    # --------------------------------------------------------------- control
    def _load_vehicles(self) -> None:
        with SessionLocal() as db:
            vehicles = db.query(Vehicle).order_by(Vehicle.vehicle_id).all()
            sims: dict[str, VehicleSim] = {}
            for vehicle in vehicles:
                existing = self.vehicles.get(vehicle.vehicle_id)
                if existing is not None:
                    sims[vehicle.vehicle_id] = existing
                    continue
                latest = (
                    db.query(TelemetryReading.cumulative_engine_hours, TelemetryReading.degradation_index)
                    .filter(TelemetryReading.vehicle_id == vehicle.vehicle_id)
                    .order_by(TelemetryReading.timestamp.desc())
                    .first()
                )
                sims[vehicle.vehicle_id] = VehicleSim(
                    vehicle_id=vehicle.vehicle_id,
                    engine_type=vehicle.engine_type,
                    driving_profile=vehicle.driving_profile,
                    engine_hours=float(latest[0]) if latest else 0.0,
                    wear=min(0.35, float(latest[1])) if latest else 0.1,
                )
            open_vehicle_ids = {
                row[0]
                for row in db.query(ServiceSlot.vehicle_id)
                .filter(ServiceSlot.slot_status == "ACTIVE")
                .all()
            }
        for vehicle_id, sim in sims.items():
            sim.in_service = vehicle_id in open_vehicle_ids
        self.vehicles = sims
        self._order = list(sims)

    def _ensure_vehicles(self) -> None:
        """Load the fleet; on a fresh run, give some vehicles a developing fault."""
        fresh = not self.vehicles
        self._load_vehicles()
        if not self._order:
            raise ValueError("No vehicles in the database. Run scripts/bootstrap.py first.")
        if fresh:
            self._seed_initial_faults()

    def _seed_initial_faults(self) -> None:
        healthy = [sim for sim in self.vehicles.values() if sim.scenario is None]
        count = round(len(self.vehicles) * self.config.initial_fault_share)
        for sim in self._rng.sample(healthy, min(count, len(healthy))):
            sim.start_scenario(self._rng.choice(SCENARIOS), progress=self._rng.uniform(0.0, 0.45))

    @staticmethod
    def _initial_clock() -> datetime:
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        if 7 <= now.hour < 16:
            return now
        day = now if now.hour < 7 else now + timedelta(days=1)
        return day.replace(hour=8)

    def start(self, config: SimulationConfig) -> dict[str, Any]:
        if config.mode not in MODES:
            raise ValueError("mode must be 'mock' or 'real'")
        loop = asyncio.get_running_loop()  # must be called from an async endpoint
        with self._lock:
            if self.running:
                # Allow switching mode/speed on the fly.
                self.config = config
                event_bus.publish("simulation", "Simulation updated", f"Mode {config.mode}, tick {config.tick_seconds}s")
                return self.status()

            self.config = config
            if not self.vehicles:
                self._rng = random.Random(config.seed)
            self._ensure_vehicles()
            if self.sim_time is None:
                self.sim_time = self._initial_clock()
                self.started_at = datetime.now()
            self.running = True
            self._task = loop.create_task(self._run())

        event_bus.publish(
            "simulation",
            f"Simulation started ({config.mode})",
            f"{len(self._order)} vehicles, {config.vehicles_per_tick} per tick every {config.tick_seconds}s",
            severity="success",
            data={"mode": config.mode},
        )
        return self.status()

    async def stop(self) -> dict[str, Any]:
        with self._lock:
            self.running = False
            task = self._task
            self._task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        event_bus.publish("simulation", "Simulation stopped", f"Stopped at tick {self.tick}, round {self.round}")
        return self.status()

    async def reset(self) -> dict[str, Any]:
        """Stop, cancel open service slots, and forget per-vehicle simulation state."""
        await self.stop()
        from app.services import ServiceSchedulingService

        with SessionLocal() as db:
            open_slots = db.query(ServiceSlot).filter(ServiceSlot.slot_status.in_(OPEN_SLOT_STATUSES)).all()
            for slot in open_slots:
                slot.slot_status = "CANCELLED"
            db.commit()
            ServiceSchedulingService.recompute_occupancy(db)
        with self._lock:
            self.vehicles = {}
            self._order = []
            self._cursor = 0
            self._reset_counters()
        event_bus.publish("simulation", "Simulation reset", f"Cancelled {len(open_slots)} open service slots")
        return self.status()

    # ------------------------------------------------------------------ loop
    async def _run(self) -> None:
        while self.running:
            started = time.perf_counter()
            try:
                await asyncio.to_thread(self.run_tick)
                self.last_error = None
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # keep the loop alive; surface the error in status
                self.last_error = str(exc)
                logger.exception("Simulation tick failed")
            self.last_tick_ms = int((time.perf_counter() - started) * 1000)
            await asyncio.sleep(max(0.2, self.config.tick_seconds - self.last_tick_ms / 1000))

    def run_tick(self) -> None:
        """Advance one tick synchronously (also used directly by tests)."""
        with self._lock:
            if not self._order:
                self._ensure_vehicles()
            if self.sim_time is None:
                self.sim_time = self._initial_clock()
                self.started_at = datetime.now()
            self.sim_time += timedelta(minutes=self.config.sim_minutes_per_tick)
            self.tick += 1

            batch: list[str] = []
            size = max(1, min(self.config.vehicles_per_tick, len(self._order)))
            for _ in range(size):
                batch.append(self._order[self._cursor])
                self._cursor += 1
                if self._cursor >= len(self._order):
                    self._cursor = 0
                    self.round += 1
            self.current_batch = batch
            sim_time = self.sim_time

        self._advance_service_slots(sim_time)
        hours_elapsed = self.config.sim_minutes_per_tick * len(self._order) / max(1, len(batch)) / 60
        for vehicle_id in batch:
            self._process_vehicle(self.vehicles[vehicle_id], sim_time, hours_elapsed)

    def _sms_allowed(self) -> bool:
        return self.config.mode != "real" or self.stats["sms_sent"] < self.sms_limit()

    def _count_sms(self, status: str | None, errors: list[str] | None = None) -> None:
        if status == "sent":
            self.stats["sms_sent"] += 1
            self.last_sms_error = None
        elif status == "mock_sent":
            self.stats["sms_mock"] += 1
        elif status in {"failed", "not_configured"}:
            self.stats["sms_failed"] = self.stats.get("sms_failed", 0) + 1
            twilio_errors = [error for error in (errors or []) if "Twilio" in error]
            self.last_sms_error = twilio_errors[-1] if twilio_errors else f"SMS {status}"

    def _advance_service_slots(self, sim_time: datetime) -> None:
        from app.services import ServiceSchedulingService
        from app.services.notification_service import NotificationService

        with SessionLocal() as db:
            slots = db.query(ServiceSlot).filter(ServiceSlot.slot_status.in_(OPEN_SLOT_STATUSES)).all()
            for slot in slots:
                center_name = slot.service_center.center_name
                end_time = slot.scheduled_time + timedelta(hours=float(slot.duration_hours))
                sim = self.vehicles.get(slot.vehicle_id)

                if slot.slot_status == "PENDING" and sim_time >= slot.scheduled_time:
                    ServiceSchedulingService.update_slot_status(db, slot.slot_id, "ACTIVE")
                    if sim:
                        sim.in_service = True
                    self.stats["services_started"] += 1
                    event_bus.publish(
                        "service_started",
                        "Service in progress",
                        f"{slot.vehicle_id} checked in at {center_name}",
                        severity="info",
                        vehicle_id=slot.vehicle_id,
                        data={"slot_id": slot.slot_id, "center_id": slot.center_id},
                    )

                if slot.slot_status == "ACTIVE" and sim_time >= end_time:
                    ServiceSchedulingService.update_slot_status(db, slot.slot_id, "COMPLETED", at=sim_time)
                    if sim:
                        sim.repair()
                    self.stats["services_completed"] += 1
                    event_bus.publish(
                        "service_completed",
                        "Service completed",
                        f"{slot.vehicle_id} finished at {center_name}: {slot.reason or 'maintenance'}",
                        severity="success",
                        vehicle_id=slot.vehicle_id,
                        data={"slot_id": slot.slot_id, "center_id": slot.center_id},
                    )
                    prefix = "[MOCK] " if self.config.mode == "mock" else ""
                    result = NotificationService.send_sms(
                        vehicle_id=slot.vehicle_id,
                        message=f"{prefix}FixSight: Your vehicle {slot.vehicle_id} maintenance at {center_name} is complete. Thank you!",
                        mode=self.config.mode,
                        alert_type="service_completed",
                        severity="success",
                        allow_real=self._sms_allowed(),
                    )
                    self._count_sms(result.status, result.errors)

    def _process_vehicle(self, sim: VehicleSim, sim_time: datetime, hours_elapsed: float) -> None:
        from app.services import AgentService

        if sim.in_service:
            return  # vehicle is at the workshop; no telemetry

        if sim.scenario is None and self._rng.random() < self.config.fault_rate:
            sim.start_scenario(self._rng.choice(SCENARIOS))

        payload = generate_reading(sim, sim_time, self._rng, hours_elapsed=hours_elapsed)
        result = AgentService.run_pipeline(
            sim.vehicle_id,
            payload,
            alert_mode=self.config.mode,
            llm_enabled=self.config.use_llm and not sim.notified,
            alert_suppressed=sim.notified,
            allow_real_sms=self._sms_allowed(),
            simulation_time=sim_time.isoformat(),
            explanation_hint=sim.explanation if sim.notified else None,
        )
        self.stats["readings"] += 1

        severity = result.get("severity")
        if result.get("is_fault") and severity in {"HIGH", "MEDIUM"} and not sim.notified:
            self.stats["faults_detected"] += 1
        if result.get("service_booking_status") == "booked":
            self.stats["services_booked"] += 1
        if result.get("alert_dispatched") or result.get("service_booking_status") in {"booked", "existing"}:
            if not sim.notified:
                sim.explanation = result.get("llm_explanation")
            sim.notified = True
        self._count_sms(result.get("alert_status"), result.get("errors"))


simulation_engine = SimulationEngine()
