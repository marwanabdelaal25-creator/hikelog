"""CSV import/export for trails and visit logs.

Author: Marwan Helmy — started as a quick spreadsheet escape hatch.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Any, Optional

from .errors import ExportError, ImportPipelineError, ValidationError, import_pipeline_error
from .parser import parse_date, parse_interval, parse_distance_km
from .trail import TrailStatus, Trail
from .storage import JsonStorage
from .visit import VisitEvent

__author__ = "Marwan Helmy"

PLANT_FIELDS = [
    "id",
    "name",
    "nickname",
    "terrain_key",
    "trailhead_id",
    "health",
    "health_score",
    "visit_interval_days",
    "visit_distance_km",
    "last_visited_at",
    "acquired_at",
    "light_override",
    "conditions_override",
    "archived",
    "source",
    "notes",
]

WATERING_FIELDS = [
    "id",
    "trail_id",
    "trail_name",
    "visited_at",
    "distance_km",
    "method",
    "visit_pace",
    "runoff",
    "skipped",
    "skip_reason",
    "notes",
]


def _read_csv_text(path: Path) -> str:
    if not path.exists():
        raise ImportPipelineError("csv", "file not found: %s" % path)
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ImportPipelineError("csv", str(exc)) from exc


def _parse_bool(raw: Optional[str]) -> bool:
    if not raw:
        return False
    return raw.strip().lower() in ("1", "true", "yes", "y")


def _parse_health(raw: Optional[str]) -> TrailStatus:
    if not raw:
        return TrailStatus.UNKNOWN
    key = raw.strip().lower().replace(" ", "_")
    try:
        return TrailStatus(key)
    except ValueError:
        return TrailStatus.UNKNOWN


def _trail_lookup(storage: JsonStorage) -> tuple[dict[str, Trail], dict[str, Trail]]:
    by_id = {p.id: p for p in storage.list_trails(active_only=False)}
    by_name: dict[str, Trail] = {}
    for p in by_id.values():
        by_name.setdefault(p.name.lower(), p)
        if p.nickname:
            by_name.setdefault(p.nickname.lower(), p)
    return by_id, by_name


def _resolve_trail_id(
    by_id: dict[str, Trail],
    by_name: dict[str, Trail],
    trail_id: Optional[str],
    trail_name: Optional[str],
) -> Optional[str]:
    if trail_id and trail_id in by_id:
        return trail_id
    if trail_name:
        hit = by_name.get(trail_name.strip().lower())
        if hit:
            return hit.id
    return trail_id


def export_trails_csv(storage: JsonStorage, dest: Path) -> int:
    """Write all trails (including archived) to a CSV file."""
    try:
        with dest.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=PLANT_FIELDS)
            writer.writeheader()
            count = 0
            for trail in storage.list_trails(active_only=False):
                notes = str(trail.metadata.get("notes", ""))
                writer.writerow({
                    "id": trail.id,
                    "name": trail.name,
                    "nickname": trail.nickname or "",
                    "terrain_key": trail.terrain_key or "",
                    "trailhead_id": trail.trailhead_id or "",
                    "health": trail.health.value,
                    "health_score": trail.health_score,
                    "visit_interval_days": trail.visit_interval_days,
                    "visit_distance_km": trail.visit_distance_km or "",
                    "last_visited_at": trail.last_visited_at or "",
                    "acquired_at": trail.acquired_at or "",
                    "light_override": trail.light_override or "",
                    "conditions_override": trail.conditions_override or "",
                    "archived": "yes" if trail.archived else "no",
                    "source": trail.source,
                    "notes": notes.replace("\n", " "),
                })
                count += 1
        return count
    except OSError as exc:
        raise ExportError("csv", str(exc)) from exc


def export_visit_csv(storage: JsonStorage, dest: Path) -> int:
    """Write visit events with trail names for human-readable spreadsheets."""
    trail_names = {p.id: p.name for p in storage.list_trails(active_only=False)}
    try:
        with dest.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=WATERING_FIELDS)
            writer.writeheader()
            count = 0
            for row in storage.list_visit_events():
                writer.writerow({
                    "id": row.get("id", ""),
                    "trail_id": row.get("trail_id", ""),
                    "trail_name": trail_names.get(row.get("trail_id", ""), ""),
                    "visited_at": row.get("visited_at", ""),
                    "distance_km": row.get("distance_km") or "",
                    "method": row.get("method", "foot_trail"),
                    "visit_pace": row.get("visit_pace", "tap"),
                    "runoff": "yes" if row.get("runoff") else "no",
                    "skipped": "yes" if row.get("skipped") else "no",
                    "skip_reason": row.get("skip_reason", ""),
                    "notes": (row.get("notes") or "").replace("\n", " "),
                })
                count += 1
        return count
    except OSError as exc:
        raise ExportError("csv", str(exc)) from exc


def export_csv_bundle(storage: JsonStorage, dest: Path) -> tuple[int, int]:
    """Export trails.csv and visit.csv beside dest stem."""
    trails_path = dest.with_name(dest.stem + "_trails.csv")
    water_path = dest.with_name(dest.stem + "_visit.csv")
    return export_trails_csv(storage, trails_path), export_visit_csv(storage, water_path)


def import_trails_csv(
    storage: JsonStorage,
    src: Path,
    *,
    update: bool = False,
) -> int:
    """Import trails from CSV; skips blank name rows."""
    text = _read_csv_text(src)
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames or "name" not in reader.fieldnames:
        raise ImportPipelineError("csv", "missing required column: name")

    existing = {p.id: p for p in storage.list_trails(active_only=False)}
    by_name = {p.name.lower(): p for p in existing.values()}
    count = 0

    for line_no, row in enumerate(reader, start=2):
        name = (row.get("name") or "").strip()
        if not name:
            continue
        pid = (row.get("id") or "").strip()
        trail: Trail | None = None
        if pid and pid in existing:
            trail = existing[pid]
        elif update:
            trail = by_name.get(name.lower())

        try:
            interval_raw = row.get("visit_interval_days")
            interval = parse_interval(str(interval_raw)) if interval_raw else 7
            health = _parse_health(row.get("health"))
            metadata = {}
            notes = (row.get("notes") or "").strip()
            if notes:
                metadata["notes"] = notes

            if trail is None:
                trail = Trail.create(
                    name,
                    id=pid or None,
                    nickname=(row.get("nickname") or "").strip() or None,
                    terrain_key=(row.get("terrain_key") or "").strip() or None,
                    trailhead_id=(row.get("trailhead_id") or "").strip() or None,
                    health=health,
                    visit_interval_days=interval,
                    last_visited_at=(row.get("last_visited_at") or "").strip() or None,
                    acquired_at=(row.get("acquired_at") or "").strip() or None,
                    light_override=(row.get("light_override") or "").strip() or None,
                    archived=_parse_bool(row.get("archived")),
                    source="csv",
                    metadata=metadata,
                )
                hs = row.get("health_score")
                if hs and str(hs).isdigit():
                    trail.health_score = int(hs)
                amt = row.get("visit_distance_km")
                if amt:
                    trail.visit_distance_km = parse_distance_km(str(amt))
                hum = row.get("conditions_override")
                if hum:
                    trail.conditions_override = float(hum)
                created = storage.create_trail(trail)
                existing[created.id] = created
                by_name[created.name.lower()] = created
            else:
                patch: dict[str, Any] = {
                    "name": name,
                    "nickname": (row.get("nickname") or "").strip() or None,
                    "terrain_key": (row.get("terrain_key") or "").strip() or None,
                    "trailhead_id": (row.get("trailhead_id") or "").strip() or None,
                    "health": health.value,
                    "visit_interval_days": interval,
                    "archived": _parse_bool(row.get("archived")),
                    "source": "csv",
                    "metadata": {**trail.metadata, **metadata},
                }
                lw = (row.get("last_visited_at") or "").strip()
                if lw:
                    patch["last_visited_at"] = lw
                updated = storage.update_trail(trail.id, patch)
                existing[updated.id] = updated
            count += 1
        except (ValidationError, ValueError) as exc:
            raise import_pipeline_error("csv", line_no, str(exc)) from exc

    return count


def import_visit_csv(storage: JsonStorage, src: Path) -> int:
    """Import visit events; resolves trail_name when trail_id missing."""
    text = _read_csv_text(src)
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ImportPipelineError("csv", "empty or headerless file")

    by_id, by_name = _trail_lookup(storage)
    count = 0

    for line_no, row in enumerate(reader, start=2):
        trail_id = _resolve_trail_id(
            by_id,
            by_name,
            (row.get("trail_id") or "").strip() or None,
            (row.get("trail_name") or "").strip() or None,
        )
        if not trail_id:
            raise import_pipeline_error("csv", line_no, "trail_id or trail_name required")

        try:
            storage.get_trail(trail_id)
        except Exception:
            raise import_pipeline_error("csv", line_no, "unknown trail %s" % trail_id)

        visited_at = (row.get("visited_at") or "").strip()
        if visited_at:
            try:
                visited_at = parse_date(visited_at).isoformat()
            except ValueError:
                pass  # keep raw ISO if already formatted

        distance_km = None
        amt_raw = row.get("distance_km")
        if amt_raw not in (None, ""):
            try:
                distance_km = parse_distance_km(str(amt_raw))
            except ValueError:
                raise import_pipeline_error("csv", line_no, "bad distance_km: %s" % amt_raw)

        event = VisitEvent.create(
            trail_id=trail_id,
            id=(row.get("id") or "").strip() or None,
            visited_at=visited_at or None,
            distance_km=distance_km,
            method=(row.get("method") or "foot_trail").strip(),
            runoff=_parse_bool(row.get("runoff")),
            skipped=_parse_bool(row.get("skipped")),
            skip_reason=(row.get("skip_reason") or "").strip(),
            notes=(row.get("notes") or "").strip(),
        )
        if row.get("visit_pace"):
            event.visit_pace = row["visit_pace"].strip()  # type: ignore[assignment]
        storage.create_visit_event(event.to_dict())
        count += 1

    return count


def validate_csv_headers(path: Path, kind: str = "trails") -> list[str]:
    """Return missing required columns for trails or visit CSV."""
    if not path.exists():
        return ["name"] if kind == "trails" else ["trail_id"]
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    headers = reader.fieldnames or []
    if kind == "trails":
        required = ["name"]
    else:
        required = []  # trail_name OR trail_id
        if "trail_id" not in headers and "trail_name" not in headers:
            return ["trail_id or trail_name"]
        return []
    return [h for h in required if h not in headers]


def sample_rows(path: Path, n: int = 3) -> list[dict[str, str]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    out: list[dict[str, str]] = []
    for i, row in enumerate(reader):
        if i >= n:
            break
        out.append({k: (v or "") for k, v in row.items()})
    return out
