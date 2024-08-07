"""Photo attachment metadata (no image handling in core).

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .errors import NotFoundError, ValidationError
from .storage import JsonStorage


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class PhotoCatalog:
    BUCKET = "photos"

    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def _rows(self) -> list[dict]:
        return self.storage.snapshot().get(self.BUCKET, [])

    def _persist(self, rows: list[dict]) -> None:
        def _write(data: dict) -> None:
            data[self.BUCKET] = rows

        self.storage.mutate(_write)

    def register(
        self,
        trail_id: str,
        path: str,
        *,
        caption: str = "",
        taken_at: Optional[str] = None,
    ) -> dict:
        self.storage.get_trail(trail_id)
        p = Path(path)
        if not str(path).strip():
            raise ValidationError("path required")
        row = {
            "id": uuid.uuid4().hex[:12],
            "trail_id": trail_id,
            "path": str(p),
            "filename": p.name,
            "caption": caption,
            "taken_at": taken_at or _utc_now(),
            "registered_at": _utc_now(),
        }
        rows = self._rows()
        rows.append(row)
        self._persist(rows)
        return row

    def for_trail(self, trail_id: str) -> list[dict]:
        rows = [r for r in self._rows() if r.get("trail_id") == trail_id]
        rows.sort(key=lambda r: r.get("taken_at", ""), reverse=True)
        return rows

    def get(self, photo_id: str) -> dict:
        for row in self._rows():
            if row.get("id") == photo_id:
                return dict(row)
        raise NotFoundError(self.BUCKET, photo_id)

    def update_caption(self, photo_id: str, caption: str) -> dict:
        rows = self._rows()
        for row in rows:
            if row.get("id") == photo_id:
                row["caption"] = caption
                self._persist(rows)
                return dict(row)
        raise NotFoundError(self.BUCKET, photo_id)

    def delete(self, photo_id: str) -> dict:
        rows = self._rows()
        removed = None
        new_rows = []
        for row in rows:
            if row.get("id") == photo_id:
                removed = row
            else:
                new_rows.append(row)
        if removed is None:
            raise NotFoundError(self.BUCKET, photo_id)
        self._persist(new_rows)
        return removed  # caller decides whether to unlink file

    def missing_files(self) -> list[dict]:
        missing = []
        for row in self._rows():
            if not Path(row.get("path", "")).exists():
                missing.append(row)
        return missing
