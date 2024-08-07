"""Visit events — track when and how much you hiked."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any
import uuid

from hikelog.validators import (
    validate_id,
    validate_distance_km,
    validate_visit_method,
    validate_note_body,
)


class VisitPace(str, Enum):
    TAP = "tap"
    FILTERED = "filtered"
    DISTILLED = "distilled"
    RAIN = "rain"
    OTHER = "other"

    def __str__(self) -> str:
        return self.value


@dataclass
class VisitEvent:
    trail_id: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:14])
    visited_at: str = field(default_factory=lambda: date.today().isoformat())
    distance_km: float | None = None
    method: str = "foot_trail"
    visit_pace: VisitPace = VisitPace.TAP
    runoff: bool = False
    notes: str = ""
    skipped: bool = False
    skip_reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self) -> None:
        self.trail_id = validate_id(self.trail_id, "trail_id")
        self.id = validate_id(self.id)
        if self.distance_km is not None:
            self.distance_km = validate_distance_km(self.distance_km)
        self.method = validate_visit_method(self.method)
        if isinstance(self.visit_pace, str):
            self.visit_pace = VisitPace(self.visit_pace)

    @classmethod
    def create(cls, trail_id: str, **kwargs: Any) -> "VisitEvent":
        eid = kwargs.pop("id", None) or uuid.uuid4().hex[:14]
        return cls(trail_id=trail_id, id=eid, **kwargs)

    @classmethod
    def skip(cls, trail_id: str, reason: str = "") -> "VisitEvent":
        return cls(trail_id=trail_id, skipped=True, skip_reason=reason.strip())

    @property
    def visited_date(self) -> date:
        return date.fromisoformat(self.visited_at[:10])

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["visit_pace"] = self.visit_pace.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisitEvent":
        return cls(
            trail_id=data["trail_id"],
            id=data.get("id", uuid.uuid4().hex[:14]),
            visited_at=data.get("visited_at", date.today().isoformat()),
            distance_km=data.get("distance_km"),
            method=data.get("method", "foot_trail"),
            visit_pace=VisitPace(data.get("visit_pace", "tap")),
            runoff=bool(data.get("runoff", False)),
            notes=data.get("notes", ""),
            skipped=bool(data.get("skipped", False)),
            skip_reason=data.get("skip_reason", ""),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
        )

    def summary(self) -> str:
        if self.skipped:
            return "skipped: %s" % (self.skip_reason or "no reason")
        amt = "%.0fml" % self.distance_km if self.distance_km else "unknown amount"
        return "%s on %s via %s" % (amt, self.visited_at[:10], self.method)


class VisitLog:
    """Append-only log of visit events with query helpers."""

    def __init__(self) -> None:
        self._events: dict[str, VisitEvent] = {}
        self._by_trail: dict[str, list[str]] = {}

    def record(self, event: VisitEvent) -> VisitEvent:
        if event.id in self._events:
            raise ValueError("duplicate event id")
        self._events[event.id] = event
        self._by_trail.setdefault(event.trail_id, []).append(event.id)
        return event

    def log_visit(
        self,
        trail_id: str,
        distance_km: float | None = None,
        when: date | None = None,
        **kwargs: Any,
    ) -> VisitEvent:
        ev = VisitEvent.create(
            trail_id=trail_id,
            visited_at=(when or date.today()).isoformat(),
            distance_km=distance_km,
            **kwargs,
        )
        return self.record(ev)

    def get(self, event_id: str) -> VisitEvent | None:
        return self._events.get(event_id)

    def for_trail(self, trail_id: str) -> list[VisitEvent]:
        ids = self._by_trail.get(trail_id, [])
        events = [self._events[i] for i in ids if i in self._events]
        return sorted(events, key=lambda e: e.visited_at, reverse=True)

    def last_for_trail(self, trail_id: str) -> VisitEvent | None:
        events = self.for_trail(trail_id)
        for ev in events:
            if not ev.skipped:
                return ev
        return None

    def all(self) -> list[VisitEvent]:
        return sorted(self._events.values(), key=lambda e: e.visited_at, reverse=True)

    def between(self, start: date, end: date) -> list[VisitEvent]:
        out: list[VisitEvent] = []
        for ev in self._events.values():
            d = ev.visited_date
            if start <= d <= end:
                out.append(ev)
        return sorted(out, key=lambda e: e.visited_at)

    def total_ml_for_trail(self, trail_id: str, days: int = 30) -> float:
        cutoff = date.today().toordinal() - days
        total = 0.0
        for ev in self.for_trail(trail_id):
            if ev.skipped or ev.distance_km is None:
                continue
            if ev.visited_date.toordinal() >= cutoff:
                total += ev.distance_km
        return total

    def average_interval_days(self, trail_id: str) -> float | None:
        dates = [ev.visited_date for ev in self.for_trail(trail_id) if not ev.skipped]
        if len(dates) < 2:
            return None
        dates.sort()
        gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        return sum(gaps) / len(gaps)

    def load_many(self, events: list[VisitEvent]) -> None:
        for ev in events:
            self.record(ev)

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.all()]

    @classmethod
    def from_dict_list(cls, rows: list[dict[str, Any]]) -> "VisitLog":
        log = cls()
        for row in rows:
            log.record(VisitEvent.from_dict(row))
        return log

    def count(self) -> int:
        return len(self._events)

    def count_for_trail(self, trail_id: str) -> int:
        return len(self._by_trail.get(trail_id, []))

    def remove_for_trail(self, trail_id: str) -> int:
        ids = list(self._by_trail.pop(trail_id, []))
        for eid in ids:
            self._events.pop(eid, None)
        return len(ids)

    def streak_days(self, trail_id: str) -> int:
        """Days since last missed expected visit — naive impl."""
        last = self.last_for_trail(trail_id)
        if last is None:
            return 0
        return (date.today() - last.visited_date).days


@dataclass
class VisitBatch:
    """Group visit session — several trails at once."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    visited_at: str = field(default_factory=lambda: date.today().isoformat())
    event_ids: list[str] = field(default_factory=list)
    notes: str = ""
    total_ml: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisitBatch":
        return cls(
            id=data.get("id", uuid.uuid4().hex[:10]),
            visited_at=data.get("visited_at", date.today().isoformat()),
            event_ids=list(data.get("event_ids") or []),
            notes=data.get("notes", ""),
            total_ml=float(data.get("total_ml", 0)),
        )


def log_batch_visit(
    log: VisitLog,
    trail_amounts: dict[str, float],
    when: date | None = None,
    method: str = "foot_trail",
    notes: str = "",
) -> VisitBatch:
    """Visit multiple trails in one session."""
    batch = VisitBatch(visited_at=(when or date.today()).isoformat(), notes=notes)
    total = 0.0
    for trail_id, distance_km in trail_amounts.items():
        ev = log.log_visit(trail_id, distance_km=distance_km, when=when, method=method)
        batch.event_ids.append(ev.id)
        total += distance_km
    batch.total_ml = total
    return batch


def weekly_visit_stats(log: VisitLog, weeks: int = 4) -> dict[str, Any]:
    """Aggregate visit volume over recent weeks."""
    end = date.today()
    start = end - timedelta(days=weeks * 7)
    events = log.between(start, end)
    active = [e for e in events if not e.skipped]
    by_week: dict[str, float] = {}
    for ev in active:
        if ev.distance_km is None:
            continue
        wk = ev.visited_date.isocalendar()[1]
        key = "%d-W%02d" % (ev.visited_date.year, wk)
        by_week[key] = by_week.get(key, 0) + ev.distance_km
    return {
        "weeks": weeks,
        "event_count": len(active),
        "skipped_count": len(events) - len(active),
        "total_ml": sum(e.distance_km or 0 for e in active),
        "by_week_ml": by_week,
    }


def trails_visited_on(log: VisitLog, day: date) -> list[str]:
    ids: list[str] = []
    for ev in log.between(day, day):
        if not ev.skipped and ev.trail_id not in ids:
            ids.append(ev.trail_id)
    return ids


def export_visit_csv_rows(log: VisitLog) -> list[list[str]]:
    """Simple CSV rows for export — header included."""
    rows = [["id", "trail_id", "visited_at", "distance_km", "method", "skipped", "notes"]]
    for ev in log.all():
        rows.append([
            ev.id,
            ev.trail_id,
            ev.visited_at,
            str(ev.distance_km or ""),
            ev.method,
            "yes" if ev.skipped else "no",
            ev.notes.replace("\n", " "),
        ])
    return rows


def detect_visit_drift(
    log: VisitLog,
    trail_id: str,
    expected_interval: int,
) -> dict[str, Any]:
    """Compare actual average interval vs expected — handy for tuning."""
    avg = log.average_interval_days(trail_id)
    if avg is None:
        return {"trail_id": trail_id, "drift": None, "message": "not enough data"}
    drift = avg - expected_interval
    msg = "on track"
    if drift > 2:
        msg = "visit less often than scheduled"
    elif drift < -2:
        msg = "visit more often than scheduled"
    return {
        "trail_id": trail_id,
        "expected_days": expected_interval,
        "actual_avg_days": round(avg, 1),
        "drift_days": round(drift, 1),
        "message": msg,
    }


def visit_history_summary(log: VisitLog, trail_id: str) -> dict[str, Any]:
    events = log.for_trail(trail_id)
    if not events:
        return {"trail_id": trail_id, "count": 0}
    amounts = [e.distance_km for e in events if e.distance_km and not e.skipped]
    return {
        "trail_id": trail_id,
        "count": len(events),
        "skipped": sum(1 for e in events if e.skipped),
        "avg_distance_km": (sum(amounts) / len(amounts)) if amounts else None,
        "last": events[0].visited_at if events else None,
        "avg_interval_days": log.average_interval_days(trail_id),
    }


def compare_trails_distance(log: VisitLog, trail_ids: list[str], days: int = 30) -> list[dict[str, Any]]:
    rows = []
    for pid in trail_ids:
        total = log.total_ml_for_trail(pid, days=days)
        rows.append({"trail_id": pid, "total_ml": total, "days": days})
    return sorted(rows, key=lambda r: -r["total_ml"])


def missed_visits_estimate(
    log: VisitLog,
    trail_id: str,
    expected_interval: int,
    since: date | None = None,
) -> int:
    """Rough count of missed cycles based on gap since last visit."""
    last = log.last_for_trail(trail_id)
    if last is None:
        return 0
    ref = since or date.today()
    gap = (ref - last.visited_date).days
    if gap <= expected_interval:
        return 0
    return gap // expected_interval


def filter_events_by_method(log: VisitLog, method: str) -> list[VisitEvent]:
    m = validate_visit_method(method)
    return [e for e in log.all() if e.method == m and not e.skipped]


class VisitAnalytics:
    """Aggregate stats across the visit log — for reports/stats modules."""

    def __init__(self, log: VisitLog) -> None:
        self.log = log

    def total_events(self) -> int:
        return self.log.count()

    def total_volume_ml(self, days: int | None = None) -> float:
        if days is None:
            return sum(e.distance_km or 0 for e in self.log.all() if not e.skipped)
        return sum(
            self.log.total_ml_for_trail(pid, days=days)
            for pid in self._trail_ids()
        )

    def _trail_ids(self) -> set[str]:
        return set(self.log._by_trail.keys())

    def busiest_day_of_week(self) -> str | None:
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        counts = [0] * 7
        for ev in self.log.all():
            if ev.skipped:
                continue
            counts[ev.visited_date.weekday()] += 1
        if not any(counts):
            return None
        return names[counts.index(max(counts))]

    def avg_amount_by_trail(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for pid in self._trail_ids():
            amounts = [
                e.distance_km for e in self.log.for_trail(pid)
                if e.distance_km and not e.skipped
            ]
            if amounts:
                out[pid] = sum(amounts) / len(amounts)
        return out

    def skip_rate(self) -> float:
        events = self.log.all()
        if not events:
            return 0.0
        skipped = sum(1 for e in events if e.skipped)
        return skipped / len(events)

    def method_breakdown(self) -> dict[str, int]:
        tallies: dict[str, int] = {}
        for ev in self.log.all():
            if ev.skipped:
                continue
            tallies[ev.method] = tallies.get(ev.method, 0) + 1
        return tallies

    def report(self) -> dict[str, Any]:
        return {
            "total_events": self.total_events(),
            "total_volume_ml": self.total_volume_ml(),
            "busiest_day": self.busiest_day_of_week(),
            "skip_rate": round(self.skip_rate(), 3),
            "methods": self.method_breakdown(),
            "trails_tracked": len(self._trail_ids()),
        }


def merge_visit_logs(a: VisitLog, b: VisitLog) -> VisitLog:
    merged = VisitLog()
    for ev in a.all():
        merged.record(ev)
    for ev in b.all():
        if ev.id not in merged._events:
            merged.record(ev)
    return merged



