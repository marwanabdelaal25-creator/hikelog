"""Aggregate logbook statistics.

Author: Marwan Helmy
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .trail import parse_iso
from .reminders import ReminderEngine
from .storage import JsonStorage


class GardenStats:
    def __init__(self, storage: JsonStorage):
        self.storage = storage
        self.reminders = ReminderEngine(storage)

    def snapshot(self) -> dict[str, Any]:
        trails = self.storage.list_trails(active_only=True)
        all_trails = self.storage.list_trails(active_only=False)
        visit = self.storage.list_visit_events()
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        watered_last_7 = sum(
            1 for e in visit
            if (dt := parse_iso(e.get("visited_at"))) and dt >= week_ago
        )
        watered_last_30 = sum(
            1 for e in visit
            if (dt := parse_iso(e.get("visited_at"))) and dt >= month_ago
        )

        overdue = self.reminders.overdue_only()
        terrain_count = len(self.storage.list_terrain())
        trailheads_count = len(self.storage.list_trailheads())
        tags_count = len(self.storage.list_tags())

        inactive = len(all_trails) - len(trails)
        avg_interval = 0.0
        if trails:
            avg_interval = sum(p.visit_interval_days for p in trails) / len(trails)

        return {
            "generated_at": now.isoformat(),
            "trails_active": len(trails),
            "trails_inactive": inactive,
            "trails_total": len(all_trails),
            "terrain_count": terrain_count,
            "trailheads_count": trailheads_count,
            "tags_count": tags_count,
            "visit_events_total": len(visit),
            "watered_last_7_days": watered_last_7,
            "watered_last_30_days": watered_last_30,
            "overdue_count": len(overdue),
            "due_today_count": sum(
                1 for r in self.reminders.upcoming(within_days=0, include_overdue=False)
                if r.urgency == "due_today"
            ),
            "avg_visit_interval_days": round(avg_interval, 1),
            "trip_logs_total": len(self.storage.list_trip_logs()),
            "notes_total": len(self.storage.list_notes()),
            "collections_total": len(self.storage.list_collections()),
        }

    def render_text(self) -> str:
        s = self.snapshot()
        return (
            f"Garden stats @ {s['generated_at'][:10]}\n"
            f"  Active trails: {s['trails_active']} / {s['trails_total']}\n"
            f"  Overdue: {s['overdue_count']}\n"
            f"  Watered (7d / 30d): {s['watered_last_7_days']} / {s['watered_last_30_days']}\n"
            f"  Terrain: {s['terrain_count']}  Trailheads: {s['trailheads_count']}"
        )
