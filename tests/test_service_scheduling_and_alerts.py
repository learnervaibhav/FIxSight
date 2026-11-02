from __future__ import annotations

from datetime import datetime

import pytest

from app.agents.nodes.alert_dispatcher import build_alert_message, should_dispatch_sms
from app.core.database import SessionLocal
from app.models import AlertLog, ServiceCenter
from app.services import NotificationService, ServiceSchedulingService
from app.services.service_scheduling_service import haversine_km, next_opening


def test_should_dispatch_sms_for_high_severity() -> None:
    assert should_dispatch_sms("HIGH", 0.9) is True


def test_should_not_dispatch_sms_for_low_severity() -> None:
    assert should_dispatch_sms("LOW", 0.2) is False


def test_should_dispatch_sms_for_critical_rul() -> None:
    assert should_dispatch_sms("LOW", 0.1, rul_hours=10) is True


def test_build_alert_message_contains_vehicle_fault_and_booking() -> None:
    state = {
        "vehicle_id": "V1",
        "fault_label": "Engine overheat",
        "severity": "HIGH",
        "fault_probability": 0.92,
        "selected_service_center": {"center_name": "Near Hub"},
        "scheduled_slot_time": "2026-01-01T10:00:00",
    }
    message = build_alert_message(state)
    assert "V1" in message
    assert "Engine overheat" in message
    assert "Near Hub" in message


def test_haversine_known_distance() -> None:
    # Connaught Place -> Gurugram is roughly 23 km.
    assert 20 < haversine_km(28.6329, 77.2197, 28.4595, 77.0266) < 27


def test_next_opening_respects_operating_hours() -> None:
    center = ServiceCenter(operating_hours_start=9, operating_hours_end=18)
    assert next_opening(center, datetime(2026, 1, 1, 6, 30), 2) == datetime(2026, 1, 1, 9)
    assert next_opening(center, datetime(2026, 1, 1, 12, 10), 2) == datetime(2026, 1, 1, 13)
    assert next_opening(center, datetime(2026, 1, 1, 17, 0), 2) == datetime(2026, 1, 2, 9)


def test_schedule_service_slot_creates_slot_and_updates_occupancy() -> None:
    with SessionLocal() as db:
        slot = ServiceSchedulingService.create_service_slot(
            db,
            vehicle_id="TEST-VEH-1",
            center_id="CENTER-FAR",
            scheduled_time=datetime(2026, 1, 1, 10),
            duration_hours=2.0,
        )
        assert slot.slot_status == "PENDING"
        assert db.get(ServiceCenter, "CENTER-FAR").current_occupancy == 1

        ServiceSchedulingService.update_slot_status(db, slot.slot_id, "COMPLETED")
        assert db.get(ServiceCenter, "CENTER-FAR").current_occupancy == 0


def test_schedule_rejects_time_outside_operating_hours() -> None:
    with SessionLocal() as db, pytest.raises(ValueError, match="open"):
        ServiceSchedulingService.create_service_slot(
            db, vehicle_id="TEST-VEH-1", center_id="CENTER-FAR", scheduled_time=datetime(2026, 1, 1, 20)
        )


def test_auto_booking_picks_nearest_then_falls_back_when_full() -> None:
    with SessionLocal() as db:
        first = ServiceSchedulingService.create_slot_for_vehicle(db, vehicle_id="TEST-VEH-1", preferred_time=datetime(2026, 1, 1, 8))
        assert first["center_id"] == "CENTER-NEAR"
        assert first["scheduled_time"] == "2026-01-01T09:00:00"

        # Near hub has capacity 1, so the next booking goes to the far hub.
        second = ServiceSchedulingService.create_slot_for_vehicle(db, vehicle_id="TEST-VEH-1", preferred_time=datetime(2026, 1, 1, 8))
        assert second["center_id"] == "CENTER-FAR"


def test_mock_notification_is_logged() -> None:
    result = NotificationService.send_sms(vehicle_id="TEST-VEH-1", message="hello", mode="mock")
    assert result.status == "mock_sent"
    with SessionLocal() as db:
        assert db.get(AlertLog, result.alert_log_id).alert_message == "hello"


def test_real_notification_without_twilio_is_not_configured() -> None:
    result = NotificationService.send_sms(vehicle_id="TEST-VEH-1", message="hello", mode="real")
    assert result.status == "not_configured"
    assert not result.dispatched


class _FakeMessages:
    def __init__(self, calls: list[dict], error: Exception | None = None) -> None:
        self.calls = calls
        self.error = error

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return type("Msg", (), {"sid": "SM123"})()


def _fake_twilio(monkeypatch, calls: list[dict], error: Exception | None = None) -> None:
    import twilio.rest

    class FakeClient:
        def __init__(self, *_args) -> None:
            self.messages = _FakeMessages(calls, error)

    monkeypatch.setattr(twilio.rest, "Client", FakeClient)


def _twilio_env(monkeypatch, **overrides: str) -> None:
    env = {
        "TWILIO_ACCOUNT_SID": "ACtest",
        "TWILIO_AUTH_TOKEN": "token",
        "TWILIO_FROM_NUMBER": "+15550000000",
        "TWILIO_MESSAGING_SERVICE_SID": "",
        "ALERT_SMS_TO": "+919800000000",
        **overrides,
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def test_real_sms_prefers_messaging_service(monkeypatch) -> None:
    calls: list[dict] = []
    _fake_twilio(monkeypatch, calls)
    _twilio_env(monkeypatch, TWILIO_MESSAGING_SERVICE_SID="MGtest", TWILIO_FROM_NUMBER="")

    result = NotificationService.send_sms(vehicle_id="TEST-VEH-1", message="hi", mode="real")

    assert result.status == "sent"
    assert calls == [{"body": "hi", "messaging_service_sid": "MGtest", "to": "+919800000000"}]


def test_real_sms_uses_from_number_without_messaging_service(monkeypatch) -> None:
    calls: list[dict] = []
    _fake_twilio(monkeypatch, calls)
    _twilio_env(monkeypatch)

    assert NotificationService.send_sms(vehicle_id="TEST-VEH-1", message="hi", mode="real").status == "sent"
    assert calls[0]["from_"] == "+15550000000"


def test_real_sms_failure_reports_actionable_twilio_error(monkeypatch) -> None:
    from twilio.base.exceptions import TwilioRestException

    error = TwilioRestException(400, "https://api.twilio.com", msg="'From' is not a Twilio phone number", code=21659)
    _fake_twilio(monkeypatch, [], error)
    _twilio_env(monkeypatch)

    result = NotificationService.send_sms(vehicle_id="TEST-VEH-1", message="hi", mode="real")

    assert result.status == "failed"
    assert "21659" in result.errors[0] and "TWILIO_MESSAGING_SERVICE_SID" in result.errors[0]
