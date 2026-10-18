from __future__ import annotations

from datetime import datetime, timedelta

from app.agents.nodes.alert_dispatcher import build_alert_message, should_dispatch_sms
from app.services.service_scheduling_service import ServiceSchedulingService
from app.core.database import SessionLocal
from app.models import ServiceCenter, ServiceSlot, Vehicle


def test_should_dispatch_sms_for_high_severity() -> None:
    assert should_dispatch_sms("HIGH", 0.9) is True


def test_should_not_dispatch_sms_for_low_severity() -> None:
    assert should_dispatch_sms("LOW", 0.2) is False


def test_build_alert_message_contains_vehicle_and_fault() -> None:
    state = {"vehicle_id": "V1", "fault_label": "Engine overheat", "severity": "HIGH", "fault_probability": 0.92}
    message = build_alert_message(state)
    assert "V1" in message
    assert "Engine overheat" in message


def test_schedule_service_slot_creates_slot() -> None:
    db = SessionLocal()
    try:
        vehicle = Vehicle(
            vehicle_id="TEST-VEH-1",
            user_id="user-1",
            location="Delhi",
            manufacture_year=2022,
            initial_odometer=12000,
            engine_type="petrol",
            driving_profile="urban",
            region="north",
            average_daily_distance=45.5,
        )
        center = ServiceCenter(
            center_id="CENTER-1",
            center_name="North Service Hub",
            location="Delhi",
            latitude=28.61,
            longitude=77.21,
            operating_hours_start=9,
            operating_hours_end=18,
            max_capacity=10,
            current_occupancy=0,
        )
        db.add_all([vehicle, center])
        db.commit()

        scheduled_time = datetime.utcnow() + timedelta(days=1)
        slot = ServiceSchedulingService.create_service_slot(
            db=db,
            vehicle_id="TEST-VEH-1",
            center_id="CENTER-1",
            scheduled_time=scheduled_time,
            duration_hours=2.0,
        )

        assert slot.vehicle_id == "TEST-VEH-1"
        assert slot.center_id == "CENTER-1"
        assert slot.slot_status == "PENDING"
    finally:
        db.query(ServiceSlot).filter(ServiceSlot.vehicle_id == "TEST-VEH-1").delete()
        db.query(ServiceCenter).filter(ServiceCenter.center_id == "CENTER-1").delete()
        db.query(Vehicle).filter(Vehicle.vehicle_id == "TEST-VEH-1").delete()
        db.commit()
        db.close()
