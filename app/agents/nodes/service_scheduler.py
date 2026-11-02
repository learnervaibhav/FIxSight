"""Service scheduler node: book the nearest open service center for a faulty vehicle."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from app.agents.state import AgentState
from app.core.database import SessionLocal
from app.core.events import event_bus

# Service length by severity (hours).
DURATION_BY_SEVERITY = {"HIGH": 3.0, "MEDIUM": 2.0, "LOW": 1.0}


def needs_service(state: AgentState) -> bool:
    """Routing predicate: should the pipeline try to book a service slot?"""
    if state.get("schedule_service"):
        return True
    if not state.get("auto_schedule", True):
        return False
    return state.get("maintenance_priority") in {"P1", "P2"}


def _reference_time(state: AgentState) -> datetime:
    for key in ("user_preferred_date", "simulation_time"):
        value = state.get(key)
        if value:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    return datetime.now()


def service_scheduler_node(state: AgentState) -> AgentState:
    """Reuse an open slot, or book the nearest center (10 km radius first) at its next opening."""
    from app.services import ServiceSchedulingService

    vehicle_id = state["vehicle_id"]
    errors = list(state.get("errors", []))
    severity = str(state.get("severity", "LOW"))
    duration_minutes = state.get("service_duration_minutes")
    duration_hours = duration_minutes / 60 if duration_minutes else DURATION_BY_SEVERITY.get(severity, 2.0)
    reason = str(state.get("fault_label", "Preventive maintenance"))
    if reason == "normal":
        reason = "Low remaining useful life"

    with SessionLocal() as db:
        existing = ServiceSchedulingService.get_open_slot(db, vehicle_id)
        if existing is not None:
            center = existing.service_center
            return cast(
                AgentState,
                {
                    **state,
                    "service_booking_status": "existing",
                    "selected_service_center": {
                        "center_id": center.center_id,
                        "center_name": center.center_name,
                        "location": center.location,
                        "latitude": center.latitude,
                        "longitude": center.longitude,
                    },
                    "scheduled_slot_time": existing.scheduled_time.isoformat(),
                    "service_slot_id": existing.slot_id,
                    "service_slot_status": existing.slot_status,
                },
            )

        try:
            booking = ServiceSchedulingService.create_slot_for_vehicle(
                db,
                vehicle_id=vehicle_id,
                preferred_time=_reference_time(state),
                duration_hours=duration_hours,
                reason=reason,
            )
        except ValueError as exc:
            errors.append(f"service_scheduler_node: {exc}")
            event_bus.publish(
                "service_unavailable",
                "No service slot available",
                f"{vehicle_id}: {exc}",
                severity="warning",
                vehicle_id=vehicle_id,
            )
            return cast(AgentState, {**state, "errors": errors, "service_booking_status": "unavailable"})

    event_bus.publish(
        "service_booked",
        "Service booked",
        f"{vehicle_id} booked at {booking['center_name']} ({booking['distance_km']} km) "
        f"for {booking['scheduled_time'].replace('T', ' ')[:16]} — {reason}",
        severity="success",
        vehicle_id=vehicle_id,
        data=booking,
    )

    center_keys = ("center_id", "center_name", "location", "latitude", "longitude", "distance_km")
    return cast(
        AgentState,
        {
            **state,
            "service_booking_status": "booked",
            "selected_service_center": {key: booking[key] for key in center_keys},
            "scheduled_slot_time": booking["scheduled_time"],
            "service_slot_id": booking["slot_id"],
            "service_slot_status": booking["slot_status"],
        },
    )
