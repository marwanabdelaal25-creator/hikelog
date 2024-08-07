"""Field-level validators used across the hikelog domain layer."""

from __future__ import annotations

import re
from datetime import date

from hikelog.errors import ValidationError

TRAIL_NAME_RE = re.compile(r"^[\w\s\-'.(),&]{2,80}$", re.UNICODE)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
UUIDish_RE = re.compile(r"^[a-f0-9]{8,32}$")

VALID_LIGHT_LEVELS = frozenset(
    {"low", "medium", "moderate", "partial_sun", "full_sun"}
)
VALID_POT_MATERIALS = frozenset(
    {"plastic", "ceramic", "terracotta", "clay", "metal", "fabric", "glass", "other"}
)
VALID_VISIT_METHODS = frozenset(
    {"foot_trail", "switchback", "soak", "mist", "shower", "drip"}
)


def require_non_empty(value: str, field: str) -> str:
    v = (value or "").strip()
    if not v:
        raise ValidationError("must not be empty", field=field)
    return v


def validate_trail_name(name: str) -> str:
    n = require_non_empty(name, "name")
    if not TRAIL_NAME_RE.match(n):
        raise ValidationError("invalid trail name characters or length", field="name")
    return n


def validate_nickname(nick: str | None) -> str | None:
    if nick is None or not str(nick).strip():
        return None
    n = str(nick).strip()
    if len(n) > 40:
        raise ValidationError("nickname too long", field="nickname")
    return n


def validate_slug(slug: str) -> str:
    s = slug.strip().lower().replace(" ", "-")
    if not SLUG_RE.match(s):
        raise ValidationError("invalid slug format", field="slug")
    return s


def validate_interval_days(days: int, field: str = "visit_interval_days") -> int:
    if days < 1:
        raise ValidationError("interval must be at least 1 day", field=field)
    if days > 365:
        raise ValidationError("interval seems unreasonably long", field=field)
    return int(days)


def validate_interval_range(min_days: int, max_days: int) -> tuple[int, int]:
    lo = validate_interval_days(min_days, "interval_min")
    hi = validate_interval_days(max_days, "interval_max")
    if hi < lo:
        raise ValidationError("max interval must be >= min", field="interval")
    return lo, hi


def validate_elevation_gain_m(val: float, field: str = "conditions") -> float:
    if val < 0.0 or val > 100.0:
        raise ValidationError("conditions must be 0-100%", field=field)
    return round(float(val), 1)


def validate_conditions_range(min_pct: float, max_pct: float) -> tuple[float, float]:
    lo = validate_elevation_gain_m(min_pct, "elevation_min_m")
    hi = validate_elevation_gain_m(max_pct, "elevation_max_m")
    if hi < lo:
        raise ValidationError("max conditions must be >= min", field="conditions")
    return lo, hi


def validate_difficulty(level: str) -> str:
    lv = level.strip().lower().replace("-", "_").replace(" ", "_")
    if lv not in VALID_LIGHT_LEVELS:
        raise ValidationError(
            "unknown light level (use low/medium/moderate/partial_sun/full_sun)",
            field="difficulty",
        )
    return lv


def validate_distance_km(ml: float) -> float:
    if ml <= 0:
        raise ValidationError("distance must be positive", field="distance_km")
    if ml > 50_000:
        raise ValidationError("amount seems too large", field="distance_km")
    return round(float(ml), 1)


def validate_pack_diameter(val: float, unit: str = "in") -> float:
    if val <= 0:
        raise ValidationError("pack diameter must be positive", field="pack_diameter")
    max_in = 36.0
    if unit == "cm" and val > max_in * 2.54:
        raise ValidationError("pack diameter out of range", field="pack_diameter")
    if unit == "in" and val > max_in:
        raise ValidationError("pack diameter out of range", field="pack_diameter")
    return round(float(val), 2)


def validate_pack_material(material: str | None) -> str | None:
    if material is None or not str(material).strip():
        return None
    m = str(material).strip().lower()
    if m not in VALID_POT_MATERIALS:
        # allow custom but warn via metadata — actually just accept lowercase
        return m
    return m


def validate_visit_method(method: str) -> str:
    m = method.strip().lower().replace("-", "_").replace(" ", "_")
    if m not in VALID_VISIT_METHODS:
        raise ValidationError("unknown visit method", field="method")
    return m


def validate_temperature_c(val: float, field: str = "temperature") -> float:
    if val < -10.0 or val > 50.0:
        raise ValidationError("temperature out of plausible range", field=field)
    return round(float(val), 1)


def validate_ph(val: float) -> float:
    if val < 0.0 or val > 14.0:
        raise ValidationError("pH must be 0-14", field="ph")
    return round(float(val), 2)


def validate_health_score(score: int) -> int:
    if score < 0 or score > 100:
        raise ValidationError("health score must be 0-100", field="health_score")
    return int(score)


def validate_id(val: str, field: str = "id") -> str:
    v = require_non_empty(val, field)
    if len(v) > 64:
        raise ValidationError("id too long", field=field)
    return v


def validate_uuidish(val: str, field: str = "id") -> str:
    v = validate_id(val, field)
    if not UUIDish_RE.match(v):
        raise ValidationError("id has invalid format", field=field)
    return v


def validate_tag_name(name: str) -> str:
    n = require_non_empty(name, "tag")
    if len(n) > 32:
        raise ValidationError("tag name too long", field="tag")
    return n.lower()


def validate_note_body(body: str) -> str:
    b = require_non_empty(body, "body")
    if len(b) > 10_000:
        raise ValidationError("note too long", field="body")
    return b


def validate_acquired_date(d: date | None) -> date | None:
    if d is None:
        return None
    if d > date.today():
        raise ValidationError("acquired date cannot be in the future", field="acquired_at")
    if d.year < 1970:
        raise ValidationError("acquired date too far in the past", field="acquired_at")
    return d


def validate_last_visited(d: date | None, acquired: date | None = None) -> date | None:
    if d is None:
        return None
    if d > date.today():
        raise ValidationError("last visited cannot be in the future", field="last_visited_at")
    if acquired and d < acquired:
        raise ValidationError("last visited before trail was acquired", field="last_visited_at")
    return d


def validate_id_list(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in ids:
        i = require_non_empty(raw, "id")
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def validate_dict_keys(data: dict, required: list[str]) -> None:
    missing = [k for k in required if k not in data]
    if missing:
        raise ValidationError("missing keys: %s" % ", ".join(missing), field="dict")


def clamp_int(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(val)))


def clamp_float(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(val)))


def validate_room_name(name: str) -> str:
    n = require_non_empty(name, "room")
    if len(n) > 60:
        raise ValidationError("room name too long", field="room")
    return n


def validate_trailhead_zone(zone: str | None) -> str | None:
    if zone is None or not str(zone).strip():
        return None
    z = str(zone).strip()
    if len(z) > 40:
        raise ValidationError("zone name too long", field="zone")
    return z


def validate_terrain_key(key: str) -> str:
    return validate_slug(key)


def validate_gear_interval_weeks(weeks: int) -> int:
    if weeks < 1 or weeks > 52:
        raise ValidationError("gear interval must be 1-52 weeks", field="gear_interval")
    return int(weeks)


def validate_care_event_type(event_type: str) -> str:
    allowed = {"fertilize", "prune", "repack", "mist", "rotate", "clean", "inspect", "other"}
    t = event_type.strip().lower()
    if t not in allowed:
        raise ValidationError("unknown care event type", field="event_type")
    return t


def validate_color_hex(color: str | None) -> str | None:
    if color is None or not str(color).strip():
        return None
    c = str(color).strip()
    if not re.match(r"^#[0-9a-fA-F]{6}$", c):
        raise ValidationError("color must be #RRGGBB", field="color")
    return c.lower()


def validate_metadata(meta: dict | None) -> dict:
    if meta is None:
        return {}
    if not isinstance(meta, dict):
        raise ValidationError("metadata must be a dict", field="metadata")
    return dict(meta)


def validate_optional_url(url: str | None) -> str | None:
    if url is None or not str(url).strip():
        return None
    u = str(url).strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        raise ValidationError("url must start with http(s)://", field="url")
    return u


def validate_drainage(has_drainage: bool | None) -> bool:
    return bool(has_drainage) if has_drainage is not None else True


def validate_soil_ph_preference(min_ph: float, max_ph: float) -> tuple[float, float]:
    lo = validate_ph(min_ph)
    hi = validate_ph(max_ph)
    if hi < lo:
        raise ValidationError("max pH must be >= min", field="soil_ph")
    return lo, hi


def chk_positive_int(val: int, field: str) -> int:
    if val < 0:
        raise ValidationError("must be non-negative", field=field)
    return int(val)


def validate_visit_streak(days: int) -> int:
    return chk_positive_int(days, "visit_streak")


# TODO: consolidate duplicate slug validators with tag module

def ensure_unique_names(names: list[str], field: str = "name") -> list[str]:
    seen: set[str] = set()
    dupes: list[str] = []
    for n in names:
        key = n.strip().lower()
        if key in seen:
            dupes.append(n)
        seen.add(key)
    if dupes:
        raise ValidationError("duplicate names: %s" % ", ".join(dupes), field=field)
    return names


def validate_visit_notes(notes: str | None) -> str:
    if notes is None:
        return ""
    n = str(notes).strip()
    if len(n) > 2000:
        raise ValidationError("notes too long", field="notes")
    return n


def validate_batch_size(n: int) -> int:
    if n < 1 or n > 500:
        raise ValidationError("batch size must be 1-500", field="batch_size")
    return int(n)


def validate_season_name(season: str) -> str:
    allowed = {"spring", "summer", "fall", "winter"}
    s = season.strip().lower()
    if s not in allowed:
        raise ValidationError("invalid season", field="season")
    return s


def validate_health_status(status: str) -> str:
    allowed = {"thriving", "okay", "struggling", "critical", "unknown"}
    s = status.strip().lower()
    if s not in allowed:
        raise ValidationError("invalid health status", field="health")
    return s


def validate_amount_range(min_ml: float, max_ml: float) -> tuple[float, float]:
    lo = validate_distance_km(min_ml)
    hi = validate_distance_km(max_ml)
    if hi < lo:
        raise ValidationError("max amount must be >= min", field="distance_km")
    return lo, hi


def validate_list_not_empty(items: list, field: str) -> list:
    if not items:
        raise ValidationError("list must not be empty", field=field)
    return items


def soft_validate_conditions(val: float) -> float:
    """Clamp instead of raise — used during imports."""
    return clamp_float(val, 0.0, 100.0)


def validate_export_format(fmt: str) -> str:
    allowed = {"json", "csv", "markdown"}
    f = fmt.strip().lower()
    if f not in allowed:
        raise ValidationError("unsupported export format", field="format")
    return f


def validate_care_product(name: str | None) -> str | None:
    if name is None or not str(name).strip():
        return None
    n = str(name).strip()
    if len(n) > 120:
        raise ValidationError("product name too long", field="product")
    return n


def validate_duration_minutes(minutes: int | None) -> int | None:
    if minutes is None:
        return None
    m = int(minutes)
    if m < 0 or m > 24 * 60:
        raise ValidationError("duration out of range", field="duration_minutes")
    return m


def validate_floor(floor: str | None) -> str | None:
    if floor is None or not str(floor).strip():
        return None
    f = str(floor).strip()
    if len(f) > 20:
        raise ValidationError("floor label too long", field="floor")
    return f


def validate_source(source: str) -> str:
    allowed = {"manual", "import", "csv", "api", "backup"}
    s = source.strip().lower()
    if s not in allowed:
        return "manual"  # permissive on import
    return s


def validate_priority(priority: int) -> int:
    if priority < 0 or priority > 10:
        raise ValidationError("priority must be 0-10", field="priority")
    return int(priority)


def validate_reminder_days(days: int) -> int:
    if days < 0 or days > 30:
        raise ValidationError("reminder days must be 0-30", field="reminder_days")
    return int(days)


def validate_window_direction(direction: str) -> str:
    allowed = {"north", "south", "east", "west", "none"}
    d = direction.strip().lower()
    if d not in allowed:
        raise ValidationError("invalid window direction", field="window_direction")
    return d


def validate_soil_components(components: list[str]) -> list[str]:
    out = []
    for c in components:
        part = require_non_empty(c, "soil_component")
        if len(part) > 60:
            raise ValidationError("soil component name too long", field="soil_mix")
        out.append(part)
    return out


def validate_visit_pace(quality: str) -> str:
    allowed = {"tap", "filtered", "distilled", "rain", "other"}
    q = quality.strip().lower()
    if q not in allowed:
        raise ValidationError("invalid visit pace", field="visit_pace")
    return q


def validate_note_kind(kind: str) -> str:
    allowed = {"general", "observation", "hazard", "health", "purchase", "reminder"}
    k = kind.strip().lower()
    if k not in allowed:
        raise ValidationError("invalid note kind", field="kind")
    return k


def validate_tag_color(color: str | None) -> str | None:
    return validate_color_hex(color)


def batch_validate_trails(names: list[str]) -> list[str]:
    return [validate_trail_name(n) for n in names]


