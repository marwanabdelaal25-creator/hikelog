"""Gear schedule and application events.

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .errors import NotFoundError, ValidationError
from .trail import parse_iso
from .storage import JsonStorage


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class GearManager:
    BUCKET = "gear_events"

    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def _rows(self) -> list[dict]:
        return self.storage.snapshot().get(self.BUCKET, [])

    def _persist(self, rows: list[dict]) -> None:
        def _write(data: dict) -> None:
            data[self.BUCKET] = rows

        self.storage.mutate(_write)

    def apply(
        self,
        trail_id: str,
        product: str,
        *,
        dilution: str = "",
        notes: str = "",
        applied_at: Optional[str] = None,
    ) -> dict:
        self.storage.get_trail(trail_id)
        row = {
            "id": uuid.uuid4().hex[:12],
            "trail_id": trail_id,
            "product": product,
            "dilution": dilution,
            "notes": notes,
            "applied_at": applied_at or _utc_now(),
        }
        rows = self._rows()
        rows.append(row)
        self._persist(rows)
        return row

    def history(self, trail_id: str) -> list[dict]:
        rows = [r for r in self._rows() if r.get("trail_id") == trail_id]
        rows.sort(key=lambda r: r.get("applied_at", ""), reverse=True)
        return rows

    def last_application(self, trail_id: str) -> Optional[dict]:
        hist = self.history(trail_id)
        return hist[0] if hist else None

    def due_for_gear(
        self,
        interval_days: int = 30,
        *,
        active_only: bool = True,
    ) -> list[dict]:
        now = datetime.now(timezone.utc)
        due = []
        for trail in self.storage.list_trails(active_only=active_only):
            last = self.last_application(trail.id)
            if last is None:
                due.append({"trail_id": trail.id, "trail_name": trail.name, "reason": "never"})
                continue
            applied = parse_iso(last.get("applied_at"))
            if applied is None:
                continue
            if applied.tzinfo is None:
                applied = applied.replace(tzinfo=timezone.utc)
            if now - applied >= timedelta(days=interval_days):
                days = (now - applied).days
                due.append({
                    "trail_id": trail.id,
                    "trail_name": trail.name,
                    "days_since": days,
                    "reason": "overdue",
                })
        due.sort(key=lambda d: d.get("days_since", 9999), reverse=True)
        return due

    def set_schedule(self, trail_id: str, interval_days: int) -> dict:
        if interval_days < 1:
            raise ValidationError("interval must be >= 1")
        return self.storage.update_trail(trail_id, {
            "metadata": {
                **self.storage.get_trail(trail_id).metadata,
                "gear_interval_days": interval_days,
            }
        }).to_dict()

    def delete_event(self, event_id: str) -> None:
        rows = self._rows()
        new_rows = [r for r in rows if r.get("id") != event_id]
        if len(new_rows) == len(rows):
            raise NotFoundError(self.BUCKET, event_id)
        self._persist(new_rows)
