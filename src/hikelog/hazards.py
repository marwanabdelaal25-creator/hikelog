"""Hazard and disease incident tracking.

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from .errors import NotFoundError, ValidationError
from .storage import JsonStorage

STATUS_OPEN = "open"
STATUS_RESOLVED = "resolved"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class HazardTracker:
    BUCKET = "hazard_incidents"

    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def _rows(self) -> list[dict]:
        return self.storage.snapshot().get(self.BUCKET, [])

    def _persist(self, rows: list[dict]) -> None:
        def _write(data: dict) -> None:
            data[self.BUCKET] = rows

        self.storage.mutate(_write)

    def report(
        self,
        trail_id: str,
        issue: str,
        *,
        severity: str = "low",
        treatment: str = "",
        notes: str = "",
    ) -> dict:
        if not issue.strip():
            raise ValidationError("issue description required")
        self.storage.get_trail(trail_id)
        row = {
            "id": uuid.uuid4().hex[:12],
            "trail_id": trail_id,
            "issue": issue.strip(),
            "severity": severity,
            "status": STATUS_OPEN,
            "treatment": treatment,
            "notes": notes,
            "reported_at": _utc_now(),
            "resolved_at": None,
        }
        rows = self._rows()
        rows.append(row)
        self._persist(rows)
        return row

    def list_open(self) -> list[dict]:
        return [r for r in self._rows() if r.get("status") == STATUS_OPEN]

    def list_for_trail(self, trail_id: str) -> list[dict]:
        return [r for r in self._rows() if r.get("trail_id") == trail_id]

    def resolve(self, incident_id: str, notes: str = "") -> dict:
        rows = self._rows()
        for row in rows:
            if row.get("id") == incident_id:
                row["status"] = STATUS_RESOLVED
                row["resolved_at"] = _utc_now()
                if notes:
                    row["notes"] = (row.get("notes", "") + "\n" + notes).strip()
                self._persist(rows)
                return dict(row)
        raise NotFoundError(self.BUCKET, incident_id)

    def update(self, incident_id: str, patch: dict) -> dict:
        rows = self._rows()
        for row in rows:
            if row.get("id") == incident_id:
                for k, v in patch.items():
                    if k != "id":
                        row[k] = v
                self._persist(rows)
                return dict(row)
        raise NotFoundError(self.BUCKET, incident_id)

    def delete(self, incident_id: str) -> None:
        rows = self._rows()
        new_rows = [r for r in rows if r.get("id") != incident_id]
        if len(new_rows) == len(rows):
            raise NotFoundError(self.BUCKET, incident_id)
        self._persist(new_rows)

    def summary(self) -> dict:
        rows = self._rows()
        open_count = sum(1 for r in rows if r.get("status") == STATUS_OPEN)
        by_severity = {}
        for r in rows:
            sev = r.get("severity", "unknown")
            by_severity[sev] = by_severity.get(sev, 0) + 1
        return {
            "total": len(rows),
            "open": open_count,
            "resolved": len(rows) - open_count,
            "by_severity": by_severity,
        }
