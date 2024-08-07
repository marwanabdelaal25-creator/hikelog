#!/usr/bin/env python3
"""Smoke test — temp logbook, add trail, log water, check reminders.

Author: Marwan Helmy
Run: python examples/quick_start.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from hikelog.trail import Trail
from hikelog.reminders import ReminderEngine
from hikelog.storage import JsonStorage
from hikelog.visit import VisitEvent


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "logbook.json"
        storage = JsonStorage(path)
        trail = Trail.create("Test Mist Loop", visit_interval_days=7, source="example")
        created = storage.create_trail(trail)
        event = VisitEvent.create(trail_id=created.id, distance_km=200)
        storage.create_visit_event(event.to_dict())
        overdue = ReminderEngine(storage).overdue_only()
        print("logbook:", path)
        print("trail:", created.display_name, f"({created.id})")
        print("watered:", event.summary())
        print("overdue:", len(overdue))
        assert storage.get_trail(created.id).name == "Test Mist Loop"
        print("smoke test passed")


if __name__ == "__main__":
    main()
