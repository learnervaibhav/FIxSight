from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional, cast

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.agents.state import AgentState
from app.core.database import SessionLocal
from app.models import AlertLog

logger = logging.getLogger(__name__)


# =========================================================
# CONFIG
# =========================================================

HIGH = "HIGH"
MEDIUM = "MEDIUM"


@dataclass(slots=True)
class TwilioConfig:
    account_sid: str
    auth_token: str
    from_number: str
    recipient: str

    @classmethod
    def from_env(cls) -> Optional["TwilioConfig"]:
        sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
        recipient = os.getenv("ALERT_SMS_TO", "").strip()

        if not all([sid, token, from_number, recipient]):
            return None

        return cls(
            account_sid=sid,
            auth_token=token,
            from_number=from_number,
            recipient=recipient,
        )


# =========================================================
# POLICY
# =========================================================

def should_dispatch_sms(severity: str, probability: float) -> bool:
    severity = severity.upper().strip()

    if severity == HIGH:
        return True

    if severity == MEDIUM and probability >= 0.67:
        return True

    return False


# =========================================================
# MESSAGE BUILDER
# =========================================================

def build_alert_message(state: AgentState) -> str:
    vehicle_id = state.get("vehicle_id", "unknown")
    fault_label = state.get("fault_label", "Unknown fault")
    severity = state.get("severity", "LOW")
    probability = float(state.get("fault_probability", 0.0))

    return (
        f"FixSight Alert\n"
        f"Vehicle: {vehicle_id}\n"
        f"Fault: {fault_label}\n"
        f"Severity: {severity}\n"
        f"Confidence: {probability:.1%}\n"
        f"Action: Immediate diagnostics recommended."
    )


def build_mock_alert_message(state: AgentState) -> str:
    vehicle_id = state.get("vehicle_id", "unknown")
    fault_label = state.get("fault_label", "Unknown fault")
    severity = state.get("severity", "LOW")
    return (
        f"[MOCK] FixSight Alert\n"
        f"Vehicle: {vehicle_id}\n"
        f"Fault: {fault_label}\n"
        f"Severity: {severity}\n"
        f"Action: Simulation mode enabled. No real SMS sent."
    )


# =========================================================
# TWILIO PROVIDER
# =========================================================

class TwilioSMSProvider:
    def __init__(self, config: TwilioConfig) -> None:
        self.client = Client(
            config.account_sid,
            config.auth_token,
        )
        self.config = config

    def send_sms(self, message: str) -> str:
        response = self.client.messages.create(
            body=message,
            from_=self.config.from_number,
            to=self.config.recipient,
        )

        return str(response.sid)


# =========================================================
# DATABASE
# =========================================================

def persist_alert_log(
    *,
    state: AgentState,
    recipient: Optional[str],
    status: str,
    message: str,
) -> int:
    with SessionLocal() as db:
        try:
            alert = AlertLog(
                vehicle_id=state["vehicle_id"],
                fault_prediction_id=state.get("fault_prediction_id"),
                channel="sms",
                recipient=recipient,
                status=status,
                alert_message=message,
            )

            db.add(alert)
            db.commit()
            db.refresh(alert)

            return int(alert.id)

        except Exception:
            db.rollback()
            logger.exception("Failed to persist alert log")
            raise


# =========================================================
# NODE
# =========================================================

def alert_dispatcher_node(state: AgentState) -> AgentState:
    severity = str(state.get("severity", "LOW"))
    probability = float(state.get("fault_probability", 0.0))
    alert_mode = str(state.get("alert_mode", "mock")).lower()

    errors = list(state.get("errors", []))

    message = build_mock_alert_message(state) if alert_mode == "mock" else build_alert_message(state)

    status = "skipped"
    provider_message_id: Optional[str] = None

    config = None
    recipient = None
    if alert_mode == "real":
        config = TwilioConfig.from_env()
        recipient = config.recipient if config else None

    dispatch_required = should_dispatch_sms(severity, probability)

    if dispatch_required and alert_mode == "mock":
        status = "mock_sent"
    elif dispatch_required and alert_mode == "real":
        if not config:
            status = "not_configured"
            logger.warning("Twilio configuration missing")
        else:
            try:
                provider = TwilioSMSProvider(config)
                provider_message_id = provider.send_sms(message)
                status = "sent"
                logger.info(
                    "SMS alert sent successfully",
                    extra={
                        "vehicle_id": state.get("vehicle_id"),
                        "message_sid": provider_message_id,
                    },
                )
            except TwilioRestException as exc:
                status = "failed"
                error_msg = f"Twilio API error: {exc}"
                errors.append(error_msg)
                logger.exception(error_msg)
            except Exception as exc:
                status = "failed"
                error_msg = f"Unexpected alert dispatcher error: {exc}"
                errors.append(error_msg)
                logger.exception(error_msg)
    elif alert_mode == "mock":
        status = "mock_skipped"

    alert_log_id = persist_alert_log(
        state=state,
        recipient=recipient,
        status=status,
        message=message,
    )

    next_state: dict[str, Any] = {
        **state,
        "errors": errors,
        "alert_log_id": alert_log_id,
        "alert_status": status,
        "alert_dispatched": status in {"sent", "mock_sent"},
        "alert_provider_message_id": provider_message_id,
        "alert_mode": alert_mode,
        "alert_message": message,
    }

    return cast(AgentState, next_state)