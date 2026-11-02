"""Alert dispatcher node: notify the fleet owner by SMS (real Twilio or mock)."""

from __future__ import annotations

from typing import Any, cast

from app.agents.nodes.maintenance_advisor import CRITICAL_RUL_HOURS
from app.agents.state import AgentState

HIGH = "HIGH"
MEDIUM = "MEDIUM"


# =========================================================
# POLICY
# =========================================================

def should_dispatch_sms(severity: str, probability: float, rul_hours: float | None = None) -> bool:
    severity = severity.upper().strip()

    if severity == HIGH:
        return True

    if severity == MEDIUM and probability >= 0.67:
        return True

    if rul_hours is not None and rul_hours < CRITICAL_RUL_HOURS:
        return True

    return False


def should_alert(state: AgentState) -> bool:
    """Routing predicate used by the graph."""
    if state.get("alert_suppressed"):
        return False
    rul = state.get("rul_hours")
    return should_dispatch_sms(
        str(state.get("severity", "LOW")),
        float(state.get("fault_probability", 0.0)),
        float(rul) if rul is not None else None,
    )


# =========================================================
# MESSAGE BUILDER
# =========================================================

def _booking_line(state: AgentState) -> str:
    center = state.get("selected_service_center")
    slot_time = state.get("scheduled_slot_time")
    if not center or not slot_time:
        return "Action: Immediate diagnostics recommended."
    return f"Service booked: {center.get('center_name')} on {str(slot_time).replace('T', ' ')[:16]}."


def build_alert_message(state: AgentState) -> str:
    vehicle_id = state.get("vehicle_id", "unknown")
    fault_label = state.get("fault_label", "Unknown fault")
    severity = state.get("severity", "LOW")
    probability = float(state.get("fault_probability", 0.0))
    rul = state.get("rul_hours")

    lines = [
        "FixSight Alert",
        f"Vehicle: {vehicle_id}",
        f"Fault: {fault_label}",
        f"Severity: {severity}",
        f"Confidence: {probability:.1%}",
    ]
    if rul is not None:
        lines.append(f"Est. remaining life: {float(rul):.0f}h")
    lines.append(_booking_line(state))
    return "\n".join(lines)


def build_mock_alert_message(state: AgentState) -> str:
    return "[MOCK] " + build_alert_message(state)


# =========================================================
# NODE
# =========================================================

def alert_dispatcher_node(state: AgentState) -> AgentState:
    from app.services.notification_service import NotificationService

    alert_mode = str(state.get("alert_mode", "mock")).lower()
    errors = list(state.get("errors", []))
    message = build_mock_alert_message(state) if alert_mode == "mock" else build_alert_message(state)

    result = NotificationService.send_sms(
        vehicle_id=state["vehicle_id"],
        message=message,
        mode=alert_mode,
        alert_type="fault",
        fault_prediction_id=state.get("fault_prediction_id"),
        severity="critical" if str(state.get("severity")) == HIGH else "warning",
        allow_real=state.get("allow_real_sms", True),
    )
    errors.extend(result.errors)

    next_state: dict[str, Any] = {
        **state,
        "errors": errors,
        "alert_log_id": result.alert_log_id,
        "alert_status": result.status,
        "alert_dispatched": result.dispatched,
        "alert_provider_message_id": result.provider_message_id,
        "alert_mode": alert_mode,
        "alert_message": message,
    }

    return cast(AgentState, next_state)
