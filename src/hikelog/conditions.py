"""Conditions reading logs per trailhead.

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Optional

from .errors import NotFoundError, ValidationError
from .storage import JsonStorage


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ConditionsLogger:
    BUCKET = "conditions_readings"

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
        trailhead_id: str,
        percent: float,
        *,
        source: str = "manual",
        notes: str = "",
    ) -> dict:
        if percent < 0 or percent > 100:
            raise ValidationError("conditions must be 0-100")
        try:
            self.storage.get_trailhead(trailhead_id)
        except NotFoundError:
            raise
        row = {
            "id": uuid.uuid4().hex[:12],
            "trailhead_id": trailhead_id,
            "percent": round(float(percent), 1),
            "recorded_at": _utc_now(),
            "source": source,
            "notes": notes,
        }
        rows = self._rows()
        rows.append(row)
        self._persist(rows)
        return row

    def list_for_trailhead(self, trailhead_id: str, limit: Optional[int] = None) -> list[dict]:
        rows = [r for r in self._rows() if r.get("trailhead_id") == trailhead_id]
        rows.sort(key=lambda r: r.get("recorded_at", ""), reverse=True)
        if limit:
            rows = rows[:limit]
        return rows

    def latest(self, trailhead_id: str) -> Optional[dict]:
        items = self.list_for_trailhead(trailhead_id, limit=1)
        return items[0] if items else None

    def average(self, trailhead_id: str, last_n: int = 10) -> Optional[float]:
        rows = self.list_for_trailhead(trailhead_id, limit=last_n)
        if not rows:
            return None
        return round(mean(r["percent"] for r in rows), 1)

    def summary_by_trailhead(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for loc in self.storage.list_trailheads():
            latest = self.latest(loc.id)
            out[loc.id] = {
                "trailhead_name": loc.name,
                "latest_percent": latest["percent"] if latest else None,
                "latest_at": latest.get("recorded_at") if latest else None,
                "avg_10": self.average(loc.id, 10),
            }
        return out

    def delete(self, reading_id: str) -> None:
        rows = self._rows()
        new_rows = [r for r in rows if r.get("id") != reading_id]
        if len(new_rows) == len(rows):
            raise NotFoundError(self.BUCKET, reading_id)
        self._persist(new_rows)
