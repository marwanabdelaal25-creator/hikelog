"""Notes attached to trails — observations, hazard logs, vibes."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any
import uuid

from hikelog.validators import (
    validate_id,
    validate_note_body,
    validate_metadata,
    require_non_empty,
)


class NoteKind(str, Enum):
    GENERAL = "general"
    OBSERVATION = "observation"
    PEST = "hazard"
    HEALTH = "health"
    PURCHASE = "purchase"
    REMINDER = "reminder"

    def __str__(self) -> str:
        return self.value


@dataclass
class Note:
    trail_id: str
    body: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:14])
    title: str = ""
    kind: NoteKind = NoteKind.GENERAL
    pinned: bool = False
    occurred_at: str = field(default_factory=lambda: date.today().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self) -> None:
        self.trail_id = validate_id(self.trail_id, "trail_id")
        self.id = validate_id(self.id)
        self.body = validate_note_body(self.body)
        if self.title:
            self.title = require_non_empty(self.title, "title")[:120]
        if isinstance(self.kind, str):
            self.kind = NoteKind(self.kind)
        self.metadata = validate_metadata(self.metadata)

    @classmethod
    def create(cls, trail_id: str, body: str, **kwargs: Any) -> "Note":
        nid = kwargs.pop("id", None) or uuid.uuid4().hex[:14]
        return cls(trail_id=trail_id, body=body, id=nid, **kwargs)

    @classmethod
    def observation(cls, trail_id: str, body: str, **kwargs: Any) -> "Note":
        return cls.create(trail_id, body, kind=NoteKind.OBSERVATION, **kwargs)

    @classmethod
    def hazard(cls, trail_id: str, body: str, **kwargs: Any) -> "Note":
        return cls.create(trail_id, body, kind=NoteKind.PEST, **kwargs)

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat()

    def edit(self, body: str | None = None, title: str | None = None) -> None:
        if body is not None:
            self.body = validate_note_body(body)
        if title is not None:
            self.title = require_non_empty(title, "title")[:120]
        self.touch()

    def pin(self) -> None:
        self.pinned = True
        self.touch()

    def unpin(self) -> None:
        self.pinned = False
        self.touch()

    @property
    def occurred_date(self) -> date:
        return date.fromisoformat(self.occurred_at[:10])

    def preview(self, max_len: int = 80) -> str:
        text = self.body.replace("\n", " ").strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Note":
        return cls(
            trail_id=data["trail_id"],
            body=data["body"],
            id=data.get("id", uuid.uuid4().hex[:14]),
            title=data.get("title", ""),
            kind=NoteKind(data.get("kind", "general")),
            pinned=bool(data.get("pinned", False)),
            occurred_at=data.get("occurred_at", date.today().isoformat()),
            metadata=dict(data.get("metadata") or {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
        )

    def headline(self) -> str:
        if self.title:
            return self.title
        return self.preview(60)


class NotesCollection:
    """Store and query notes per trail."""

    def __init__(self) -> None:
        self._notes: dict[str, Note] = {}
        self._by_trail: dict[str, list[str]] = {}

    def add(self, note: Note) -> Note:
        if note.id in self._notes:
            raise ValueError("duplicate note id")
        self._notes[note.id] = note
        self._by_trail.setdefault(note.trail_id, []).append(note.id)
        return note

    def create(self, trail_id: str, body: str, **kwargs: Any) -> Note:
        return self.add(Note.create(trail_id, body, **kwargs))

    def get(self, note_id: str) -> Note | None:
        return self._notes.get(note_id)

    def require(self, note_id: str) -> Note:
        n = self.get(note_id)
        if n is None:
            from hikelog.errors import NotFoundError
            raise NotFoundError("note", note_id)
        return n

    def for_trail(self, trail_id: str) -> list[Note]:
        ids = self._by_trail.get(trail_id, [])
        notes = [self._notes[i] for i in ids if i in self._notes]
        notes.sort(key=lambda n: (not n.pinned, n.occurred_at), reverse=True)
        return notes

    def pinned_for_trail(self, trail_id: str) -> list[Note]:
        return [n for n in self.for_trail(trail_id) if n.pinned]

    def of_kind(self, kind: NoteKind) -> list[Note]:
        return [n for n in self._notes.values() if n.kind == kind]

    def search(self, query: str, trail_id: str | None = None) -> list[Note]:
        q = query.strip().lower()
        pool = self.for_trail(trail_id) if trail_id else list(self._notes.values())
        if not q:
            return sorted(pool, key=lambda n: n.occurred_at, reverse=True)
        hits = []
        for n in pool:
            blob = " ".join([n.title, n.body, n.kind.value]).lower()
            if q in blob:
                hits.append(n)
        return sorted(hits, key=lambda n: n.occurred_at, reverse=True)

    def all(self) -> list[Note]:
        return sorted(self._notes.values(), key=lambda n: n.occurred_at, reverse=True)

    def remove(self, note_id: str) -> bool:
        note = self._notes.pop(note_id, None)
        if note is None:
            return False
        ids = self._by_trail.get(note.trail_id, [])
        if note_id in ids:
            ids.remove(note_id)
        return True

    def remove_for_trail(self, trail_id: str) -> int:
        ids = list(self._by_trail.pop(trail_id, []))
        for nid in ids:
            self._notes.pop(nid, None)
        return len(ids)

    def count(self) -> int:
        return len(self._notes)

    def count_for_trail(self, trail_id: str) -> int:
        return len(self._by_trail.get(trail_id, []))

    def recent(self, limit: int = 10) -> list[Note]:
        return self.all()[:limit]

    def hazard_notes(self) -> list[Note]:
        return self.of_kind(NoteKind.PEST)

    def load_many(self, notes: list[Note]) -> None:
        for n in notes:
            self.add(n)

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [n.to_dict() for n in self.all()]

    @classmethod
    def from_dict_list(cls, rows: list[dict[str, Any]]) -> "NotesCollection":
        coll = cls()
        for row in rows:
            coll.add(Note.from_dict(row))
        return coll

    def export_markdown(self, trail_id: str, trail_name: str = "") -> str:
        """Quick markdown dump for sharing — nothing fancy."""
        lines = ["# Notes for %s\n" % (trail_name or trail_id)]
        for n in self.for_trail(trail_id):
            lines.append("## %s (%s)" % (n.headline(), n.occurred_at[:10]))
            lines.append(n.body)
            lines.append("")
        return "\n".join(lines)

    def merge(self, other: "NotesCollection") -> "NotesCollection":
        merged = NotesCollection()
        for n in self.all():
            merged.add(n)
        for n in other.all():
            if n.id not in merged._notes:
                merged.add(n)
        return merged

    def attach_to_trail_ids(self) -> dict[str, list[str]]:
        """Return trail_id -> note_id list for syncing trail.note_ids."""
        out: dict[str, list[str]] = {}
        for pid, ids in self._by_trail.items():
            out[pid] = list(ids)
        return out


_NOTE_TEMPLATES: dict[str, str] = {
    "new_leaf": "New leaf unfurling on {date}.",
    "yellow_leaf": "Yellowing leaf on lower stem — watching for overwater.",
    "hazard_spackted": "Possible hazards spackted: {details}. Isolated from neighbors.",
    "repackted": "Repackted today into {pack_size}. Used {soil}.",
    "fertilized": "Fed with {product} at {strength}.",
}


def render_note_template(template_key: str, **ctx: Any) -> str:
    tpl = _NOTE_TEMPLATES.get(template_key)
    if tpl is None:
        raise ValueError("unknown template: %s" % template_key)
    ctx.setdefault("date", date.today().isoformat())
    try:
        return tpl.format(**ctx)
    except KeyError as exc:
        return tpl + " (missing: %s)" % exc.args[0]


def create_from_template(
    coll: NotesCollection,
    trail_id: str,
    template_key: str,
    kind: NoteKind = NoteKind.OBSERVATION,
    **ctx: Any,
) -> Note:
    body = render_note_template(template_key, **ctx)
    return coll.create(trail_id, body, kind=kind)


def notes_timeline(coll: NotesCollection, trail_id: str) -> list[dict[str, Any]]:
    """Flatten notes into timeline dicts for UI rendering."""
    items = []
    for n in coll.for_trail(trail_id):
        items.append({
            "id": n.id,
            "date": n.occurred_at[:10],
            "kind": n.kind.value,
            "headline": n.headline(),
            "pinned": n.pinned,
            "preview": n.preview(120),
        })
    return items


def count_by_kind(coll: NotesCollection) -> dict[str, int]:
    tallies: dict[str, int] = {}
    for n in coll.all():
        k = n.kind.value
        tallies[k] = tallies.get(k, 0) + 1
    return tallies


def find_open_hazard_issues(coll: NotesCollection) -> list[Note]:
    """Hazard notes from the last 30 days — FIXME: need resolved flag."""
    cutoff = date.today().toordinal() - 30
    issues = []
    for n in coll.hazard_notes():
        if n.occurred_date.toordinal() >= cutoff:
            issues.append(n)
    return issues


def bulk_pin(coll: NotesCollection, note_ids: list[str]) -> int:
    n = 0
    for nid in note_ids:
        note = coll.get(nid)
        if note:
            note.pin()
            n += 1
    return n


def notes_report(coll: NotesCollection) -> dict[str, Any]:
    return {
        "total": coll.count(),
        "by_kind": count_by_kind(coll),
        "open_hazard_issues": len(find_open_hazard_issues(coll)),
        "trails_with_notes": len(coll._by_trail),
    }


class NotesIndexer:
    """Build inverted index for full-text search across notes."""

    def __init__(self, coll: NotesCollection) -> None:
        self._coll = coll
        self._index: dict[str, set[str]] = {}
        self.rebuild()

    def rebuild(self) -> None:
        self._index.clear()
        for note in self._coll.all():
            tokens = set(note.body.lower().split())
            tokens.update(note.title.lower().split())
            for tok in tokens:
                if len(tok) < 2:
                    continue
                self._index.setdefault(tok, set()).add(note.id)

    def search_tokens(self, query: str) -> list[Note]:
        tokens = [t for t in query.lower().split() if t]
        if not tokens:
            return []
        sets = [self._index.get(t, set()) for t in tokens]
        if not sets:
            return []
        ids = set.intersection(*sets) if len(sets) > 1 else sets[0]
        return [self._coll.require(nid) for nid in ids if self._coll.get(nid)]

    def related_notes(self, note_id: str, limit: int = 5) -> list[Note]:
        note = self._coll.get(note_id)
        if note is None:
            return []
        tokens = [t for t in note.body.lower().split() if len(t) > 3][:10]
        hits: dict[str, int] = {}
        for tok in tokens:
            for nid in self._index.get(tok, set()):
                if nid != note_id:
                    hits[nid] = hits.get(nid, 0) + 1
        ranked = sorted(hits.items(), key=lambda x: -x[1])
        out: list[Note] = []
        for nid, _ in ranked[:limit]:
            n = self._coll.get(nid)
            if n:
                out.append(n)
        return out


def migrate_note_kind_legacy(kind: str) -> NoteKind:
    """Map old export values to current enum."""
    aliases = {
        "obs": NoteKind.OBSERVATION,
        "bug": NoteKind.PEST,
        "health_check": NoteKind.HEALTH,
        "buy": NoteKind.PURCHASE,
    }
    if kind in aliases:
        return aliases[kind]
    try:
        return NoteKind(kind)
    except ValueError:
        return NoteKind.GENERAL


def notes_for_week(coll: NotesCollection, start: date | None = None) -> list[Note]:
    ref = start or date.today()
    end = ref + timedelta(days=7)
    return [n for n in coll.all() if ref <= n.occurred_date <= end]

