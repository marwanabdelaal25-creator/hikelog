"""JSON persistence layer for logbook data.

Author: Marwan Helmy
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .errors import NotFoundError, StorageError, ValidationError
from .trailhead import Trailhead
from .trail import Trail
from .terrain import TerrainProfile

SCHEMA_VERSION = 2

DEFAULT_GARDEN: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "trails": [],
    "terrain": [],
    "trailheads": [],
    "visit_events": [],
    "trip_logs": [],
    "tags": [],
    "notes": [],
    "audit": [],
    "plugins": [],
    "recurring": [],
    "collections": [],
    "conditions_readings": [],
    "exposure_logs": [],
    "hazard_incidents": [],
    "gear_events": [],
    "photos": [],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_id(prefix: str = "") -> str:
    raw = uuid.uuid4().hex[:12]
    return f"{prefix}{raw}" if prefix else raw


def _normalize_trail_row(row: dict) -> dict:
    """Bridge legacy logbook.json field names."""
    out = dict(row)
    if "terrain_key" not in out and out.get("terrain_id"):
        out["terrain_key"] = out["terrain_id"]
    if "tag_ids" not in out and out.get("tags"):
        out["tag_ids"] = list(out["tags"])
    if "archived" not in out and "active" in out:
        out["archived"] = not bool(out.get("active", True))
    return out


def _trail_payload(data: Trail | dict) -> dict:
    if isinstance(data, Trail):
        return data.to_dict()
    return _normalize_trail_row(dict(data))


def _normalize_terrain_row(row: dict) -> dict:
    out = dict(row)
    if "key" not in out and out.get("id"):
        out["key"] = out["id"]
    return out


def _terrain_payload(data: TerrainProfile | dict) -> dict:
    if isinstance(data, TerrainProfile):
        return data.to_dict()
    row = _normalize_terrain_row(dict(data))
    return row


class JsonStorage:
    """Thread-safe JSON file store with atomic writes."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._data: dict[str, Any] = deepcopy(DEFAULT_GARDEN)
        if self.path.exists():
            self.load()
        else:
            self._ensure_parent()
            self.save()

    def _ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                text = self.path.read_text(encoding="utf-8")
                payload = json.loads(text)
            except (OSError, json.JSONDecodeError) as exc:
                raise StorageError(f"failed to load {self.path}: {exc}") from exc
            if not isinstance(payload, dict):
                raise StorageError("logbook root must be an object")
            self._data = self._merge_defaults(payload)
            return deepcopy(self._data)

    def save(self) -> None:
        with self._lock:
            self._atomic_write(self._data)

    def _merge_defaults(self, payload: dict) -> dict:
        merged = deepcopy(DEFAULT_GARDEN)
        merged.update(payload)
        for key in DEFAULT_GARDEN:
            if key not in payload:
                merged[key] = deepcopy(DEFAULT_GARDEN[key])
        return merged

    def _atomic_write(self, data: dict) -> None:
        self._ensure_parent()
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            raise StorageError(f"failed to save {self.path}: {exc}") from exc

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def replace_all(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._data = self._merge_defaults(data)
            self._atomic_write(self._data)

    # --- generic list CRUD ---

    def _list(self, bucket: str) -> list[dict]:
        items = self._data.get(bucket, [])
        if not isinstance(items, list):
            raise StorageError(f"bucket {bucket!r} is corrupt")
        return items

    def _find_index(self, bucket: str, item_id: str, id_field: str = "id") -> int:
        for idx, row in enumerate(self._list(bucket)):
            if row.get(id_field) == item_id:
                return idx
        raise NotFoundError(bucket, item_id)

    def _create(self, bucket: str, record: dict, id_field: str = "id") -> dict:
        with self._lock:
            if not record.get(id_field):
                record[id_field] = _new_id()
            if any(r.get(id_field) == record[id_field] for r in self._list(bucket)):
                raise ValidationError(f"duplicate {id_field} in {bucket}")
            record.setdefault("created_at", _utc_now())
            record.setdefault("updated_at", record["created_at"])
            self._list(bucket).append(record)
            self._atomic_write(self._data)
            return deepcopy(record)

    def _read(self, bucket: str, item_id: str, id_field: str = "id") -> dict:
        idx = self._find_index(bucket, item_id, id_field)
        return deepcopy(self._list(bucket)[idx])

    def _update(self, bucket: str, item_id: str, patch: dict, id_field: str = "id") -> dict:
        with self._lock:
            idx = self._find_index(bucket, item_id, id_field)
            row = self._list(bucket)[idx]
            for k, v in patch.items():
                if k == id_field:
                    continue
                row[k] = v
            row["updated_at"] = _utc_now()
            self._atomic_write(self._data)
            return deepcopy(row)

    def _delete(self, bucket: str, item_id: str, id_field: str = "id") -> None:
        with self._lock:
            idx = self._find_index(bucket, item_id, id_field)
            del self._list(bucket)[idx]
            self._atomic_write(self._data)

    def _list_all(self, bucket: str) -> list[dict]:
        with self._lock:
            return deepcopy(self._list(bucket))

    # --- trails ---

    def list_trails(self, active_only: bool = False) -> list[Trail]:
        rows = self._list_all("trails")
        if active_only:
            rows = [r for r in rows if not r.get("archived", False)]
        return [Trail.from_dict(_normalize_trail_row(r)) for r in rows]

    def get_trail(self, trail_id: str) -> Trail:
        return Trail.from_dict(_normalize_trail_row(self._read("trails", trail_id)))

    def create_trail(self, trail: Trail | dict) -> Trail:
        return Trail.from_dict(self._create("trails", _trail_payload(trail)))

    def update_trail(self, trail_id: str, patch: dict) -> Trail:
        return Trail.from_dict(self._update("trails", trail_id, _normalize_trail_row(patch)))

    def delete_trail(self, trail_id: str) -> None:
        self._delete("trails", trail_id)

    # --- terrain ---

    def list_terrain(self) -> list[TerrainProfile]:
        return [TerrainProfile.from_dict(_normalize_terrain_row(r)) for r in self._list_all("terrain")]

    def get_terrain(self, terrain_id: str) -> TerrainProfile:
        for row in self._list_all("terrain"):
            if row.get("key") == terrain_id or row.get("id") == terrain_id:
                return TerrainProfile.from_dict(_normalize_terrain_row(row))
        raise NotFoundError("terrain", terrain_id)

    def create_terrain(self, terrain: TerrainProfile | dict) -> TerrainProfile:
        row = _terrain_payload(terrain)
        created = self._create("terrain", row, id_field="key")
        return TerrainProfile.from_dict(_normalize_terrain_row(created))

    def update_terrain(self, terrain_id: str, patch: dict) -> TerrainProfile:
        row = self._update("terrain", terrain_id, _normalize_terrain_row(patch), id_field="key")
        return TerrainProfile.from_dict(_normalize_terrain_row(row))

    def delete_terrain(self, terrain_id: str) -> None:
        with self._lock:
            rows = self._list("terrain")
            for idx, row in enumerate(rows):
                if row.get("key") == terrain_id or row.get("id") == terrain_id:
                    del rows[idx]
                    self._atomic_write(self._data)
                    return
        raise NotFoundError("terrain", terrain_id)

    # --- trailheads ---

    def list_trailheads(self) -> list[Trailhead]:
        return [Trailhead.from_dict(r) for r in self._list_all("trailheads")]

    def get_trailhead(self, trailhead_id: str) -> Trailhead:
        return Trailhead.from_dict(self._read("trailheads", trailhead_id))

    def create_trailhead(self, trailhead: Trailhead | dict) -> Trailhead:
        data = trailhead.to_dict() if isinstance(trailhead, Trailhead) else dict(trailhead)
        return Trailhead.from_dict(self._create("trailheads", data))

    def update_trailhead(self, trailhead_id: str, patch: dict) -> Trailhead:
        return Trailhead.from_dict(self._update("trailheads", trailhead_id, patch))

    def delete_trailhead(self, trailhead_id: str) -> None:
        self._delete("trailheads", trailhead_id)

    # --- visit / care ---

    def list_visit_events(self, trail_id: Optional[str] = None) -> list[dict]:
        rows = self._list_all("visit_events")
        if trail_id:
            rows = [r for r in rows if r.get("trail_id") == trail_id]
        return rows

    def create_visit_event(self, event: dict) -> dict:
        event.setdefault("visited_at", _utc_now())
        created = self._create("visit_events", event)
        # keep trail in sync - lazy but handy
        try:
            self.update_trail(created["trail_id"], {"last_visited_at": created["visited_at"]})
        except NotFoundError:
            pass
        return created

    def get_visit_event(self, event_id: str) -> dict:
        return self._read("visit_events", event_id)

    def update_visit_event(self, event_id: str, patch: dict) -> dict:
        return self._update("visit_events", event_id, patch)

    def delete_visit_event(self, event_id: str) -> None:
        self._delete("visit_events", event_id)

    def list_trip_logs(self, trail_id: Optional[str] = None) -> list[dict]:
        rows = self._list_all("trip_logs")
        if trail_id:
            rows = [r for r in rows if r.get("trail_id") == trail_id]
        return rows

    def create_trip_log(self, log: dict) -> dict:
        log.setdefault("logged_at", _utc_now())
        return self._create("trip_logs", log)

    def get_trip_log(self, log_id: str) -> dict:
        return self._read("trip_logs", log_id)

    def update_trip_log(self, log_id: str, patch: dict) -> dict:
        return self._update("trip_logs", log_id, patch)

    def delete_trip_log(self, log_id: str) -> None:
        self._delete("trip_logs", log_id)

    # --- tags / notes ---

    def list_tags(self) -> list[dict]:
        return self._list_all("tags")

    def create_tag(self, tag: dict) -> dict:
        tag.setdefault("name", tag.get("id", ""))
        return self._create("tags", tag)

    def update_tag(self, tag_id: str, patch: dict) -> dict:
        return self._update("tags", tag_id, patch)

    def delete_tag(self, tag_id: str) -> None:
        self._delete("tags", tag_id)

    def list_notes(self, trail_id: Optional[str] = None) -> list[dict]:
        rows = self._list_all("notes")
        if trail_id:
            rows = [r for r in rows if r.get("trail_id") == trail_id]
        return rows

    def create_note(self, note: dict) -> dict:
        note.setdefault("created_at", _utc_now())
        return self._create("notes", note)

    def update_note(self, note_id: str, patch: dict) -> dict:
        return self._update("notes", note_id, patch)

    def delete_note(self, note_id: str) -> None:
        self._delete("notes", note_id)

    # --- audit / plugins / recurring ---

    def list_audit(self) -> list[dict]:
        return self._list_all("audit")

    def append_audit(self, entry: dict) -> dict:
        entry.setdefault("timestamp", _utc_now())
        entry.setdefault("id", _new_id("aud_"))
        with self._lock:
            self._list("audit").append(entry)
            self._atomic_write(self._data)
            return deepcopy(entry)

    def list_plugins(self) -> list[dict]:
        return self._list_all("plugins")

    def upsert_plugin(self, plugin: dict) -> dict:
        pid = plugin.get("id")
        if not pid:
            return self._create("plugins", plugin)
        with self._lock:
            for idx, row in enumerate(self._list("plugins")):
                if row.get("id") == pid:
                    row.update(plugin)
                    row["updated_at"] = _utc_now()
                    self._atomic_write(self._data)
                    return deepcopy(row)
        return self._create("plugins", plugin)

    def delete_plugin(self, plugin_id: str) -> None:
        self._delete("plugins", plugin_id)

    def list_recurring(self) -> list[dict]:
        return self._list_all("recurring")

    def create_recurring(self, task: dict) -> dict:
        return self._create("recurring", task)

    def update_recurring(self, task_id: str, patch: dict) -> dict:
        return self._update("recurring", task_id, patch)

    def delete_recurring(self, task_id: str) -> None:
        self._delete("recurring", task_id)

    # --- extended buckets used by other modules ---

    def list_collections(self) -> list[dict]:
        return self._list_all("collections")

    def create_collection(self, coll: dict) -> dict:
        return self._create("collections", coll)

    def update_collection(self, coll_id: str, patch: dict) -> dict:
        return self._update("collections", coll_id, patch)

    def delete_collection(self, coll_id: str) -> None:
        self._delete("collections", coll_id)

    def mutate(self, fn: Callable[[dict[str, Any]], None]) -> None:
        """Run arbitrary in-lock mutation (used by migrations)."""
        with self._lock:
            fn(self._data)
            self._atomic_write(self._data)
