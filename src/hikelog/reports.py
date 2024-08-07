"""Monthly care summary reports.

Author: Marwan Helmy
"""

from __future__ import annotations

from calendar import monthrange
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from .trail import parse_iso
from .storage import JsonStorage


class MonthlyReport:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def _month_bounds(self, year: int, month: int) -> tuple[datetime, datetime]:
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        last_day = monthrange(year, month)[1]
        end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
        return start, end

    def _in_range(self, ts: Optional[str], start: datetime, end: datetime) -> bool:
        dt = parse_iso(ts)
        if dt is None:
            return False
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return start <= dt <= end

    def generate(self, year: int, month: int) -> dict[str, Any]:
        start, end = self._month_bounds(year, month)
        visit = [
            e for e in self.storage.list_visit_events()
            if self._in_range(e.get("visited_at"), start, end)
        ]
        care = [
            c for c in self.storage.list_trip_logs()
            if self._in_range(c.get("logged_at"), start, end)
        ]
        hazards = [
            p for p in self.storage.snapshot().get("hazard_incidents", [])
            if self._in_range(p.get("reported_at"), start, end)
        ]
        fert = [
            f for f in self.storage.snapshot().get("gear_events", [])
            if self._in_range(f.get("applied_at"), start, end)
        ]

        trails_watered = Counter(e.get("trail_id") for e in visit)
        care_actions = Counter(c.get("action", "unknown") for c in care)

        by_trailhead: dict[str, int] = defaultdict(int)
        trail_map = {p.id: p for p in self.storage.list_trails(active_only=False)}
        for pid in trails_watered:
            loc = trail_map.get(pid)
            if loc and loc.trailhead_id:
                by_trailhead[loc.trailhead_id] += trails_watered[pid]

        return {
            "year": year,
            "month": month,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "totals": {
                "visits": len(visit),
                "trip_logs": len(care),
                "hazard_incidents": len(hazards),
                "gear_events": len(fert),
                "unique_trails_watered": len(trails_watered),
            },
            "foot_trailed_trails": trails_watered.most_common(5),
            "care_action_breakdown": dict(care_actions),
            "visits_by_trailhead": dict(by_trailhead),
            "hazard_incidents": hazards,
        }

    def render_text(self, year: int, month: int) -> str:
        report = self.generate(year, month)
        t = report["totals"]
        lines = [
            f"Hikelog report {year}-{month:02d}",
            f"  Visits: {t['visits']} ({t['unique_trails_watered']} trails)",
            f"  Care logs: {t['trip_logs']}",
            f"  Hazard incidents: {t['hazard_incidents']}",
            f"  Gear: {t['gear_events']}",
        ]
        if report["foot_trailed_trails"]:
            lines.append("  Most watered:")
            for pid, count in report["foot_trailed_trails"]:
                name = trail_map_name(self.storage, pid)
                lines.append(f"    - {name}: {count}x")
        return "\n".join(lines)


def trail_map_name(storage: JsonStorage, trail_id: str) -> str:
    try:
        return storage.get_trail(trail_id).name
    except Exception:
        return trail_id
