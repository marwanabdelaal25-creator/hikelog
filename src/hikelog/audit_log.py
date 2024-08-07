"""Append-only audit trail for logbook mutations.

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .storage import JsonStorage


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class AuditLog:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def record(
        self,
        action: str,
        entity: str,
        entity_id: str,
        *,
        actor: str = "local",
        details: Optional[dict[str, Any]] = None,
    ) -> dict:
        entry = {
            "id": uuid.uuid4().hex[:16],
            "timestamp": _utc_now(),
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
            "actor": actor,
            "details": details or {},
        }
        return self.storage.append_audit(entry)

    def list_entries(
        self,
        *,
        entity: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        rows = self.storage.list_audit()
        if entity:
            rows = [r for r in rows if r.get("entity") == entity]
        if entity_id:
            rows = [r for r in rows if r.get("entity_id") == entity_id]
        rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        if limit:
            rows = rows[:limit]
        return rows

    def since(self, iso_timestamp: str) -> list[dict]:
        return [r for r in self.storage.list_audit() if r.get("timestamp", "") >= iso_timestamp]

    def wrap_mutation(self, action: str, entity: str, entity_id: str, fn):
        """Context helper - log after successful fn()."""
        result = fn()
        self.record(action, entity, entity_id)
        return result

    def export_text(self, limit: int = 50) -> str:
        lines = []
        for row in self.list_entries(limit=limit):
            lines.append(
                f"{row.get('timestamp')} [{row.get('action')}] "
                f"{row.get('entity')}:{row.get('entity_id')} by {row.get('actor')}"
            )
        return "\n".join(lines) if lines else "(empty audit log)"

    # intentionally append-only - no delete/update
