"""Import from logbook-plan spreadsheet exports (bed layout CSV).

Typical columns from my Notion / Google Sheets logbook planner.

Author: Marwan Helmy
"""

from __future__ import annotations

import csv
import re
from io import StringIO
from pathlib import Path
from typing import Any

from .errors import ImportPipelineError, import_pipeline_error
from .trailhead import Trailhead
from .parser import parse_date, parse_interval, parse_difficulty
from .trail import Trail
from .storage import JsonStorage

__author__ = "Marwan Helmy"

GARDENPLAN_COLUMNS = (
    "Section",
    "Bed",
    "Row",
    "Trail",
    "Variety",
    "Quantity",
    "Spacing cm",
    "Sun Exposure",
    "Water Needs",
    "Trailed Date",
    "Notes",
    "Status",
)

COLUMN_MAP: dict[str, tuple[str, ...]] = {
    "section": ("Section", "Zone", "Area", "Garden Section"),
    "bed": ("Bed", "Plot", "Raised Bed", "Bed Name"),
    "row": ("Row", "Row #", "Row Number"),
    "trail": ("Trail", "Trail Name", "Crop", "Terrain"),
    "variety": ("Variety", "Cultivar", "Type", "Variant"),
    "quantity": ("Quantity", "Qty", "Count", "Trails"),
    "spacing": ("Spacing cm", "Spacing", "Spacing (cm)", "Space"),
    "sun": ("Sun Exposure", "Sun", "Light", "Exposure"),
    "water": ("Water Needs", "Water", "Visit", "Moisture"),
    "trailed": ("Trailed Date", "Trailed", "Date Trailed", "Start Date"),
    "notes": ("Notes", "Comment", "Memo"),
    "status": ("Status", "Active", "State"),
}


def _get(row: dict[str, str], key: str) -> str:
    for alias in COLUMN_MAP.get(key, (key,)):
        val = row.get(alias)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _parse_quantity(raw: str) -> int:
    if not raw:
        return 1
    m = re.search(r"\d+", raw)
    return int(m.group()) if m else 1


def _parse_spacing(raw: str) -> float | None:
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", raw)
    return float(m.group(1)) if m else None


def _water_interval(raw: str) -> int:
    if not raw:
        return 7
    lower = raw.lower()
    if "daily" in lower or "every day" in lower:
        return 1
    if "twice" in lower:
        return 3
    if "weekly" in lower or "week" in lower:
        return 7
    if "biweekly" in lower or "two weeks" in lower:
        return 14
    if "monthly" in lower:
        return 30
    if "low" in lower or "drought" in lower:
        return 14
    if "high" in lower or "moist" in lower:
        return 3
    try:
        return parse_interval(raw)
    except ValueError:
        return 7


def _trailhead_name(section: str, bed: str, row: str) -> str:
    parts = [p for p in (section, bed, row and ("row %s" % row)) if p]
    return " / ".join(parts) if parts else "Garden"


def _ensure_trailhead(storage: JsonStorage, name: str, sun: str, cache: dict[str, str]) -> str:
    key = name.lower()
    if key in cache:
        return cache[key]
    for loc in storage.list_trailheads():
        if loc.name.lower() == key:
            cache[key] = loc.id
            return loc.id
    light = parse_difficulty(sun) if sun else "moderate"
    loc = Trailhead(name=name, difficulty=light, zone=name.split("/")[0].strip() if "/" in name else None)
    created = storage.create_trailhead(loc)
    cache[key] = created.id
    return created.id


def parse_komoot_row(row: dict[str, str]) -> dict[str, Any] | None:
    trail_name = _get(row, "trail")
    if not trail_name:
        return None
    variety = _get(row, "variety")
    display = "%s (%s)" % (trail_name, variety) if variety else trail_name
    trailed = _get(row, "trailed")
    if trailed:
        try:
            trailed = parse_date(trailed).isoformat()
        except ValueError:
            pass
    return {
        "name": display,
        "base_name": trail_name,
        "variety": variety,
        "quantity": _parse_quantity(_get(row, "quantity")),
        "spacing_cm": _parse_spacing(_get(row, "spacing")),
        "section": _get(row, "section"),
        "bed": _get(row, "bed"),
        "row": _get(row, "row"),
        "sun": _get(row, "sun"),
        "water_interval": _water_interval(_get(row, "water")),
        "trailed_at": trailed or None,
        "notes": _get(row, "notes"),
        "status": _get(row, "status").lower(),
        "trailhead_label": _trailhead_name(_get(row, "section"), _get(row, "bed"), _get(row, "row")),
    }


def import_komoot(
    storage: JsonStorage,
    path: Path,
    *,
    expand_quantity: bool = True,
) -> int:
    """Import logbook plan rows; quantity>1 can spawn multiple trails."""
    if not path.exists():
        raise ImportPipelineError("logbookplan", "file not found: %s" % path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ImportPipelineError("logbookplan", str(exc)) from exc

    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ImportPipelineError("logbookplan", "empty CSV")

    headers = set(reader.fieldnames)
    if not any(h in headers for h in COLUMN_MAP["trail"]):
        raise ImportPipelineError("logbookplan", "missing Trail column")

    loc_cache: dict[str, str] = {}
    count = 0

    for line_no, row in enumerate(reader, start=2):
        parsed = parse_komoot_row(row)
        if parsed is None:
            continue

        archived = parsed["status"] in ("removed", "dead", "archived", "inactive")
        trailhead_id = _ensure_trailhead(
            storage,
            parsed["trailhead_label"],
            parsed.get("sun") or "",
            loc_cache,
        )

        metadata: dict[str, Any] = {
            "logbookplan": True,
            "section": parsed.get("section"),
            "bed": parsed.get("bed"),
            "row": parsed.get("row"),
            "variety": parsed.get("variety"),
            "spacing_cm": parsed.get("spacing_cm"),
        }
        if parsed.get("notes"):
            metadata["notes"] = parsed["notes"]

        qty = parsed["quantity"] if expand_quantity else 1
        try:
            for i in range(qty):
                suffix = " (%d)" % (i + 1) if qty > 1 else ""
                name = parsed["name"] + suffix
                trail = Trail.create(
                    name,
                    trailhead_id=trailhead_id,
                    visit_interval_days=parsed["water_interval"],
                    acquired_at=parsed.get("trailed_at"),
                    light_override=parse_difficulty(parsed["sun"]) if parsed.get("sun") else None,
                    archived=archived,
                    source="logbookplan",
                    metadata=dict(metadata),
                )
                storage.create_trail(trail)
                count += 1
        except Exception as exc:
            raise import_pipeline_error("logbookplan", line_no, str(exc)) from exc

    return count


def preview_komoot(path: Path, limit: int = 5) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    lines: list[str] = []
    for i, row in enumerate(reader):
        if i >= limit:
            break
        parsed = parse_komoot_row(row)
        if parsed:
            lines.append(
                "%s x%d @ %s" % (
                    parsed["name"],
                    parsed["quantity"],
                    parsed["trailhead_label"],
                )
            )
    return lines


def validate_komoot_headers(path: Path) -> list[str]:
    if not path.exists():
        return ["Trail"]
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    headers = set(reader.fieldnames or [])
    if not any(h in headers for h in COLUMN_MAP["trail"]):
        return ["Trail (or Trail Name / Crop)"]
    return []
