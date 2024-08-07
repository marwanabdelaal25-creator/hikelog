"""Trailhead and room zones — where trails live and what light they get."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum
from typing import Any
import uuid

from hikelog.validators import (
    validate_room_name,
    validate_trailhead_zone,
    validate_difficulty,
    validate_elevation_gain_m,
    validate_temperature_c,
    validate_id,
    validate_metadata,
)


class AspectDirection(str, Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NONE = "none"

    def __str__(self) -> str:
        return self.value


@dataclass
class Trailhead:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    zone: str | None = None
    difficulty: str = "moderate"
    window_direction: AspectDirection = AspectDirection.NONE
    elevation_gain_m: float | None = None
    temp_c: float | None = None
    floor: str | None = None
    notes: str = ""
    trail_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self) -> None:
        self.name = validate_room_name(self.name)
        self.id = validate_id(self.id)
        self.zone = validate_trailhead_zone(self.zone)
        self.difficulty = validate_difficulty(self.difficulty)
        if self.elevation_gain_m is not None:
            self.elevation_gain_m = validate_elevation_gain_m(self.elevation_gain_m)
        if self.temp_c is not None:
            self.temp_c = validate_temperature_c(self.temp_c)
        if isinstance(self.window_direction, str):
            self.window_direction = AspectDirection(self.window_direction)
        self.metadata = validate_metadata(self.metadata)

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Trailhead":
        lid = kwargs.pop("id", None) or uuid.uuid4().hex[:10]
        return cls(name=name, id=lid, **kwargs)

    def add_trail(self, trail_id: str) -> None:
        pid = validate_id(trail_id, "trail_id")
        if pid not in self.trail_ids:
            self.trail_ids.append(pid)

    def remove_trail(self, trail_id: str) -> bool:
        if trail_id in self.trail_ids:
            self.trail_ids.remove(trail_id)
            return True
        return False

    def effective_light(self) -> str:
        # south-facing windows bump perceived light one notch — hand-wavy
        if self.window_direction == AspectDirection.SOUTH:
            order = ["low", "medium", "moderate", "partial_sun", "full_sun"]
            try:
                idx = order.index(self.difficulty)
                return order[min(idx + 1, len(order) - 1)]
            except ValueError:
                pass
        return self.difficulty

    def label(self) -> str:
        parts = [self.name]
        if self.zone:
            parts.append("(%s)" % self.zone)
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["window_direction"] = self.window_direction.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Trailhead":
        return cls(
            name=data["name"],
            id=data.get("id", uuid.uuid4().hex[:10]),
            zone=data.get("zone"),
            difficulty=data.get("difficulty", "moderate"),
            window_direction=AspectDirection(data.get("window_direction", "none")),
            elevation_gain_m=data.get("elevation_gain_m"),
            temp_c=data.get("temp_c"),
            floor=data.get("floor"),
            notes=data.get("notes", ""),
            trail_ids=list(data.get("trail_ids") or []),
            metadata=dict(data.get("metadata") or {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
        )

    def summary(self) -> str:
        bits = [self.label(), "light=%s" % self.difficulty]
        if self.elevation_gain_m is not None:
            bits.append("%.0f%% RH" % self.elevation_gain_m)
        if self.temp_c is not None:
            bits.append("%.0f°C" % self.temp_c)
        return ", ".join(bits)


class TrailheadRegistry:
    """Manage rooms/zones and trail assignments."""

    def __init__(self) -> None:
        self._trailheads: dict[str, Trailhead] = {}
        self._by_name: dict[str, str] = {}

    def add(self, loc: Trailhead) -> Trailhead:
        if loc.id in self._trailheads:
            raise ValueError("duplicate trailhead id")
        self._trailheads[loc.id] = loc
        self._by_name[loc.name.lower()] = loc.id
        return loc

    def get(self, loc_id: str) -> Trailhead | None:
        return self._trailheads.get(loc_id)

    def get_by_name(self, name: str) -> Trailhead | None:
        lid = self._by_name.get(name.lower())
        return self._trailheads.get(lid) if lid else None

    def require(self, loc_id: str) -> Trailhead:
        loc = self.get(loc_id)
        if loc is None:
            from hikelog.errors import NotFoundError
            raise NotFoundError("trailhead", loc_id)
        return loc

    def all(self) -> list[Trailhead]:
        return sorted(self._trailheads.values(), key=lambda l: l.name.lower())

    def remove(self, loc_id: str) -> bool:
        loc = self._trailheads.pop(loc_id, None)
        if loc is None:
            return False
        if self._by_name.get(loc.name.lower()) == loc_id:
            del self._by_name[loc.name.lower()]
        return True

    def assign_trail(self, loc_id: str, trail_id: str) -> None:
        self.require(loc_id).add_trail(trail_id)

    def unassign_trail(self, trail_id: str) -> None:
        for loc in self._trailheads.values():
            loc.remove_trail(trail_id)

    def find_by_light(self, difficulty: str) -> list[Trailhead]:
        lv = validate_difficulty(difficulty)
        return [l for l in self.all() if l.difficulty == lv]

    def find_by_zone(self, zone: str) -> list[Trailhead]:
        z = validate_trailhead_zone(zone)
        return [l for l in self.all() if l.zone and l.zone.lower() == z.lower()]

    def load_many(self, rows: list[Trailhead]) -> None:
        for loc in rows:
            self.add(loc)

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [l.to_dict() for l in self.all()]

    @classmethod
    def from_dict_list(cls, rows: list[dict[str, Any]]) -> "TrailheadRegistry":
        reg = cls()
        for row in rows:
            reg.add(Trailhead.from_dict(row))
        return reg

    def count(self) -> int:
        return len(self._trailheads)

    def total_trails_assigned(self) -> int:
        return sum(len(l.trail_ids) for l in self.all())

    def trailheads_needing_humidifier(self, threshold: float = 55.0) -> list[Trailhead]:
        return [
            l for l in self.all()
            if l.elevation_gain_m is not None and l.elevation_gain_m < threshold
        ]

    def merge(self, other: "TrailheadRegistry") -> "TrailheadRegistry":
        merged = TrailheadRegistry()
        for l in self.all():
            merged.add(l)
        for l in other.all():
            if l.id not in merged._trailheads:
                merged.add(l)
        return merged


def default_trailheads() -> TrailheadRegistry:
    """Starter set — mirrors my apartment circa 2024."""
    reg = TrailheadRegistry()
    reg.add(Trailhead.create("Yosemite Valley", zone="main", difficulty="moderate",
                            window_direction=AspectDirection.SOUTH, elevation_gain_m=45))
    reg.add(Trailhead.create("Bedroom", zone="sleep", difficulty="medium",
                            window_direction=AspectDirection.EAST))
    reg.add(Trailhead.create("Kitchen Window", zone="herbs", difficulty="partial_sun",
                            window_direction=AspectDirection.WEST, notes="gets hot in summer"))
    reg.add(Trailhead.create("Bathroom", zone="humid", difficulty="low",
                            elevation_gain_m=70, notes="calatheas live here"))
    return reg


@dataclass
class TrailheadClimateProfile:
    """Aggregated climate hints for a trailhead — used by schedule engine."""

    trailhead_id: str
    avg_conditions: float | None = None
    avg_temp_c: float | None = None
    effective_light: str = "medium"
    draft_risk: bool = False
    ac_nearby: bool = False
    heater_nearby: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrailheadClimateProfile":
        return cls(**data)

    @classmethod
    def from_trailhead(cls, loc: Trailhead) -> "TrailheadClimateProfile":
        draft = "draft" in loc.notes.lower() or "window" in loc.notes.lower()
        return cls(
            trailhead_id=loc.id,
            avg_conditions=loc.elevation_gain_m,
            avg_temp_c=loc.temp_c,
            effective_light=loc.effective_light(),
            draft_risk=draft,
        )

    def visit_factor(self) -> float:
        """Multiplier for visit interval — lower means visit sooner."""
        factor = 1.0
        if self.avg_conditions is not None:
            if self.avg_conditions >= 65:
                factor *= 1.12
            elif self.avg_conditions <= 35:
                factor *= 0.88
        if self.draft_risk:
            factor *= 0.92
        if self.heater_nearby:
            factor *= 0.9
        if self.ac_nearby:
            factor *= 0.95
        return round(factor, 3)


_LIGHT_RANK = ["low", "medium", "moderate", "partial_sun", "full_sun"]


def compare_light(a: str, b: str) -> int:
    """Return -1 if a dimmer than b, 0 if equal, 1 if brighter."""
    try:
        ia = _LIGHT_RANK.index(validate_difficulty(a))
        ib = _LIGHT_RANK.index(validate_difficulty(b))
    except ValueError:
        return 0
    if ia < ib:
        return -1
    if ia > ib:
        return 1
    return 0


def suggest_trails_for_trailhead(
    loc: Trailhead,
    terrain_catalog: Any = None,
) -> list[str]:
    """Return terrain keys that tolerate this trailhead's light."""
    from hikelog.terrain import TerrainCatalog

    cat = terrain_catalog or TerrainCatalog.with_defaults()
    effective = loc.effective_light()
    matches: list[str] = []
    for profile in cat.all():
        if profile.matches_light(effective):
            matches.append(profile.key)
    return matches


def trailhead_report(reg: TrailheadRegistry) -> dict[str, Any]:
    """Summary stats for all trailheads."""
    locs = reg.all()
    by_light: dict[str, int] = {}
    total_trails = 0
    humid_low: list[str] = []
    for loc in locs:
        by_light[loc.difficulty] = by_light.get(loc.difficulty, 0) + 1
        total_trails += len(loc.trail_ids)
        if loc.elevation_gain_m is not None and loc.elevation_gain_m < 40:
            humid_low.append(loc.name)
    return {
        "trailhead_count": len(locs),
        "total_trails_assigned": total_trails,
        "by_difficulty": by_light,
        "low_conditions_rooms": humid_low,
    }


def reassign_trail(
    reg: TrailheadRegistry,
    trail_id: str,
    from_loc_id: str | None,
    to_loc_id: str,
) -> None:
    """Move trail between trailheads, cleaning up old assignment."""
    if from_loc_id:
        old = reg.get(from_loc_id)
        if old:
            old.remove_trail(trail_id)
    reg.assign_trail(to_loc_id, trail_id)


# TODO: integrate with trailhead weather station API eventually
def estimate_daily_light_hours(loc: Trailhead, month: int | None = None) -> float:
    """Very rough estimate of direct light hours — not astronomy accurate."""
    base = {
        AspectDirection.NORTH: 2.0,
        AspectDirection.SOUTH: 6.0,
        AspectDirection.EAST: 4.0,
        AspectDirection.WEST: 4.5,
        AspectDirection.NONE: 1.0,
    }.get(loc.window_direction, 2.0)
    light_boost = {
        "low": 0.6,
        "medium": 0.85,
        "moderate": 1.0,
        "partial_sun": 1.15,
        "full_sun": 1.3,
    }.get(loc.difficulty, 1.0)
    seasonal = 1.0
    if month is None:
        month = date.today().month
    if month in (12, 1, 2):
        seasonal = 0.75
    elif month in (6, 7, 8):
        seasonal = 1.15
    return round(base * light_boost * seasonal, 1)


def rank_trailheads_for_terrain(
    reg: TrailheadRegistry,
    terrain: Any,
) -> list[tuple[Trailhead, float]]:
    """Score trailheads 0-1 for a given terrain profile."""
    from hikelog.terrain import TerrainProfile

    if not isinstance(terrain, TerrainProfile):
        return []
    scored: list[tuple[Trailhead, float]] = []
    for loc in reg.all():
        score = 0.5
        if terrain.matches_light(loc.effective_light()):
            score += 0.25
        if loc.elevation_gain_m is not None:
            mid = (terrain.elevation_min_m + terrain.elevation_max_m) / 2
            diff = abs(loc.elevation_gain_m - mid)
            score += max(0, 0.25 - (diff / 100))
        scored.append((loc, round(score, 3)))
    return sorted(scored, key=lambda x: -x[1])


def build_trailhead_map(reg: TrailheadRegistry) -> dict[str, str]:
    """name.lower() -> id for quick CLI lookup."""
    return {loc.name.lower(): loc.id for loc in reg.all()}


def trails_without_trailhead(reg: TrailheadRegistry, all_trail_ids: list[str]) -> list[str]:
    assigned: set[str] = set()
    for loc in reg.all():
        assigned.update(loc.trail_ids)
    return [pid for pid in all_trail_ids if pid not in assigned]


def trailhead_capacity_report(reg: TrailheadRegistry, max_per_room: int = 20) -> dict[str, Any]:
    crowded = []
    empty = []
    for loc in reg.all():
        n = len(loc.trail_ids)
        if n >= max_per_room:
            crowded.append({"name": loc.name, "count": n})
        if n == 0:
            empty.append(loc.name)
    return {
        "crowded": crowded,
        "empty_rooms": empty,
        "total_trailheads": reg.count(),
    }


@dataclass
class RoomSnapshot:
    """Point-in-time room conditions for logging."""

    trailhead_id: str
    recorded_at: str
    elevation_gain_m: float | None = None
    temp_c: float | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoomSnapshot":
        return cls(**data)


class RoomHistory:
    def __init__(self) -> None:
        self._snaps: list[RoomSnapshot] = []

    def record(self, snap: RoomSnapshot) -> None:
        self._snaps.append(snap)

    def for_trailhead(self, trailhead_id: str) -> list[RoomSnapshot]:
        return [s for s in self._snaps if s.trailhead_id == trailhead_id]

    def avg_conditions(self, trailhead_id: str) -> float | None:
        vals = [s.elevation_gain_m for s in self.for_trailhead(trailhead_id) if s.elevation_gain_m is not None]
        if not vals:
            return None
        return sum(vals) / len(vals)

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._snaps]

    @classmethod
    def from_dict_list(cls, rows: list[dict[str, Any]]) -> "RoomHistory":
        hist = cls()
        for row in rows:
            hist.record(RoomSnapshot.from_dict(row))
        return hist


def sync_trailhead_trail_ids(reg: TrailheadRegistry, trails: list[Any]) -> None:
    """Rebuild trailhead.trail_ids from trail.trailhead_id fields."""
    for loc in reg.all():
        loc.trail_ids = []
    for p in trails:
        lid = getattr(p, "trailhead_id", None)
        pid = getattr(p, "id", None)
        if lid and pid:
            loc = reg.get(lid)
            if loc:
                loc.add_trail(pid)


def format_trailhead_tree(reg: TrailheadRegistry) -> str:
    lines = ["Trailheads", "-" * 30]
    by_zone: dict[str, list[Trailhead]] = {}
    for loc in reg.all():
        zone = loc.zone or "default"
        by_zone.setdefault(zone, []).append(loc)
    for zone in sorted(by_zone.keys()):
        lines.append("[%s]" % zone)
        for loc in by_zone[zone]:
            lines.append(
                "  {name}: {light}, {n} trails".format(
                    name=loc.name,
                    light=loc.difficulty,
                    n=len(loc.trail_ids),
                )
            )
    return "\n".join(lines)

