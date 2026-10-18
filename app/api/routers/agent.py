"""Agent routers."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, status

from app.services.agent_service import AgentService

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run/{vehicle_id}", status_code=status.HTTP_200_OK)
def run_agent_pipeline(
    vehicle_id: str,
    telemetry_row: dict[str, Any] = Body(..., embed=True),
    alert_mode: str = Body("mock", embed=True),
    schedule_service: bool = Body(False, embed=True),
    preferred_time: str | None = Body(None, embed=True),
    duration_hours: float = Body(2.0, embed=True),
) -> dict[str, Any]:
    """Trigger the centralized orchestration graph and return final state."""
    try:
        result = AgentService.run_pipeline(
            vehicle_id,
            telemetry_row,
            alert_mode=alert_mode,
            schedule_service=schedule_service,
            preferred_time=preferred_time,
            duration_hours=duration_hours,
        )
        return dict(result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
