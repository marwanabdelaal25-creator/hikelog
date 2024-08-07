"""Tests for hikelog.storage."""

import json

import pytest

from hikelog.errors import NotFoundError, StorageError, ValidationError
from hikelog.trailhead import Trailhead
from hikelog.trail import Trail, TrailStatus
from hikelog.terrain import TerrainProfile
from hikelog.storage import JsonStorage, DEFAULT_GARDEN, SCHEMA_VERSION


class TestJsonStorageInit:
    def test_creates_empty_logbook(self, tmp_logbook_path):
        storage = JsonStorage(tmp_logbook_path)
        assert tmp_logbook_path.exists()

    def test_loads_existing(self, populated_storage, tmp_logbook_path):
        storage2 = JsonStorage(tmp_logbook_path)
        assert len(storage2.list_trails()) >= 2


class TestTrails:
    def test_create_and_list(self, empty_storage, sample_trail):
        created = empty_storage.create_trail(sample_trail)
        assert created.name == sample_trail.name

    def test_get_trail(self, populated_storage, sample_trail):
        trail = populated_storage.get_trail(sample_trail.id)
        assert trail.id == sample_trail.id

    def test_get_trail_not_found(self, empty_storage):
        with pytest.raises(NotFoundError):
            empty_storage.get_trail("missing")

    def test_update_trail(self, populated_storage, sample_trail):
        updated = populated_storage.update_trail(sample_trail.id, {"nickname": "NewNick"})
        assert updated.nickname == "NewNick"

    def test_delete_trail(self, populated_storage, sample_trail):
        populated_storage.delete_trail(sample_trail.id)
        with pytest.raises(NotFoundError):
            populated_storage.get_trail(sample_trail.id)

    def test_list_trails_active_only(self, populated_storage, sample_trail):
        populated_storage.update_trail(sample_trail.id, {"archived": True})
        active = populated_storage.list_trails(active_only=True)
        assert all(not p.archived for p in active)

    def test_duplicate_trail_raises(self, populated_storage, sample_trail):
        with pytest.raises(ValidationError):
            populated_storage.create_trail(sample_trail.to_dict())


class TestTerrain:
    def test_create_terrain(self, empty_storage, sample_terrain):
        created = empty_storage.create_terrain(sample_terrain)
        assert created.key == sample_terrain.key

    def test_get_terrain(self, populated_storage, sample_terrain):
        sp = populated_storage.get_terrain(sample_terrain.key)
        assert sp.display_name == sample_terrain.display_name

    def test_delete_terrain(self, populated_storage, sample_terrain):
        populated_storage.delete_terrain(sample_terrain.key)
        with pytest.raises(NotFoundError):
            populated_storage.get_terrain(sample_terrain.key)


class TestTrailheads:
    def test_create_trailhead(self, empty_storage, sample_trailhead):
        created = empty_storage.create_trailhead(sample_trailhead)
        assert created.name == sample_trailhead.name

    def test_get_trailhead(self, populated_storage, sample_trailhead):
        loc = populated_storage.get_trailhead(sample_trailhead.id)
        assert loc.id == sample_trailhead.id

    def test_update_trailhead(self, populated_storage, sample_trailhead):
        updated = populated_storage.update_trailhead(sample_trailhead.id, {"notes": "Updated"})
        assert updated.notes == "Updated"


class TestVisit:
    def test_create_visit_event(self, populated_storage, sample_trail):
        event = populated_storage.create_visit_event({
            "id": "we_new",
            "trail_id": sample_trail.id,
            "distance_km": 300,
        })
        assert event["trail_id"] == sample_trail.id

    def test_list_visit_events_filtered(self, populated_storage, sample_trail):
        events = populated_storage.list_visit_events(trail_id=sample_trail.id)
        assert len(events) >= 1

    def test_delete_visit_event(self, populated_storage):
        events = populated_storage.list_visit_events()
        eid = events[0]["id"]
        populated_storage.delete_visit_event(eid)
        with pytest.raises(NotFoundError):
            populated_storage.get_visit_event(eid)


class TestTagsAndNotes:
    def test_create_tag(self, empty_storage):
        tag = empty_storage.create_tag({"id": "tag_new", "name": "test"})
        assert tag["name"] == "test"

    def test_create_note(self, populated_storage, sample_trail):
        note = populated_storage.create_note({
            "id": "note_new",
            "trail_id": sample_trail.id,
            "body": "Test note",
        })
        assert note["body"] == "Test note"

    def test_list_notes_filtered(self, populated_storage, sample_trail):
        notes = populated_storage.list_notes(trail_id=sample_trail.id)
        assert len(notes) >= 1


class TestAuditAndPlugins:
    def test_append_audit(self, empty_storage):
        entry = empty_storage.append_audit({"action": "create", "entity": "trail"})
        assert "timestamp" in entry

    def test_upsert_plugin(self, empty_storage):
        plugin = empty_storage.upsert_plugin({"id": "p1", "name": "Test Plugin"})
        assert plugin["name"] == "Test Plugin"
        updated = empty_storage.upsert_plugin({"id": "p1", "name": "Updated"})
        assert updated["name"] == "Updated"


class TestRecurringAndCollections:
    def test_create_recurring(self, empty_storage):
        task = empty_storage.create_recurring({"id": "r1", "title": "Weekly mist"})
        assert task["title"] == "Weekly mist"

    def test_create_collection(self, empty_storage):
        coll = empty_storage.create_collection({"id": "c1", "name": "Favorites"})
        assert coll["name"] == "Favorites"


class TestStorageCore:
    def test_snapshot(self, populated_storage):
        snap = populated_storage.snapshot()
        assert "trails" in snap

    def test_replace_all(self, empty_storage, sample_trail):
        empty_storage.replace_all({
            **DEFAULT_GARDEN,
            "trails": [sample_trail.to_dict()],
        })
        assert len(empty_storage.list_trails()) == 1

    def test_mutate(self, empty_storage):
        def add_tag(data):
            data["tags"].append({"id": "t1", "name": "test"})
        empty_storage.mutate(add_tag)
        assert len(empty_storage.list_tags()) == 1

    def test_load_corrupt_json(self, tmp_logbook_path):
        tmp_logbook_path.write_text("{not json", encoding="utf-8")
        with pytest.raises(StorageError):
            JsonStorage(tmp_logbook_path)

    def test_schema_version_in_default(self):
        assert DEFAULT_GARDEN["schema_version"] == SCHEMA_VERSION
