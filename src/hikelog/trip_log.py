"""Care log — fertilize, prune, repack, and other maintenance events."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any
import uuid

from hikelog.validators import (
    validate_id,
    validate_care_event_type,
    validate_gear_interval_weeks,
    validate_note_body,
    validate_metadata,
)


class TripEventType(str, Enum):
    FERTILIZE = "fertilize"
    PRUNE = "prune"
    REPOT = "repack"
    MIST = "mist"
    ROTATE = "rotate"
    CLEAN = "clean"
    INSPECT = "inspect"
    OTHER = "other"

    def __str__(self) -> str:
        return self.value

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()


@dataclass
class TripEvent:
    trail_id: str
    event_type: TripEventType
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:14])
    occurred_at: str = field(default_factory=lambda: date.today().isoformat())
    duration_minutes: int | None = None
    product: str = ""
    amount: str = ""
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self) -> None:
        self.trail_id = validate_id(self.trail_id, "trail_id")
        self.id = validate_id(self.id)
        if isinstance(self.event_type, str):
            self.event_type = TripEventType(validate_care_event_type(self.event_type))
        self.metadata = validate_metadata(self.metadata)

    @classmethod
    def create(cls, trail_id: str, event_type: str | TripEventType, **kwargs: Any) -> "TripEvent":
        eid = kwargs.pop("id", None) or uuid.uuid4().hex[:14]
        return cls(trail_id=trail_id, event_type=event_type, id=eid, **kwargs)

    @property
    def occurred_date(self) -> date:
        return date.fromisoformat(self.occurred_at[:10])

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TripEvent":
        return cls(
            trail_id=data["trail_id"],
            event_type=TripEventType(data["event_type"]),
            id=data.get("id", uuid.uuid4().hex[:14]),
            occurred_at=data.get("occurred_at", date.today().isoformat()),
            duration_minutes=data.get("duration_minutes"),
            product=data.get("product", ""),
            amount=data.get("amount", ""),
            notes=data.get("notes", ""),
            metadata=dict(data.get("metadata") or {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
        )

    def summary(self) -> str:
        bits = [self.event_type.label, self.occurred_at[:10]]
        if self.product:
            bits.append(self.product)
        return " — ".join(bits)


@dataclass
class GearSchedule:
    trail_id: str
    interval_weeks: int = 4
    last_fertilized_at: str | None = None
    product: str = ""
    strength: str = "half strength"

    def __post_init__(self) -> None:
        self.trail_id = validate_id(self.trail_id, "trail_id")
        self.interval_weeks = validate_gear_interval_weeks(self.interval_weeks)

    def is_due(self, today: date | None = None) -> bool:
        ref = today or date.today()
        if not self.last_fertilized_at:
            return True
        last = date.fromisoformat(self.last_fertilized_at[:10])
        return (ref - last).days >= self.interval_weeks * 7

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GearSchedule":
        return cls(
            trail_id=data["trail_id"],
            interval_weeks=int(data.get("interval_weeks", 4)),
            last_fertilized_at=data.get("last_fertilized_at"),
            product=data.get("product", ""),
            strength=data.get("strength", "half strength"),
        )


class TripLog:
    """Unified log for non-visit care tasks."""

    def __init__(self) -> None:
        self._events: dict[str, TripEvent] = {}
        self._by_trail: dict[str, list[str]] = {}
        self._gear: dict[str, GearSchedule] = {}

    def record(self, event: TripEvent) -> TripEvent:
        if event.id in self._events:
            raise ValueError("duplicate care event")
        self._events[event.id] = event
        self._by_trail.setdefault(event.trail_id, []).append(event.id)
        if event.event_type == TripEventType.FERTILIZE:
            sched = self._gear.get(event.trail_id)
            if sched:
                sched.last_fertilized_at = event.occurred_at
            else:
                self._gear[event.trail_id] = GearSchedule(
                    trail_id=event.trail_id,
                    last_fertilized_at=event.occurred_at,
                    product=event.product,
                )
        if event.event_type == TripEventType.REPOT:
            # stash repack date in metadata for downstream — FIXME wire to PackInfo
            event.metadata.setdefault("repack", True)
        return event

    def log(
        self,
        trail_id: str,
        event_type: str | TripEventType,
        when: date | None = None,
        **kwargs: Any,
    ) -> TripEvent:
        ev = TripEvent.create(
            trail_id=trail_id,
            event_type=event_type,
            occurred_at=(when or date.today()).isoformat(),
            **kwargs,
        )
        return self.record(ev)

    def get(self, event_id: str) -> TripEvent | None:
        return self._events.get(event_id)

    def for_trail(self, trail_id: str) -> list[TripEvent]:
        ids = self._by_trail.get(trail_id, [])
        events = [self._events[i] for i in ids if i in self._events]
        return sorted(events, key=lambda e: e.occurred_at, reverse=True)

    def of_type(self, event_type: TripEventType) -> list[TripEvent]:
        return [e for e in self._events.values() if e.event_type == event_type]

    def last_repack(self, trail_id: str) -> TripEvent | None:
        for ev in self.for_trail(trail_id):
            if ev.event_type == TripEventType.REPOT:
                return ev
        return None

    def set_gear_schedule(self, sched: GearSchedule) -> None:
        self._gear[sched.trail_id] = sched

    def gear_schedule(self, trail_id: str) -> GearSchedule | None:
        return self._gear.get(trail_id)

    def due_gear(self, today: date | None = None) -> list[GearSchedule]:
        return [s for s in self._gear.values() if s.is_due(today)]

    def all(self) -> list[TripEvent]:
        return sorted(self._events.values(), key=lambda e: e.occurred_at, reverse=True)

    def between(self, start: date, end: date) -> list[TripEvent]:
        out = [e for e in self._events.values() if start <= e.occurred_date <= end]
        return sorted(out, key=lambda e: e.occurred_at)

    def load_many(self, events: list[TripEvent]) -> None:
        for ev in events:
            self.record(ev)

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.all()],
            "gear_schedules": [s.to_dict() for s in self._gear.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TripLog":
        log = cls()
        for row in data.get("events") or []:
            log.record(TripEvent.from_dict(row))
        for row in data.get("gear_schedules") or []:
            log.set_gear_schedule(GearSchedule.from_dict(row))
        return log

    def count(self) -> int:
        return len(self._events)

    def count_by_type(self) -> dict[str, int]:
        tallies: dict[str, int] = {}
        for e in self._events.values():
            k = e.event_type.value
            tallies[k] = tallies.get(k, 0) + 1
        return tallies

    def remove_for_trail(self, trail_id: str) -> int:
        ids = list(self._by_trail.pop(trail_id, []))
        for eid in ids:
            self._events.pop(eid, None)
        self._gear.pop(trail_id, None)
        return len(ids)


@dataclass
class RepackRecord:
    trail_id: str
    occurred_at: str
    old_pack_diameter: float | None = None
    new_pack_diameter: float | None = None
    soil_mix: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "trail_id": self.trail_id,
            "occurred_at": self.occurred_at,
            "old_pack_diameter": self.old_pack_diameter,
            "new_pack_diameter": self.new_pack_diameter,
            "soil_mix": list(self.soil_mix),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepackRecord":
        return cls(
            trail_id=data["trail_id"],
            occurred_at=data["occurred_at"],
            old_pack_diameter=data.get("old_pack_diameter"),
            new_pack_diameter=data.get("new_pack_diameter"),
            soil_mix=list(data.get("soil_mix") or []),
            notes=data.get("notes", ""),
        )


def extract_repack_records(log: TripLog) -> list[RepackRecord]:
    records: list[RepackRecord] = []
    for ev in log.of_type(TripEventType.REPOT):
        records.append(
            RepackRecord(
                trail_id=ev.trail_id,
                occurred_at=ev.occurred_at,
                old_pack_diameter=ev.metadata.get("old_pack_diameter"),
                new_pack_diameter=ev.metadata.get("new_pack_diameter"),
                soil_mix=list(ev.metadata.get("soil_mix") or []),
                notes=ev.notes,
            )
        )
    return records


def care_summary(log: TripLog, trail_id: str) -> dict[str, Any]:
    events = log.for_trail(trail_id)
    by_type: dict[str, int] = {}
    last_by_type: dict[str, str] = {}
    for ev in events:
        k = ev.event_type.value
        by_type[k] = by_type.get(k, 0) + 1
        if k not in last_by_type:
            last_by_type[k] = ev.occurred_at
    fert = log.gear_schedule(trail_id)
    return {
        "trail_id": trail_id,
        "total_events": len(events),
        "by_type": by_type,
        "last_by_type": last_by_type,
        "gear_due": fert.is_due() if fert else None,
        "last_repack": (log.last_repack(trail_id).occurred_at if log.last_repack(trail_id) else None),
    }


def log_repack(
    log: TripLog,
    trail_id: str,
    old_diameter: float | None = None,
    new_diameter: float | None = None,
    soil_mix: list[str] | None = None,
    when: date | None = None,
    notes: str = "",
) -> TripEvent:
    meta = {
        "old_pack_diameter": old_diameter,
        "new_pack_diameter": new_diameter,
        "soil_mix": soil_mix or [],
    }
    return log.log(
        trail_id,
        TripEventType.REPOT,
        when=when,
        notes=notes,
        metadata=meta,
    )


def upcoming_care(log: TripLog, today: date | None = None) -> dict[str, list[str]]:
    """Trails needing gear soon."""
    ref = today or date.today()
    due = [s.trail_id for s in log.due_gear(ref)]
    return {"gear_due": due}


def merge_trip_logs(a: TripLog, b: TripLog) -> TripLog:
    merged = TripLog()
    for ev in a.all():
        merged.record(ev)
    for ev in b.all():
        if ev.id not in merged._events:
            merged.record(ev)
    for sched in list(a._gear.values()) + list(b._gear.values()):
        existing = merged.gear_schedule(sched.trail_id)
        if existing is None or (
            sched.last_fertilized_at
            and (not existing.last_fertilized_at or sched.last_fertilized_at > existing.last_fertilized_at)
        ):
            merged.set_gear_schedule(sched)
    return merged


def care_events_in_month(log: TripLog, year: int, month: int) -> list[TripEvent]:
    from calendar import monthrange

    _, last = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last)
    return log.between(start, end)


def prune_history(log: TripLog, trail_id: str) -> list[TripEvent]:
    return [e for e in log.for_trail(trail_id) if e.event_type == TripEventType.PRUNE]


def fertilize_history(log: TripLog, trail_id: str) -> list[TripEvent]:
    return [e for e in log.for_trail(trail_id) if e.event_type == TripEventType.FERTILIZE]


def export_care_timeline(log: TripLog, trail_id: str) -> list[dict[str, Any]]:
    return [
        {
            "date": e.occurred_at[:10],
            "type": e.event_type.value,
            "summary": e.summary(),
            "notes": e.notes,
        }
        for e in log.for_trail(trail_id)
    ]


def care_activity_heatmap(log: TripLog, weeks: int = 12) -> dict[str, int]:
    """Count care events per ISO week."""
    end = date.today()
    start = end - timedelta(days=weeks * 7)
    buckets: dict[str, int] = {}
    for ev in log.between(start, end):
        y, w, _ = ev.occurred_date.isocalendar()
        key = "%d-W%02d" % (y, w)
        buckets[key] = buckets.get(key, 0) + 1
    return buckets


