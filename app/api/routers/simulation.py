"""Simulation control and live event feed endpoints."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.core.events import event_bus
from app.schemas import EventListResponse, EventResponse, SimulationStartRequest
from app.simulation.engine import SimulationConfig, simulation_engine

router = APIRouter(tags=["simulation"])


@router.get("/simulation/status")
def simulation_status() -> dict[str, Any]:
    return simulation_engine.status()


@router.get("/simulation/twilio-check")
async def twilio_check() -> dict[str, Any]:
    """Read-only Twilio diagnosis for Real mode (no SMS is sent)."""
    from app.services.notification_service import check_twilio

    return await asyncio.to_thread(check_twilio)


@router.post("/simulation/start")
async def start_simulation(payload: SimulationStartRequest) -> dict[str, Any]:
    """Start (or reconfigure) the live simulation in `mock` or `real` SMS mode."""
    try:
        return simulation_engine.start(SimulationConfig(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/simulation/stop")
async def stop_simulation() -> dict[str, Any]:
    return await simulation_engine.stop()


@router.post("/simulation/reset")
async def reset_simulation() -> dict[str, Any]:
    """Stop and cancel all open service slots so the next run starts clean."""
    return await simulation_engine.reset()


@router.post("/simulation/tick")
async def single_tick() -> dict[str, Any]:
    """Advance exactly one tick (useful for step-by-step demos)."""
    if simulation_engine.running:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stop the simulation before stepping")
    await asyncio.to_thread(simulation_engine.run_tick)
    return simulation_engine.status()


@router.get("/events", response_model=EventListResponse)
def list_events(after_id: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)) -> EventListResponse:
    """Live events after `after_id` (poll with the returned `last_id`)."""
    events = event_bus.since(after_id, limit)
    return EventListResponse(events=[EventResponse(**event.to_dict()) for event in events], last_id=event_bus.last_id)
