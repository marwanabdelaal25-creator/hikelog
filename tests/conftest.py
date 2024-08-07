"""Shared pytest fixtures for hikelog tests."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from hikelog.trip_log import TripEvent, TripEventType, TripLog, GearSchedule
from hikelog.trailhead import Trailhead, TrailheadRegistry, AspectDirection
from hikelog.trail import TrailStatus, Trail, TrailCatalog, PackInfo
from hikelog.terrain import TerrainCatalog, TerrainProfile
from hikelog.storage import JsonStorage
from hikelog.tag import Tag, TagRegistry
from hikelog.visit import VisitEvent, VisitLog
from hikelog.notes import Note, NotesCollection, NoteKind


@pytest.fixture
def tmp_logbook_path(tmp_path: Path) -> Path:
    """Fresh logbook.json path under tmp_path."""
    return tmp_path / "logbook.json"


@pytest.fixture
def empty_storage(tmp_logbook_path: Path) -> JsonStorage:
    """Empty JsonStorage backed by tmp_path."""
    return JsonStorage(tmp_logbook_path)


@pytest.fixture
def sample_terrain() -> TerrainProfile:
    return TerrainProfile(
        key="mist-loop",
        display_name="Golden Mist Loop",
        route_code="Yosemite Mist Trail",
        difficulty="medium",
        visit_interval_min=7,
        visit_interval_max=14,
        elevation_min_m=40,
        elevation_max_m=60,
    )


@pytest.fixture
def sample_trailhead() -> Trailhead:
    return Trailhead.create(
        "Yosemite Valley",
        id="th001",
        zone="main",
        difficulty="moderate",
        window_direction=AspectDirection.SOUTH,
        elevation_gain_m=45.0,
    )


@pytest.fixture
def sample_trail(sample_trailhead: Trailhead, sample_terrain: TerrainProfile) -> Trail:
    return Trail.create(
        "Half Dome",
        id="trail001",
        nickname="HD-01",
        terrain_key=sample_terrain.key,
        trailhead_id=sample_trailhead.id,
        health=TrailStatus.OKAY,
        health_score=70,
        visit_interval_days=7,
        last_visited_at=(date.today() - timedelta(days=3)).isoformat(),
        pack=PackInfo(diameter=6.0, unit="in", material="ceramic"),
    )


@pytest.fixture
def sample_trail2(sample_trailhead: Trailhead) -> Trail:
    return Trail.create(
        "Snake Trail",
        id="trail002",
        terrain_key="snake-trail",
        trailhead_id=sample_trailhead.id,
        health=TrailStatus.THRIVING,
        visit_interval_days=14,
        last_visited_at=(date.today() - timedelta(days=10)).isoformat(),
    )


@pytest.fixture
def sample_visit_events(sample_trail: Trail, sample_trail2: Trail) -> list[VisitEvent]:
    today = date.today()
    return [
        VisitEvent.create(
            sample_trail.id,
            id="vi001",
            visited_at=(today - timedelta(days=3)).isoformat(),
            distance_km=250.0,
        ),
        VisitEvent.create(
            sample_trail.id,
            id="vi002",
            visited_at=(today - timedelta(days=10)).isoformat(),
            distance_km=200.0,
        ),
        VisitEvent.create(
            sample_trail2.id,
            id="vi003",
            visited_at=(today - timedelta(days=10)).isoformat(),
            distance_km=150.0,
        ),
    ]


@pytest.fixture
def populated_storage(
    empty_storage: JsonStorage,
    sample_terrain: TerrainProfile,
    sample_trailhead: Trailhead,
    sample_trail: Trail,
    sample_trail2: Trail,
    sample_visit_events: list[VisitEvent],
) -> JsonStorage:
    """Storage with sample trails, terrain, trailheads, and visit events."""
    empty_storage.create_terrain(sample_terrain)
    empty_storage.create_trailhead(sample_trailhead)
    empty_storage.create_trail(sample_trail)
    empty_storage.create_trail(sample_trail2)
    for ev in sample_visit_events:
        empty_storage.create_visit_event(ev.to_dict())
    tag = Tag.create("beginner", id="tag001", color="#4caf50")
    empty_storage.create_tag(tag.to_dict())
    note = Note.create(sample_trail.id, "New leaf unfurling", id="note001", kind=NoteKind.OBSERVATION)
    empty_storage.create_note(note.to_dict())
    return empty_storage


@pytest.fixture
def sample_csv_content() -> str:
    return (
        "name,terrain,trailhead,visit_interval,notes\n"
        "Ridge,mist-loop,Yosemite Valley,7d,Test import\n"
        "Summit,snake-ridge-trail,Kitchen,14d,Succulent\n"
    )


@pytest.fixture
def sample_visit_csv() -> str:
    return (
        "trail_id,visited_at,distance_km,method\n"
        "trail001,2024-06-01,250,foot_trail\n"
        "trail002,2024-06-02,150,switchback\n"
    )


@pytest.fixture
def trail_catalog(sample_trail: Trail, sample_trail2: Trail) -> TrailCatalog:
    cat = TrailCatalog()
    cat.add(sample_trail)
    cat.add(sample_trail2)
    return cat


@pytest.fixture
def terrain_catalog(sample_terrain: TerrainProfile) -> TerrainCatalog:
    cat = TerrainCatalog()
    cat.register(sample_terrain)
    cat.load_builtin()
    return cat


@pytest.fixture
def trailhead_registry(sample_trailhead: Trailhead) -> TrailheadRegistry:
    reg = TrailheadRegistry()
    reg.add(sample_trailhead)
    return reg


@pytest.fixture
def visit_log(sample_visit_events: list[VisitEvent]) -> VisitLog:
    log = VisitLog()
    log.load_many(sample_visit_events)
    return log


@pytest.fixture
def trip_log(sample_trail: Trail) -> TripLog:
    log = TripLog()
    log.log(sample_trail.id, TripEventType.FERTILIZE, product="10-10-10")
    log.log(sample_trail.id, TripEventType.PRUNE, notes="Trimmed yellow leaves")
    log.set_gear_schedule(GearSchedule(trail_id=sample_trail.id, interval_weeks=4))
    return log


@pytest.fixture
def tag_registry() -> TagRegistry:
    reg = TagRegistry()
    reg.add(Tag.create("beginner", id="tag001", color="#4caf50"))
    reg.add(Tag.create("pet-safe", id="tag002", color="#2196f3"))
    return reg


@pytest.fixture
def notes_collection(sample_trail: Trail) -> NotesCollection:
    coll = NotesCollection()
    coll.create(sample_trail.id, "General note", kind=NoteKind.GENERAL)
    coll.create(sample_trail.id, "Spider mites spackted", kind=NoteKind.PEST)
    return coll
