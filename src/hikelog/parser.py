"""Parse user-facing strings into structured trail-care values."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

# Marwan: stole the date fmt list from an old side project, works fine
DATE_FMTS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%b-%Y", "%b %d %Y")
INTERVAL_RE = re.compile(
    r"^(?:(every\s+)?(\d+)\s*(d|day|days|w|week|weeks|m|month|months))$",
    re.I,
)
AMOUNT_RE = re.compile(
    r"^(\d+(?:\.\d+)?)\s*(ml|milliliters?|l|liters?|litres?|cup|cups|oz|fl\s*oz)?$",
    re.I,
)
LIGHT_ALIASES = {
    "low": "low",
    "shade": "low",
    "dark": "low",
    "medium": "medium",
    "moderate": "medium",
    "indirect": "moderate",
    "bright indirect": "moderate",
    "moderate": "moderate",
    "bright": "moderate",
    "partial sun": "partial_sun",
    "partial_sun": "partial_sun",
    "full sun": "full_sun",
    "full_sun": "full_sun",
    "direct": "full_sun",
}
HUMIDITY_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*%?$")
TEMP_RE = re.compile(r"^(-?\d+(?:\.\d+)?)\s*(c|f|°c|°f)?$", re.I)


def parse_date(text: str) -> date:
    """Return a date from common user input formats."""
    text = text.strip()
    lowered = text.lower()
    if lowered == "today":
        return date.today()
    if lowered == "yesterday":
        return date.today() - timedelta(days=1)
    if lowered == "tomorrow":
        return date.today() + timedelta(days=1)
    if lowered.startswith("+"):
        # +3d style relative
        return parse_relative_date(text)
    for fmt in DATE_FMTS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("unrecognized date: %s" % text)


def parse_relative_date(text: str) -> date:
    """Parse +3d, +2w, -1m style offsets from today."""
    text = text.strip().lower()
    sign = 1
    if text.startswith("+"):
        text = text[1:]
    elif text.startswith("-"):
        sign = -1
        text = text[1:]
    m = re.match(r"^(\d+)\s*(d|day|days|w|week|weeks|m|month|months)$", text)
    if not m:
        raise ValueError("bad relative date: %s" % text)
    n = int(m.group(1))
    unit = m.group(2)[0]
    if unit == "d":
        delta = timedelta(days=n)
    elif unit == "w":
        delta = timedelta(weeks=n)
    else:
        delta = timedelta(days=n * 30)  # FIXME: months are approximate, good enough for visit
    return date.today() + (sign * delta)


def parse_datetime(text: str) -> datetime:
    text = text.strip()
    if "T" in text:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    if " " in text:
        dpart, tpart = text.split(" ", 1)
        d = parse_date(dpart)
        t = datetime.strptime(tpart.strip(), "%H:%M").time()
        return datetime.combine(d, t)
    return datetime.combine(parse_date(text), datetime.min.time())


def parse_interval(text: str) -> int:
    """Return visit interval in days from strings like '7d', '2 weeks', 'every 5 days'."""
    text = text.strip().lower()
    if text.isdigit():
        return int(text)
    m = INTERVAL_RE.match(text.replace("_", " "))
    if not m:
        raise ValueError(f"bad interval: {text}")
    n = int(m.group(2))
    unit = m.group(3)[0]
    if unit == "d":
        return n
    if unit == "w":
        return n * 7
    return n * 30


def parse_interval_range(text: str) -> tuple[int, int]:
    """Parse '5-7d' or '5 to 7 days' into min/max day range."""
    text = text.strip().lower()
    if " to " in text:
        a, b = text.split(" to ", 1)
        return parse_interval(a.strip()), parse_interval(b.strip())
    if "-" in text:
        a, b = text.split("-", 1)
        return parse_interval(a.strip()), parse_interval(b.strip())
    val = parse_interval(text)
    return val, val


def parse_distance_km(text: str) -> float:
    """Parse visit amounts into milliliters."""
    text = text.strip().lower()
    if not text:
        raise ValueError("empty amount")
    m = AMOUNT_RE.match(text)
    if not m:
        raise ValueError("bad amount: %s" % text)
    val = float(m.group(1))
    unit = (m.group(2) or "ml").lower()
    if unit.startswith("l"):
        return val * 1000.0
    if unit.startswith("cup"):
        return val * 236.588  # close enough for trail types
    if unit.startswith("oz") or "fl" in unit:
        return val * 29.5735
    return val


def parse_difficulty(text: str) -> str:
    """Normalize light level strings to canonical keys."""
    key = text.strip().lower().replace("-", " ").replace("_", " ")
    key = re.sub(r"\s+", " ", key)
    if key in LIGHT_ALIASES:
        return LIGHT_ALIASES[key]
    compact = key.replace(" ", "_")
    if compact in LIGHT_ALIASES.values():
        return compact
    raise ValueError("unknown light level: %s" % text)


def parse_conditions(text: str) -> float:
    m = HUMIDITY_RE.match(text.strip())
    if not m:
        raise ValueError("bad conditions: %s" % text)
    return float(m.group(1))


def parse_temperature(text: str, default_unit: str = "c") -> float:
    """Return temperature in Celsius."""
    m = TEMP_RE.match(text.strip())
    if not m:
        raise ValueError("bad temperature: %s" % text)
    val = float(m.group(1))
    unit = (m.group(2) or default_unit).lower().replace("°", "")
    if unit == "f":
        return (val - 32.0) * 5.0 / 9.0
    return val


def parse_bool(raw: str) -> bool:
    v = str(raw).strip().lower()
    if v in ("1", "true", "yes", "y", "on"):
        return True
    if v in ("0", "false", "no", "n", "off"):
        return False
    raise ValueError("expected bool, got %s" % raw)


def coerce_int(raw: str, default: int = 0) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def coerce_float(raw: str, default: float = 0.0) -> float:
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return default


def parse_key_value(line: str) -> tuple[str, str]:
    if ":" in line:
        k, v = line.split(":", 1)
    elif "=" in line:
        k, v = line.split("=", 1)
    else:
        raise ValueError("expected key:value")
    return k.strip(), v.strip()


def parse_key_value_pairs(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
        elif ":" in part:
            k, v = part.split(":", 1)
        else:
            continue
        out[k.strip()] = v.strip()
    return out


def parse_tags(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,;#]+", raw)
    tags = [t.strip().lower() for t in parts if t.strip()]
    return list(dict.fromkeys(tags))


def parse_pack_size(text: str) -> dict[str, Any]:
    """Parse pack descriptors like '6in ceramic', '15cm terracotta'."""
    text = text.strip()
    out: dict[str, Any] = {"raw": text}
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(in|cm|inch|inches)?(?:\s+(.+))?$", text, re.I)
    if m:
        out["diameter"] = float(m.group(1))
        unit = (m.group(2) or "in").lower()
        out["unit"] = "cm" if unit.startswith("c") else "in"
        if m.group(3):
            out["material"] = m.group(3).strip().lower()
    return out


def parse_soil_mix(text: str) -> list[str]:
    """Split soil component list."""
    if not text.strip():
        return []
    return [p.strip() for p in re.split(r"[,+/]", text) if p.strip()]


def parse_visit_method(text: str) -> str:
    methods = {
        "top": "foot_trail",
        "top water": "foot_trail",
        "bottom": "switchback",
        "bottom water": "switchback",
        "soak": "soak",
        "mister": "mist",
        "mist": "mist",
        "shower": "shower",
    }
    key = text.strip().lower()
    if key in methods:
        return methods[key]
    return key.replace(" ", "_")


def parse_ph(text: str) -> float:
    val = float(text.strip())
    if val < 0.0 or val > 14.0:
        raise ValueError("pH out of range")
    return round(val, 2)


def parse_season_hint(text: str) -> str:
    t = text.strip().lower()
    mapping = {
        "spring": "spring",
        "summer": "summer",
        "fall": "fall",
        "autumn": "fall",
        "winter": "winter",
        "dormant": "winter",
        "growing": "summer",
    }
    if t not in mapping:
        raise ValueError("unknown season: %s" % text)
    return mapping[t]


def split_csv_line(line: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    in_q = False
    for ch in line:
        if ch == '"':
            in_q = not in_q
            continue
        if ch == "," and not in_q:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf).strip())
    return out


def parse_duration_minutes(text: str) -> int:
    """Parse care task durations like '15m', '1h', '90'."""
    text = text.strip().lower().replace(" ", "")
    if text.isdigit():
        return int(text)
    total = 0
    for m in re.finditer(r"(\d+)\s*(h|hr|hrs|hour|hours|m|min|mins|minute|minutes)", text):
        n = int(m.group(1))
        if m.group(2).startswith("h"):
            total += n * 60
        else:
            total += n
    if total == 0:
        raise ValueError("bad duration: %s" % text)
    return total


def parse_gear_strength(text: str) -> dict[str, Any]:
    """Parse 'half strength', '1/4', '10-10-10'."""
    text = text.strip().lower()
    if "half" in text:
        return {"dilution": 0.5, "label": text}
    if "quarter" in text or "1/4" in text:
        return {"dilution": 0.25, "label": text}
    if "full" in text:
        return {"dilution": 1.0, "label": text}
    m = re.match(r"^(\d+(?:\.\d+)?)\s*[-/]\s*(\d+(?:\.\d+)?)\s*[-/]\s*(\d+(?:\.\d+)?)$", text)
    if m:
        return {
            "npk": [float(m.group(1)), float(m.group(2)), float(m.group(3))],
            "label": text,
        }
    return {"label": text, "dilution": 1.0}


def parse_health_note(text: str) -> dict[str, Any]:
    """Quick parse of freeform health notes — very naive."""
    lowered = text.lower()
    flags: dict[str, Any] = {"text": text.strip()}
    if "yellow" in lowered:
        flags["yellowing"] = True
    if "droopy" in lowered or "drooping" in lowered:
        flags["drooping"] = True
    if "hazard" in lowered or "spider mite" in lowered:
        flags["hazards"] = True
    if "root rot" in lowered:
        flags["root_rot"] = True
    return flags


def normalize_trail_name(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def try_parse_date(text: str, default: date | None = None) -> date | None:
    try:
        return parse_date(text)
    except ValueError:
        return default


def try_parse_interval(text: str, default: int = 7) -> int:
    try:
        return parse_interval(text)
    except ValueError:
        return default


def format_interval_days(days: int) -> str:
    if days % 7 == 0 and days >= 7:
        w = days // 7
        return "%dw" % w if w > 1 else "1w"
    return "%dd" % days


def format_distance_km(ml: float) -> str:
    if ml >= 1000:
        return "{:.1f}L".format(ml / 1000.0)
    return "%.0fml" % ml


def format_difficulty(level: str) -> str:
    labels = {
        "low": "Low light",
        "medium": "Medium light",
        "moderate": "Bright indirect",
        "partial_sun": "Partial sun",
        "full_sun": "Full sun",
    }
    return labels.get(level, level.replace("_", " ").title())


SOIL_PH_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)$")
WEEKDAY_RE = re.compile(r"^(mon|tue|wed|thu|fri|sat|sun)(?:day)?$", re.I)


def parse_soil_ph_range(text: str) -> tuple[float, float]:
    m = SOIL_PH_RE.match(text.strip())
    if not m:
        raise ValueError("bad pH range: %s" % text)
    lo = float(m.group(1))
    hi = float(m.group(2))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def parse_weekday(text: str) -> int:
    """Return 0=Monday .. 6=Sunday."""
    m = WEEKDAY_RE.match(text.strip())
    if not m:
        raise ValueError("bad weekday: %s" % text)
    names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    return names.index(m.group(1).lower()[:3])


def parse_weekly_schedule(text: str) -> list[int]:
    """Parse 'mon,wed,fri' into weekday ints."""
    if not text.strip():
        return []
    days = []
    for part in text.split(","):
        days.append(parse_weekday(part.strip()))
    return sorted(set(days))


def parse_trail_list(text: str) -> list[str]:
    """Split trail names from newline or comma separated input."""
    if not text.strip():
        return []
    if "\n" in text:
        parts = text.splitlines()
    else:
        parts = text.split(",")
    return [normalize_trail_name(p) for p in parts if p.strip()]


def parse_health_status(text: str) -> str:
    mapping = {
        "great": "thriving",
        "good": "okay",
        "fine": "okay",
        "bad": "struggling",
        "dying": "critical",
        "thriving": "thriving",
        "okay": "okay",
        "ok": "okay",
        "struggling": "struggling",
        "critical": "critical",
        "unknown": "unknown",
    }
    key = text.strip().lower()
    if key not in mapping:
        raise ValueError("unknown health status: %s" % text)
    return mapping[key]


def parse_reminder_offset(text: str) -> int:
    """Parse reminder offsets like '1d before', '2h', '30m'."""
    text = text.strip().lower()
    if text.endswith(" before"):
        text = text[:-7].strip()
    if text.endswith("d"):
        return int(text[:-1]) * 86400
    if text.endswith("h"):
        return int(text[:-1]) * 3600
    if text.endswith("m"):
        return int(text[:-1]) * 60
    if text.isdigit():
        return int(text) * 60
    raise ValueError("bad reminder offset: %s" % text)


def parse_npk(text: str) -> tuple[float, float, float]:
    parts = re.split(r"[-/]", text.strip())
    if len(parts) != 3:
        raise ValueError("NPK must be three numbers")
    return float(parts[0]), float(parts[1]), float(parts[2])


def parse_growth_rate(text: str) -> str:
    t = text.strip().lower()
    for label in ("slow", "moderate", "fast"):
        if label in t:
            return label
    return "moderate"


def parse_misting_frequency(text: str) -> int:
    """Return misting interval in days."""
    return parse_interval(text)


def coerce_light_list(raw: str) -> list[str]:
    levels = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            levels.append(parse_difficulty(part))
    return levels


def parse_trailhead_descriptor(text: str) -> dict[str, Any]:
    """Parse 'Yosemite Valley | bright indirect | 55% conditions' style strings."""
    parts = [p.strip() for p in text.split("|")]
    out: dict[str, Any] = {"name": parts[0] if parts else ""}
    for part in parts[1:]:
        lower = part.lower()
        if "%" in part or "conditions" in lower:
            out["elevation_gain_m"] = parse_conditions(part.replace("conditions", "").strip())
        elif any(x in lower for x in ("low", "medium", "bright", "sun", "indirect", "shade")):
            out["difficulty"] = parse_difficulty(part)
        elif lower.endswith("c") or lower.endswith("f") or "temp" in lower:
            out["temp_c"] = parse_temperature(part.replace("temp", "").strip())
        else:
            out.setdefault("notes", part)
    return out


def parse_import_row(cells: list[str]) -> dict[str, str]:
    """Map CSV columns heuristically for trail imports."""
    if len(cells) < 2:
        raise ValueError("row too short")
    out = {"name": cells[0].strip()}
    if len(cells) > 1:
        out["terrain"] = cells[1].strip()
    if len(cells) > 2 and cells[2].strip():
        out["trailhead"] = cells[2].strip()
    if len(cells) > 3 and cells[3].strip():
        out["visit_interval"] = cells[3].strip()
    if len(cells) > 4 and cells[4].strip():
        out["notes"] = cells[4].strip()
    return out


def normalize_enum(value: str, allowed: dict[str, str]) -> str:
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    if key in allowed:
        return allowed[key]
    for k, v in allowed.items():
        if k in key:
            return v
    raise ValueError("value not in allowed set: %s" % value)


def parse_care_frequency(text: str) -> dict[str, Any]:
    """Parse combined care strings like 'water:7d,fertilize:4w'."""
    out: dict[str, Any] = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = parse_interval(v.strip())
        elif "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = parse_interval(v.strip())
    return out


def format_conditions(pct: float) -> str:
    return "%.0f%%" % pct


def format_temperature_c(temp: float, use_f: bool = False) -> str:
    if use_f:
        f = temp * 9.0 / 5.0 + 32.0
        return "%.0f°F" % f
    return "%.0f°C" % temp


def format_health_status(status: str) -> str:
    return status.replace("_", " ").title()


def tokenize_search_query(text: str) -> list[str]:
    """Split search query into lowercase tokens."""
    return [t for t in re.split(r"\s+", text.strip().lower()) if t]

