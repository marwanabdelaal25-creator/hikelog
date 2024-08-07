#!/usr/bin/env python3
"""Weekly visit workflow — hike overdue and due-today trails.

Author: Marwan Helmy
Run: python examples/weekly_visit.py
     HIKELOG_HOME=~/.hikelog python examples/weekly_visit.py
"""

from __future__ import annotations

import os
from pathlib import Path

from hikelog.reminders import ReminderEngine
from hikelog.storage import JsonStorage
from hikelog.visit import VisitEvent


def logbook_path() -> Path:
    home = os.environ.get("HIKELOG_HOME")
    base = Path(home) if home else Path.home() / ".hikelog"
    return base / "logbook.json"


def main() -> None:
    storage = JsonStorage(logbook_path())
    engine = ReminderEngine(storage)
    due = [r for r in engine.upcoming(within_days=0, include_overdue=True) if r.urgency != "upcoming"]

    if not due:
        print("All caught up — nothing due today or overdue.")
        return

    print(f"Visit {len(due)} trail(s):\n")
    for rem in due:
        trail = storage.get_trail(rem.trail_id)
        amount = trail.visit_distance_km
        flag = "OVERDUE" if rem.urgency == "overdue" else "TODAY"
        print(f"  [{flag}] {rem.trail_name} (due {rem.due_at.date()})")

        if amount is None:
            print("    skipped — no default amount; set visit_distance_km on trail")
            continue

        event = VisitEvent.create(trail_id=trail.id, distance_km=amount, notes="weekly script")
        storage.create_visit_event(event.to_dict())
        print(f"    logged: {event.summary()}")

    print("\nDone. Run `hikelog reminders --within 7` to preview the week ahead.")


if __name__ == "__main__":
    main()
