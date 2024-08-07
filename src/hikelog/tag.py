"""Tag model for organizing trails."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any
import uuid

from hikelog.validators import (
    validate_tag_name,
    validate_id,
    validate_color_hex,
    validate_slug,
    validate_metadata,
)


@dataclass
class Tag:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    slug: str = ""
    color: str | None = None
    description: str = ""
    trail_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self) -> None:
        self.name = validate_tag_name(self.name)
        self.id = validate_id(self.id)
        if not self.slug:
            self.slug = self.name.lower().replace(" ", "-")
        self.slug = validate_slug(self.slug)
        self.color = validate_color_hex(self.color)
        self.metadata = validate_metadata(self.metadata)

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Tag":
        tid = kwargs.pop("id", None) or uuid.uuid4().hex[:8]
        return cls(name=name, id=tid, **kwargs)

    def touch_count(self, n: int) -> None:
        self.trail_count = max(0, int(n))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tag":
        return cls(
            name=data["name"],
            id=data.get("id", uuid.uuid4().hex[:8]),
            slug=data.get("slug", ""),
            color=data.get("color"),
            description=data.get("description", ""),
            trail_count=int(data.get("trail_count", 0)),
            metadata=dict(data.get("metadata") or {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
        )

    def display(self) -> str:
        if self.color:
            return "%s (%s)" % (self.name, self.color)
        return self.name


# preset palette — copied from my notes app, works fine here
_PRESET_COLORS = [
    "#4caf50",
    "#2196f3",
    "#ff9800",
    "#9c27b0",
    "#795548",
    "#607d8b",
    "#e91e63",
]


class TagRegistry:
    """CRUD + lookup for tags."""

    def __init__(self) -> None:
        self._tags: dict[str, Tag] = {}
        self._by_slug: dict[str, str] = {}
        self._by_name: dict[str, str] = {}

    def add(self, tag: Tag) -> Tag:
        if tag.id in self._tags:
            raise ValueError("duplicate tag id")
        if tag.slug in self._by_slug:
            from hikelog.errors import ConflictError
            raise ConflictError("tag slug already exists: %s" % tag.slug, key=tag.slug)
        self._tags[tag.id] = tag
        self._by_slug[tag.slug] = tag.id
        self._by_name[tag.name.lower()] = tag.id
        return tag

    def get(self, tag_id: str) -> Tag | None:
        return self._tags.get(tag_id)

    def get_by_slug(self, slug: str) -> Tag | None:
        tid = self._by_slug.get(validate_slug(slug))
        return self._tags.get(tid) if tid else None

    def get_by_name(self, name: str) -> Tag | None:
        tid = self._by_name.get(name.lower())
        return self._tags.get(tid) if tid else None

    def require(self, tag_id: str) -> Tag:
        t = self.get(tag_id)
        if t is None:
            from hikelog.errors import NotFoundError
            raise NotFoundError("tag", tag_id)
        return t

    def find_or_create(self, name: str, **kwargs: Any) -> Tag:
        existing = self.get_by_name(name)
        if existing:
            return existing
        color = kwargs.pop("color", None)
        if color is None:
            color = _PRESET_COLORS[len(self._tags) % len(_PRESET_COLORS)]
        tag = Tag.create(name, color=color, **kwargs)
        return self.add(tag)

    def all(self) -> list[Tag]:
        return sorted(self._tags.values(), key=lambda t: t.name.lower())

    def remove(self, tag_id: str) -> bool:
        tag = self._tags.pop(tag_id, None)
        if tag is None:
            return False
        self._by_slug.pop(tag.slug, None)
        self._by_name.pop(tag.name.lower(), None)
        return True

    def search(self, query: str) -> list[Tag]:
        q = query.strip().lower()
        if not q:
            return self.all()
        return [
            t for t in self.all()
            if q in t.name.lower() or q in t.slug or q in t.description.lower()
        ]

    def load_many(self, tags: list[Tag]) -> None:
        for t in tags:
            self.add(t)

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.all()]

    @classmethod
    def from_dict_list(cls, rows: list[dict[str, Any]]) -> "TagRegistry":
        reg = cls()
        for row in rows:
            reg.add(Tag.from_dict(row))
        return reg

    def count(self) -> int:
        return len(self._tags)

    def recalculate_counts(self, trail_tag_map: dict[str, list[str]]) -> None:
        tallies: dict[str, int] = {}
        for tag_ids in trail_tag_map.values():
            for tid in tag_ids:
                tallies[tid] = tallies.get(tid, 0) + 1
        for tag in self._tags.values():
            tag.touch_count(tallies.get(tag.id, 0))

    def default_tags(self) -> "TagRegistry":
        """Built-in tags I always end up creating anyway."""
        presets = [
            ("beginner", "#4caf50", "easy care"),
            ("pet-safe", "#2196f3", "non-toxic to pets"),
            ("fussy", "#ff9800", "needs attention"),
            ("propagation", "#9c27b0", "parent for cuttings"),
            ("wishlist", "#607d8b", "don't own yet — TODO remove when acquired"),
        ]
        for name, color, desc in presets:
            try:
                self.add(Tag.create(name, color=color, description=desc))
            except Exception:
                pass
        return self

    def merge(self, other: "TagRegistry") -> "TagRegistry":
        merged = TagRegistry()
        for t in self.all():
            merged.add(t)
        for t in other.all():
            if t.slug not in merged._by_slug:
                merged.add(t)
        return merged

    def ids_for_names(self, names: list[str]) -> list[str]:
        out: list[str] = []
        for n in names:
            t = self.find_or_create(n)
            out.append(t.id)
        return out

    def tag_cloud(self) -> list[tuple[str, int]]:
        """Return (name, trail_count) sorted by popularity."""
        return sorted(
            [(t.name, t.trail_count) for t in self.all()],
            key=lambda x: (-x[1], x[0]),
        )


@dataclass
class TagGroup:
    """Logical grouping of tags — e.g. 'care level' tags."""

    name: str
    tag_ids: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TagGroup":
        return cls(
            name=data["name"],
            tag_ids=list(data.get("tag_ids") or []),
            id=data.get("id", uuid.uuid4().hex[:8]),
        )


class TagGroupRegistry:
    def __init__(self) -> None:
        self._groups: dict[str, TagGroup] = {}

    def add(self, group: TagGroup) -> TagGroup:
        self._groups[group.id] = group
        return group

    def get(self, group_id: str) -> TagGroup | None:
        return self._groups.get(group_id)

    def all(self) -> list[TagGroup]:
        return list(self._groups.values())

    def tags_in_group(self, group_id: str, registry: TagRegistry) -> list[Tag]:
        grp = self.get(group_id)
        if grp is None:
            return []
        return [registry.require(tid) for tid in grp.tag_ids if registry.get(tid)]

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [g.to_dict() for g in self.all()]

    @classmethod
    def from_dict_list(cls, rows: list[dict[str, Any]]) -> "TagGroupRegistry":
        reg = cls()
        for row in rows:
            reg.add(TagGroup.from_dict(row))
        return reg


def filter_trails_by_tag_names(
    registry: TagRegistry,
    trails: list[Any],
    names: list[str],
    match_all: bool = False,
) -> list[Any]:
    """Filter trail objects that have tag_ids matching given names."""
    tag_ids = set(registry.ids_for_names(names))
    out = []
    for p in trails:
        ptags = set(getattr(p, "tag_ids", []) or [])
        if match_all:
            if tag_ids.issubset(ptags):
                out.append(p)
        else:
            if ptags & tag_ids:
                out.append(p)
    return out


def rename_tag(registry: TagRegistry, tag_id: str, new_name: str) -> Tag:
    tag = registry.require(tag_id)
    old_name = tag.name.lower()
    tag.name = validate_tag_name(new_name)
    tag.slug = validate_slug(tag.name.replace(" ", "-"))
    registry._by_name.pop(old_name, None)
    registry._by_name[tag.name.lower()] = tag.id
    registry._by_slug[tag.slug] = tag.id
    return tag


def unused_tags(registry: TagRegistry, trail_tag_map: dict[str, list[str]]) -> list[Tag]:
    used: set[str] = set()
    for tids in trail_tag_map.values():
        used.update(tids)
    return [t for t in registry.all() if t.id not in used]


def export_tags_csv(registry: TagRegistry) -> list[list[str]]:
    rows = [["id", "name", "slug", "color", "trail_count", "description"]]
    for t in registry.all():
        rows.append([
            t.id, t.name, t.slug, t.color or "", str(t.trail_count), t.description,
        ])
    return rows


def tag_stats(registry: TagRegistry) -> dict[str, Any]:
    tags = registry.all()
    if not tags:
        return {"count": 0}
    counts = [t.trail_count for t in tags]
    return {
        "count": len(tags),
        "total_assignments": sum(counts),
        "avg_per_tag": sum(counts) / len(counts),
        "most_used": max(tags, key=lambda t: t.trail_count).name,
    }


def apply_tags_to_trail(trail: Any, registry: TagRegistry, names: list[str]) -> list[str]:
    """Return tag ids attached."""
    ids = registry.ids_for_names(names)
    for tid in ids:
        trail.attach_tag(tid)
    return ids

