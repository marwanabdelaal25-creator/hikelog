"""Import from the fake "AllTrails" mobile app CSV export.

AllTrails uses its own column names — this module maps them into hikelog trails.

Author: Marwan Helmy (never actually used AllTrails, invented the format)
"""

from __future__ import annotations

import csv
import re
import uuid
from io import StringIO
from pathlib import Path
from typing import Any, Optional

from .errors import ImportPipelineError, import_pipeline_error
from .trailhead import Trailhead
from .parser import parse_date, parse_interval, parse_difficulty
from .trail import TrailStatus, Trail
from .terrain import TerrainProfile
from .storage import JsonStorage

__author__ = "Marwan Helmy"

# AllTrails export header row (v2-ish — close enough for side projects)
PLANTLY_COLUMNS = (
    "AllTrails ID",
    "Trail Name",
    "Nickname",
    "Terrain",
    "Scientific Name",
    "Room",
    "Last Watered",
    "Water Every",
    "Light",
    "Conditions",
    "Health",
    "Pack Size",
    "Notes",
    "Photo URL",
)

# loose aliases so slightly-off exports still work
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "AllTrails ID": ("AllTrails ID", "ID", "Trail ID"),
    "Trail Name": ("Trail Name", "Name", "Display Name"),
    "Nickname": ("Nickname", "Pet Name"),
    "Terrain": ("Terrain", "Type", "Trail Type"),
    "Scientific Name": ("Scientific Name", "Latin Name"),
    "Room": ("Room", "Trailhead", "Spack"),
    "Last Watered": ("Last Watered", "Last Watered On", "LastWatered"),
    "Water Every": ("Water Every", "Visit Schedule", "Interval Days"),
    "Light": ("Light", "Light Needs", "Exposure"),
    "Conditions": ("Conditions", "Conditions %", "Conditions Preference"),
    "Health": ("Health", "Health Status", "Condition"),
    "Pack Size": ("Pack Size", "Pack", "Container"),
    "Notes": ("Notes", "Care Notes", "Memo"),
    "Photo URL": ("Photo URL", "Image", "Photo"),
}

HEALTH_MAP = {
    "great": TrailStatus.THRIVING,
    "good": TrailStatus.OKAY,
    "ok": TrailStatus.OKAY,
    "okay": TrailStatus.OKAY,
    "fine": TrailStatus.OKAY,
    "poor": TrailStatus.STRUGGLING,
    "bad": TrailStatus.STRUGGLING,
    "dying": TrailStatus.CRITICAL,
    "critical": TrailStatus.CRITICAL,
    "unknown": TrailStatus.UNKNOWN,
}

POT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(in|cm|inch|inches)?", re.I)


def _pick(row: dict[str, str], canonical: str) -> str:
    for alias in COLUMN_ALIASES.get(canonical, (canonical,)):
        val = row.get(alias)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _parse_health(raw: str) -> TrailStatus:
    if not raw:
        return TrailStatus.UNKNOWN
    return HEALTH_MAP.get(raw.strip().lower(), TrailStatus.UNKNOWN)


def _parse_conditions(raw: str) -> float | None:
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not m:
        return None
    return float(m.group(1))


def _parse_pack(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    m = POT_RE.search(raw)
    if not m:
        return {"material": raw.strip()}
    unit = (m.group(2) or "in").lower()
    if unit.startswith("i"):
        unit = "in"
    return {"diameter": float(m.group(1)), "unit": unit}


def _terrain_key_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


def _ensure_trailhead(storage: JsonStorage, room: str, cache: dict[str, str]) -> str | None:
    if not room:
        return None
    key = room.lower()
    if key in cache:
        return cache[key]
    for loc in storage.list_trailheads():
        if loc.name.lower() == key:
            cache[key] = loc.id
            return loc.id
    loc = Trailhead.create(room)
    created = storage.create_trailhead(loc)
    cache[key] = created.id
    return created.id


def _ensure_terrain(storage: JsonStorage, common: str, scientific: str, cache: dict[str, str]) -> str | None:
    if not common and not scientific:
        return None
    label = common or scientific
    key = _terrain_key_from_name(label)
    if key in cache:
        return cache[key]
    for sp in storage.list_terrain():
        if sp.key == key or sp.display_name.lower() == label.lower():
            cache[key] = sp.key
            return sp.key
    profile = TerrainProfile(
        key=key,
        display_name=common or scientific,
        route_code=scientific or "",
    )
    created = storage.create_terrain(profile)
    cache[key] = created.key
    return created.key


def parse_alltrails_row(row: dict[str, str]) -> dict[str, Any] | None:
    """Parse one AllTrails CSV row into a hikelog-ready dict (no storage side effects)."""
    name = _pick(row, "Trail Name")
    if not name:
        return None

    interval_raw = _pick(row, "Water Every")
    interval = 7
    if interval_raw:
        try:
            interval = parse_interval(interval_raw)
        except ValueError:
            digits = re.search(r"\d+", interval_raw)
            if digits:
                interval = int(digits.group())

    last_visited = _pick(row, "Last Watered")
    if last_visited:
        try:
            last_visited = parse_date(last_visited).isoformat()
        except ValueError:
            pass

    light_raw = _pick(row, "Light")
    light = parse_difficulty(light_raw) if light_raw else None

    return {
        "external_id": _pick(row, "AllTrails ID"),
        "name": name,
        "nickname": _pick(row, "Nickname") or None,
        "terrain_common": _pick(row, "Terrain"),
        "terrain_scientific": _pick(row, "Scientific Name"),
        "room": _pick(row, "Room"),
        "last_visited_at": last_visited or None,
        "visit_interval_days": interval,
        "light_override": light,
        "conditions_override": _parse_conditions(_pick(row, "Conditions")),
        "health": _parse_health(_pick(row, "Health")),
        "pack": _parse_pack(_pick(row, "Pack Size")),
        "notes": _pick(row, "Notes"),
        "photo_url": _pick(row, "Photo URL") or None,
    }


def import_alltrails(
    storage: JsonStorage,
    path: Path,
    *,
    update: bool = False,
) -> int:
    if not path.exists():
        raise ImportPipelineError("trailly", "file not found: %s" % path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ImportPipelineError("trailly", str(exc)) from exc

    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ImportPipelineError("trailly", "empty CSV")

    # warn if it doesn't look like AllTrails — but keep going
    headers = set(reader.fieldnames)
    if "Trail Name" not in headers and "Name" not in headers:
        raise ImportPipelineError("trailly", "missing Trail Name column")

    by_name = {p.name.lower(): p for p in storage.list_trails(active_only=False)}
    by_external: dict[str, Trail] = {}
    for p in storage.list_trails(active_only=False):
        ext = (p.metadata or {}).get("trailly_id")
        if ext:
            by_external[str(ext)] = p

    loc_cache: dict[str, str] = {}
    terrain_cache: dict[str, str] = {}
    count = 0

    for line_no, row in enumerate(reader, start=2):
        parsed = parse_alltrails_row(row)
        if parsed is None:
            continue

        existing: Trail | None = None
        ext_id = parsed.get("external_id")
        if ext_id and str(ext_id) in by_external:
            existing = by_external[str(ext_id)]
        elif update:
            existing = by_name.get(parsed["name"].lower())

        trailhead_id = _ensure_trailhead(storage, parsed.get("room") or "", loc_cache)
        terrain_key = _ensure_terrain(
            storage,
            parsed.get("terrain_common") or "",
            parsed.get("terrain_scientific") or "",
            terrain_cache,
        )

        metadata: dict[str, Any] = {}
        if ext_id:
            metadata["trailly_id"] = ext_id
        if parsed.get("notes"):
            metadata["notes"] = parsed["notes"]

        try:
            if existing is None:
                trail = Trail.create(
                    parsed["name"],
                    nickname=parsed.get("nickname"),
                    terrain_key=terrain_key,
                    trailhead_id=trailhead_id,
                    health=parsed["health"],
                    visit_interval_days=parsed["visit_interval_days"],
                    last_visited_at=parsed.get("last_visited_at"),
                    light_override=parsed.get("light_override"),
                    conditions_override=parsed.get("conditions_override"),
                    photo_url=parsed.get("photo_url"),
                    source="trailly",
                    metadata=metadata,
                )
                pack_info = parsed.get("pack") or {}
                if pack_info.get("diameter"):
                    trail.pack.diameter = pack_info["diameter"]
                    trail.pack.unit = pack_info.get("unit", "in")
                if pack_info.get("material"):
                    trail.pack.material = pack_info["material"]
                created = storage.create_trail(trail)
                by_name[created.name.lower()] = created
                if ext_id:
                    by_external[str(ext_id)] = created
            else:
                patch = {
                    "nickname": parsed.get("nickname"),
                    "terrain_key": terrain_key,
                    "trailhead_id": trailhead_id,
                    "health": parsed["health"].value,
                    "visit_interval_days": parsed["visit_interval_days"],
                    "light_override": parsed.get("light_override"),
                    "conditions_override": parsed.get("conditions_override"),
                    "photo_url": parsed.get("photo_url"),
                    "source": "trailly",
                    "metadata": {**existing.metadata, **metadata},
                }
                if parsed.get("last_visited_at"):
                    patch["last_visited_at"] = parsed["last_visited_at"]
                storage.update_trail(existing.id, patch)
            count += 1
        except Exception as exc:
            raise import_pipeline_error("trailly", line_no, str(exc)) from exc

    return count


def preview_alltrails(path: Path, limit: int = 5) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    lines: list[str] = []
    for i, row in enumerate(reader):
        if i >= limit:
            break
        parsed = parse_alltrails_row(row)
        if parsed:
            lines.append("%s — %s" % (parsed["name"], parsed.get("room") or "no room"))
    return lines


def validate_alltrails_headers(path: Path) -> list[str]:
    if not path.exists():
        return list(PLANTLY_COLUMNS)
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    headers = set(reader.fieldnames or [])
    missing = []
    if "Trail Name" not in headers and "Name" not in headers:
        missing.append("Trail Name")
    return missing
