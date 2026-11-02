"""In-process event bus feeding the live dashboard (polled via /api/events)."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Event:
    id: int
    type: str  # fault_detected / service_booked / service_started / service_completed / notification / simulation
    title: str
    message: str
    severity: str = "info"  # info / success / warning / critical
    vehicle_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventBus:
    """Thread-safe ring buffer of recent events with monotonically increasing ids."""

    def __init__(self, maxlen: int = 500) -> None:
        self._events: deque[Event] = deque(maxlen=maxlen)
        self._next_id = 1
        self._lock = threading.Lock()

    def publish(
        self,
        type: str,
        title: str,
        message: str,
        *,
        severity: str = "info",
        vehicle_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Event:
        with self._lock:
            event = Event(
                id=self._next_id,
                type=type,
                title=title,
                message=message,
                severity=severity,
                vehicle_id=vehicle_id,
                data=data or {},
            )
            self._next_id += 1
            self._events.append(event)
            return event

    def since(self, after_id: int = 0, limit: int = 100) -> list[Event]:
        with self._lock:
            events = [event for event in self._events if event.id > after_id]
        return events[-limit:]

    @property
    def last_id(self) -> int:
        with self._lock:
            return self._next_id - 1


event_bus = EventBus()
