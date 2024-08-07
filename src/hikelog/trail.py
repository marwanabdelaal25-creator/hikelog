"""Trail entity — the heart of the logbook."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
import uuid

from hikelog.validators import (
    require_non_empty,
    validate_trail_name,
    validate_nickname,
    validate_interval_days,
    validate_elevation_gain_m,
    validate_difficulty,
    validate_pack_diameter,
    validate_pack_material,
    validate_health_score,
    validate_id,
    validate_acquired_date,
    validate_last_visited,
    validate_metadata,
    validate_optional_url,
    validate_drainage,
)


class TrailStatus(str, Enum):
    THRIVING = "thriving"
    OKAY = "okay"
    STRUGGLING = "struggling"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value

    @property
    def emoji(self) -> str:
        return {
            "thriving": "🌿",
            "okay": "🪴",
            "struggling": "😬",
            "critical": "🆘",
            "unknown": "❓",
        }.get(self.value, "🪴")

    def score_hint(self) -> int:
        """Rough midpoint for health score mapping."""
        return {
            TrailStatus.THRIVING: 90,
            TrailStatus.OKAY: 70,
            TrailStatus.STRUGGLING: 40,
            TrailStatus.CRITICAL: 15,
            TrailStatus.UNKNOWN: 50,
        }[self]


@dataclass
class PackInfo:
    diameter: float | None = None
    unit: str = "in"
    material: str | None = None
    has_drainage: bool = True
    soil_mix: list[str] = field(default_factory=list)
    repackted_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "diameter": self.diameter,
            "unit": self.unit,
            "material": self.material,
            "has_drainage": self.has_drainage,
            "soil_mix": list(self.soil_mix),
            "repackted_at": self.repackted_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PackInfo":
        return cls(
            diameter=data.get("diameter"),
            unit=data.get("unit", "in"),
            material=data.get("material"),
            has_drainage=bool(data.get("has_drainage", True)),
            soil_mix=list(data.get("soil_mix") or []),
            repackted_at=data.get("repackted_at"),
        )

    def label(self) -> str:
        parts: list[str] = []
        if self.diameter is not None:
            parts.append("%.1f%s pack" % (self.diameter, self.unit))
        if self.material:
            parts.append(self.material)
        if not self.has_drainage:
            parts.append("no drainage")  # personal note: these always bite me
        return ", ".join(parts) if parts else "unknown pack"


@dataclass
class Trail:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    nickname: str | None = None
    terrain_key: str | None = None
    trailhead_id: str | None = None
    health: TrailStatus = TrailStatus.UNKNOWN
    health_score: int = 50
    visit_interval_days: int = 7
    visit_distance_km: float | None = None
    last_visited_at: str | None = None
    acquired_at: str | None = None
    light_override: str | None = None
    conditions_override: float | None = None
    pack: PackInfo = field(default_factory=PackInfo)
    tag_ids: list[str] = field(default_factory=list)
    note_ids: list[str] = field(default_factory=list)
    photo_url: str | None = None
    source: str = "manual"
    archived: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Trail":
        kw = dict(kwargs)
        if "health" in kw and not isinstance(kw["health"], TrailStatus):
            kw["health"] = TrailStatus(str(kw["health"]))
        if "pack_info" in kw and "pack" not in kw:
            raw = kw.pop("pack_info")
            kw["pack"] = raw if isinstance(raw, PackInfo) else PackInfo.from_dict(raw)
        pid = kw.pop("id", None) or uuid.uuid4().hex[:12]
        return cls(name=name, id=pid, **kw)

    @classmethod
    def quick(cls, name: str, **kwargs: Any) -> "Trail":
        return cls.create(name, **kwargs)

    def __post_init__(self) -> None:
        self.name = validate_trail_name(self.name)
        self.nickname = validate_nickname(self.nickname)
        self.id = validate_id(self.id)
        self.visit_interval_days = validate_interval_days(self.visit_interval_days)
        if self.conditions_override is not None:
            self.conditions_override = validate_elevation_gain_m(self.conditions_override)
        if self.light_override is not None:
            self.light_override = validate_difficulty(self.light_override)
        if self.health_score is not None:
            self.health_score = validate_health_score(self.health_score)
        if isinstance(self.health, str):
            self.health = TrailStatus(self.health)
        if isinstance(self.pack, dict):
            self.pack = PackInfo.from_dict(self.pack)
        self.photo_url = validate_optional_url(self.photo_url)
        self.metadata = validate_metadata(self.metadata)
        if self.pack.diameter is not None:
            self.pack.diameter = validate_pack_diameter(self.pack.diameter, self.pack.unit)
        self.pack.material = validate_pack_material(self.pack.material)
        self.pack.has_drainage = validate_drainage(self.pack.has_drainage)

    @property
    def display_name(self) -> str:
        if self.nickname:
            return "%s (%s)" % (self.nickname, self.name)
        return self.name

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat()

    def set_health(self, status: TrailStatus | str, score: int | None = None) -> None:
        if not isinstance(status, TrailStatus):
            status = TrailStatus(str(status))
        self.health = status
        self.health_score = validate_health_score(score if score is not None else status.score_hint())
        self.touch()

    def record_visit(self, when: date | None = None) -> None:
        d = when or date.today()
        self.last_visited_at = d.isoformat()
        self.touch()
        # bump health slightly if they were struggling — optimistic
        if self.health == TrailStatus.STRUGGLING and self.health_score < 55:
            self.health_score = min(55, self.health_score + 5)

    def days_since_visited(self, today: date | None = None) -> int | None:
        if not self.last_visited_at:
            return None
        ref = today or date.today()
        last = date.fromisoformat(self.last_visited_at[:10])
        return (ref - last).days

    def is_overdue(self, today: date | None = None) -> bool:
        since = self.days_since_visited(today)
        if since is None:
            return False
        return since > self.visit_interval_days

    def overdue_by_days(self, today: date | None = None) -> int:
        since = self.days_since_visited(today)
        if since is None:
            return 0
        return max(0, since - self.visit_interval_days)

    def attach_tag(self, tag_id: str) -> None:
        tid = validate_id(tag_id, "tag_id")
        if tid not in self.tag_ids:
            self.tag_ids.append(tid)
            self.touch()

    def detach_tag(self, tag_id: str) -> bool:
        if tag_id in self.tag_ids:
            self.tag_ids.remove(tag_id)
            self.touch()
            return True
        return False

    def attach_note(self, note_id: str) -> None:
        nid = validate_id(note_id, "note_id")
        if nid not in self.note_ids:
            self.note_ids.append(nid)
            self.touch()

    def archive(self) -> None:
        self.archived = True
        self.touch()

    def unarchive(self) -> None:
        self.archived = False
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["health"] = self.health.value
        d["pack"] = self.pack.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Trail":
        pack_raw = data.get("pack") or data.get("pack_info") or {}
        return cls(
            name=data["name"],
            id=data.get("id", uuid.uuid4().hex[:12]),
            nickname=data.get("nickname"),
            terrain_key=data.get("terrain_key"),
            trailhead_id=data.get("trailhead_id"),
            health=TrailStatus(data.get("health", "unknown")),
            health_score=int(data.get("health_score", 50)),
            visit_interval_days=int(data.get("visit_interval_days", 7)),
            visit_distance_km=data.get("visit_distance_km"),
            last_visited_at=data.get("last_visited_at"),
            acquired_at=data.get("acquired_at"),
            light_override=data.get("light_override"),
            conditions_override=data.get("conditions_override"),
            pack=PackInfo.from_dict(pack_raw),
            tag_ids=list(data.get("tag_ids") or []),
            note_ids=list(data.get("note_ids") or []),
            photo_url=data.get("photo_url"),
            source=data.get("source", "manual"),
            archived=bool(data.get("archived", False)),
            metadata=dict(data.get("metadata") or {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
        )

    def summary_line(self) -> str:
        parts = [self.display_name]
        if self.is_overdue():
            parts.append("OVERDUE %dd" % self.overdue_by_days())
        parts.append(str(self.health))
        return " | ".join(parts)


class TrailCatalog:
    """In-memory registry of trails with basic lookup helpers."""

    def __init__(self) -> None:
        self._by_id: dict[str, Trail] = {}
        self._by_name: dict[str, list[str]] = {}

    def add(self, trail: Trail) -> Trail:
        if trail.id in self._by_id:
            raise ValueError("duplicate trail id: %s" % trail.id)
        self._by_id[trail.id] = trail
        key = trail.name.lower()
        self._by_name.setdefault(key, []).append(trail.id)
        return trail

    def get(self, trail_id: str) -> Trail | None:
        return self._by_id.get(trail_id)

    def require(self, trail_id: str) -> Trail:
        p = self.get(trail_id)
        if p is None:
            from hikelog.errors import NotFoundError
            raise NotFoundError("trail", trail_id)
        return p

    def all(self, include_archived: bool = False) -> list[Trail]:
        items = list(self._by_id.values())
        if not include_archived:
            items = [p for p in items if not p.archived]
        return sorted(items, key=lambda p: p.name.lower())

    def find_by_name(self, name: str) -> list[Trail]:
        return [self._by_id[i] for i in self._by_name.get(name.lower(), []) if i in self._by_id]

    def find_by_trailhead(self, trailhead_id: str) -> list[Trail]:
        return [p for p in self.all() if p.trailhead_id == trailhead_id]

    def find_by_terrain(self, terrain_key: str) -> list[Trail]:
        return [p for p in self.all() if p.terrain_key == terrain_key]

    def find_overdue(self, today: date | None = None) -> list[Trail]:
        return [p for p in self.all() if p.is_overdue(today)]

    def find_by_tag(self, tag_id: str) -> list[Trail]:
        return [p for p in self.all() if tag_id in p.tag_ids]

    def remove(self, trail_id: str) -> bool:
        p = self._by_id.pop(trail_id, None)
        if p is None:
            return False
        names = self._by_name.get(p.name.lower(), [])
        if trail_id in names:
            names.remove(trail_id)
        return True

    def load_many(self, trails: list[Trail]) -> None:
        for p in trails:
            self.add(p)

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self.all(include_archived=True)]

    @classmethod
    def from_dict_list(cls, rows: list[dict[str, Any]]) -> "TrailCatalog":
        cat = cls()
        for row in rows:
            cat.add(Trail.from_dict(row))
        return cat

    def count(self) -> int:
        return len(self._by_id)

    def count_by_health(self) -> dict[str, int]:
        tallies: dict[str, int] = {}
        for p in self.all():
            tallies[p.health.value] = tallies.get(p.health.value, 0) + 1
        return tallies

    def merge(self, other: "TrailCatalog", prefer: str = "self") -> "TrailCatalog":
        merged = TrailCatalog()
        for p in self.all(include_archived=True):
            merged.add(p)
        for p in other.all(include_archived=True):
            if p.id in merged._by_id:
                if prefer == "other":
                    merged._by_id[p.id] = p
            else:
                merged.add(p)
        return merged


def trail_health_report(catalog: TrailCatalog) -> dict[str, Any]:
    """Quick dashboard numbers."""
    trails = catalog.all()
    overdue = catalog.find_overdue()
    return {
        "total": len(trails),
        "archived": catalog.count() - len(trails),
        "by_health": catalog.count_by_health(),
        "overdue_count": len(overdue),
        "overdue_names": [p.display_name for p in overdue[:10]],
    }


def apply_terrain_defaults(trail: Trail, terrain: Any) -> Trail:
    """Copy terrain visit/light hints onto a trail if unset."""
    from hikelog.terrain import TerrainProfile

    if not isinstance(terrain, TerrainProfile):
        return trail
    if trail.visit_interval_days == 7:
        trail.visit_interval_days = terrain.visit_interval_days
    if trail.light_override is None:
        trail.light_override = terrain.difficulty
    if trail.conditions_override is None:
        trail.conditions_override = (terrain.elevation_min_m + terrain.elevation_max_m) / 2
    trail.terrain_key = terrain.key
    trail.touch()
    return trail


def sort_by_visit_priority(trails: list[Trail], today: date | None = None) -> list[Trail]:
    ref = today or date.today()

    def key(p: Trail) -> tuple[int, str]:
        overdue = p.overdue_by_days(ref)
        health_rank = {
            TrailStatus.CRITICAL: 0,
            TrailStatus.STRUGGLING: 1,
            TrailStatus.UNKNOWN: 2,
            TrailStatus.OKAY: 3,
            TrailStatus.THRIVING: 4,
        }.get(p.health, 2)
        return (-overdue, health_rank, p.name.lower())

    return sorted(trails, key=key)


def clone_trail(trail: Trail, new_name: str | None = None) -> Trail:
    """Duplicate trail for propagation tracking."""
    data = trail.to_dict()
    data["id"] = uuid.uuid4().hex[:12]
    data["name"] = new_name or ("%s (propagation)" % trail.name)
    data["nickname"] = None
    data["last_visited_at"] = None
    data["note_ids"] = []
    data["tag_ids"] = list(trail.tag_ids)
    data["metadata"] = dict(trail.metadata)
    data["metadata"]["propagated_from"] = trail.id
    return Trail.from_dict(data)


def bulk_update_interval(catalog: TrailCatalog, trail_ids: list[str], days: int) -> int:
    updated = 0
    for pid in trail_ids:
        p = catalog.get(pid)
        if p:
            p.visit_interval_days = validate_interval_days(days)
            p.touch()
            updated += 1
    return updated


def catalog_to_summary_lines(catalog: TrailCatalog) -> list[str]:
    lines = []
    for p in catalog.all():
        status = "OVERDUE" if p.is_overdue() else "ok"
        lines.append(
            "{name} [{health}] interval={days}d last={last} ({status})".format(
                name=p.display_name,
                health=p.health.value,
                days=p.visit_interval_days,
                last=(p.last_visited_at or "never")[:10],
                status=status,
            )
        )
    return lines


def find_duplicates_by_name(catalog: TrailCatalog) -> dict[str, list[Trail]]:
    buckets: dict[str, list[Trail]] = {}
    for p in catalog.all(include_archived=True):
        key = p.name.lower()
        buckets.setdefault(key, []).append(p)
    return {k: v for k, v in buckets.items() if len(v) > 1}




def parse_iso(dt_str: str | None) -> datetime | None:
    """Parse ISO timestamps from logbook.json (used by reminders/stats)."""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None

