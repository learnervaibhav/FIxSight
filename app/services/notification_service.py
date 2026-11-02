"""SMS notification delivery (Twilio or mock) with alert-log persistence."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from app.core.database import SessionLocal
from app.core.events import event_bus
from app.models import AlertLog

logger = logging.getLogger(__name__)

MODE_MOCK = "mock"
MODE_REAL = "real"


@dataclass(slots=True)
class TwilioConfig:
    account_sid: str
    auth_token: str
    recipient: str
    from_number: str = ""
    messaging_service_sid: str = ""  # MG...; preferred over from_number when set

    @classmethod
    def from_env(cls) -> TwilioConfig | None:
        sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
        messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "").strip()
        recipient = os.getenv("ALERT_SMS_TO", "").strip()

        # A sender is either a Messaging Service or a Twilio phone number owned by this account.
        if not all([sid, token, recipient]) or not (messaging_service_sid or from_number):
            return None

        return cls(
            account_sid=sid,
            auth_token=token,
            recipient=recipient,
            from_number=from_number,
            messaging_service_sid=messaging_service_sid,
        )

    @property
    def sender(self) -> str:
        return f"messaging service {self.messaging_service_sid}" if self.messaging_service_sid else self.from_number


def twilio_configured() -> bool:
    return TwilioConfig.from_env() is not None


def check_twilio() -> dict[str, object]:
    """Read-only diagnosis of the Twilio setup (sends nothing): account, sender and recipient."""
    config = TwilioConfig.from_env()
    if config is None:
        return {"ok": False, "issues": ["Twilio is not configured: set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, ALERT_SMS_TO and a sender"]}

    from twilio.rest import Client

    issues: list[str] = []
    report: dict[str, object] = {"sender": config.sender, "recipient": config.recipient}
    try:
        client = Client(config.account_sid, config.auth_token)
        account = client.api.v2010.accounts(config.account_sid).fetch()
        report.update(account_status=account.status, account_type=account.type)
        if account.status != "active":
            issues.append(f"Twilio account is {account.status}")

        owned = [number.phone_number for number in client.incoming_phone_numbers.list(limit=50)]
        report["owned_numbers"] = owned
        if config.messaging_service_sid:
            senders = [n.phone_number for n in client.messaging.v1.services(config.messaging_service_sid).phone_numbers.list(limit=50)]
            report["messaging_service_senders"] = senders
            if not senders:
                issues.append("The Messaging Service has no phone numbers: add a Twilio number to it in the Twilio console")
        elif config.from_number not in owned:
            issues.append(
                f"TWILIO_FROM_NUMBER {config.from_number} is not owned by this Twilio account "
                f"(owned: {', '.join(owned) or 'none'}). Get a number in the Twilio console and update app/core/.env"
            )

        if account.type == "Trial":
            verified = [caller.phone_number for caller in client.outgoing_caller_ids.list(limit=50)]
            if config.recipient not in verified:
                issues.append(f"Trial account: ALERT_SMS_TO {config.recipient} is not a verified number")
    except Exception as exc:  # network / auth problems
        issues.append(_describe_twilio_error(exc))

    report["issues"] = issues
    report["ok"] = not issues
    return report


@dataclass
class NotificationResult:
    alert_log_id: int
    status: str  # sent / mock_sent / failed / not_configured / rate_limited
    recipient: str | None
    provider_message_id: str | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def dispatched(self) -> bool:
        return self.status in {"sent", "mock_sent"}


def _send_twilio(config: TwilioConfig, message: str) -> str:
    # Imported lazily so mock mode works without network/twilio setup.
    from twilio.rest import Client

    client = Client(config.account_sid, config.auth_token)
    if config.messaging_service_sid:
        response = client.messages.create(body=message, messaging_service_sid=config.messaging_service_sid, to=config.recipient)
    else:
        response = client.messages.create(body=message, from_=config.from_number, to=config.recipient)
    return str(response.sid)


def _describe_twilio_error(exc: Exception) -> str:
    """Short, actionable text for the dashboard (full traceback stays in the logs)."""
    code = getattr(exc, "code", None)
    detail = getattr(exc, "msg", None) or str(exc)
    hints = {
        21659: "TWILIO_FROM_NUMBER is not a number owned by this Twilio account; set TWILIO_MESSAGING_SERVICE_SID or fix the From number",
        21608: "Trial account: ALERT_SMS_TO must be a verified number in Twilio",
        21211: "ALERT_SMS_TO is not a valid phone number (use E.164, e.g. +91XXXXXXXXXX)",
        20003: "Twilio authentication failed: check TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN",
    }
    hint = hints.get(code) if isinstance(code, int) else None
    return f"Twilio error {code}: {hint or detail}" if code else f"Twilio error: {detail}"


class NotificationService:
    """Send an SMS in `real` mode or log/publish it in `mock` mode, always persisting an AlertLog."""

    @staticmethod
    def send_sms(
        *,
        vehicle_id: str,
        message: str,
        mode: str = MODE_MOCK,
        alert_type: str = "fault",
        fault_prediction_id: int | None = None,
        severity: str = "info",
        allow_real: bool = True,
    ) -> NotificationResult:
        mode = (mode or MODE_MOCK).lower()
        errors: list[str] = []
        provider_message_id: str | None = None
        recipient: str | None = None

        if mode == MODE_REAL:
            config = TwilioConfig.from_env()
            if config is None:
                status = "not_configured"
                errors.append("Twilio is not configured (TWILIO_* / ALERT_SMS_TO missing)")
            elif not allow_real:
                status = "rate_limited"
                recipient = config.recipient
            else:
                recipient = config.recipient
                try:
                    provider_message_id = _send_twilio(config, message)
                    status = "sent"
                    logger.info("SMS sent to %s for %s (sid=%s)", recipient, vehicle_id, provider_message_id)
                except Exception as exc:  # Twilio errors must never break the pipeline
                    status = "failed"
                    errors.append(_describe_twilio_error(exc))
                    logger.exception("Twilio SMS failed for %s via %s", vehicle_id, config.sender)
        else:
            status = "mock_sent"
            recipient = "dev-console"
            logger.info("[MOCK SMS] %s\n%s", vehicle_id, message)

        with SessionLocal() as db:
            alert = AlertLog(
                vehicle_id=vehicle_id,
                fault_prediction_id=fault_prediction_id,
                alert_type=alert_type,
                channel="sms",
                recipient=recipient,
                status=status,
                alert_message=message,
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            alert_log_id = int(alert.id)

        failed = status not in {"sent", "mock_sent"}
        event_bus.publish(
            "notification",
            "SMS sent" if status == "sent" else ("Mock SMS (dev)" if status == "mock_sent" else f"SMS {status.replace('_', ' ')}"),
            # On failure show why, so a misconfigured Twilio account is obvious in the UI.
            f"{'; '.join(errors) or status}\n\n{message}" if failed else message,
            severity=severity if not failed else "critical",
            vehicle_id=vehicle_id,
            data={
                "mode": mode,
                "status": status,
                "alert_type": alert_type,
                "alert_log_id": alert_log_id,
                "recipient": recipient,
                "errors": errors,
            },
        )

        return NotificationResult(
            alert_log_id=alert_log_id,
            status=status,
            recipient=recipient,
            provider_message_id=provider_message_id,
            errors=errors,
        )
