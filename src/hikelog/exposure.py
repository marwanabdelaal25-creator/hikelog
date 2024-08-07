"""Light exposure logs for trails and trailheads.

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from .errors import NotFoundError, ValidationError
from .storage import JsonStorage

VALID_LEVELS = ("low", "medium", "bright", "direct")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ExposureLogger:
    BUCKET = "exposure_logs"

    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def _rows(self) -> list[dict]:
        return self.storage.snapshot().get(self.BUCKET, [])

    def _persist(self, rows: list[dict]) -> None:
        def _write(data: dict) -> None:
            data[self.BUCKET] = rows

        self.storage.mutate(_write)

    def log(
        self,
        *,
        trail_id: Optional[str] = None,
        trailhead_id: Optional[str] = None,
        level: str = "medium",
        hours: Optional[float] = None,
        notes: str = "",
    ) -> dict:
        if not trail_id and not trailhead_id:
            raise ValidationError("need trail_id or trailhead_id")
        level = level.lower()
        if level not in VALID_LEVELS:
            raise ValidationError(f"level must be one of {VALID_LEVELS}")
        if trail_id:
            self.storage.get_trail(trail_id)
        if trailhead_id:
            self.storage.get_trailhead(trailhead_id)

        row = {
            "id": uuid.uuid4().hex[:12],
            "trail_id": trail_id,
            "trailhead_id": trailhead_id,
            "level": level,
            "hours": hours,
            "observed_at": _utc_now(),
            "notes": notes,
        }
        rows = self._rows()
        rows.append(row)
        self._persist(rows)
        return row

    def for_trail(self, trail_id: str) -> list[dict]:
        rows = [r for r in self._rows() if r.get("trail_id") == trail_id]
        rows.sort(key=lambda r: r.get("observed_at", ""), reverse=True)
        return rows

    def for_trailhead(self, trailhead_id: str) -> list[dict]:
        rows = [r for r in self._rows() if r.get("trailhead_id") == trailhead_id]
        rows.sort(key=lambda r: r.get("observed_at", ""), reverse=True)
        return rows

    def latest_for_trail(self, trail_id: str) -> Optional[dict]:
        items = self.for_trail(trail_id)
        return items[0] if items else None

    def delete(self, log_id: str) -> None:
        rows = self._rows()
        new_rows = [r for r in rows if r.get("id") != log_id]
        if len(new_rows) == len(rows):
            raise NotFoundError(self.BUCKET, log_id)
        self._persist(new_rows)
