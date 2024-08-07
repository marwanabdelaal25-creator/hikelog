"""Tests for hikelog.collections."""

import pytest

from hikelog.errors import NotFoundError, ValidationError
from hikelog.collections import CollectionManager


class TestCollectionManager:
    def test_create(self, populated_storage, sample_trail):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Kitchen Herbs", trail_ids=[sample_trail.id])
        assert coll["name"] == "Kitchen Herbs"
        assert sample_trail.id in coll["trail_ids"]

    def test_create_empty_name_raises(self, empty_storage):
        mgr = CollectionManager(empty_storage)
        with pytest.raises(ValidationError):
            mgr.create("  ")

    def test_create_invalid_trail_raises(self, empty_storage):
        mgr = CollectionManager(empty_storage)
        with pytest.raises(NotFoundError):
            mgr.create("Bad", trail_ids=["missing"])

    def test_list_all(self, populated_storage, sample_trail):
        mgr = CollectionManager(populated_storage)
        mgr.create("Group A", trail_ids=[sample_trail.id])
        assert len(mgr.list_all()) == 1

    def test_get(self, populated_storage, sample_trail):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Favorites")
        found = mgr.get(coll["id"])
        assert found["name"] == "Favorites"

    def test_get_not_found(self, empty_storage):
        mgr = CollectionManager(empty_storage)
        with pytest.raises(NotFoundError):
            mgr.get("missing")

    def test_add_trail(self, populated_storage, sample_trail, sample_trail2):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group")
        updated = mgr.add_trail(coll["id"], sample_trail.id)
        updated = mgr.add_trail(coll["id"], sample_trail2.id)
        assert len(updated["trail_ids"]) == 2

    def test_add_trail_dedupes(self, populated_storage, sample_trail):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group", trail_ids=[sample_trail.id])
        updated = mgr.add_trail(coll["id"], sample_trail.id)
        assert updated["trail_ids"].count(sample_trail.id) == 1

    def test_remove_trail(self, populated_storage, sample_trail):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group", trail_ids=[sample_trail.id])
        updated = mgr.remove_trail(coll["id"], sample_trail.id)
        assert sample_trail.id not in updated["trail_ids"]

    def test_rename(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Old Name")
        updated = mgr.rename(coll["id"], "New Name")
        assert updated["name"] == "New Name"

    def test_rename_blank_raises(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Name")
        with pytest.raises(ValidationError):
            mgr.rename(coll["id"], "  ")

    def test_delete(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Temp")
        mgr.delete(coll["id"])
        assert mgr.list_all() == []

    def test_trails_in(self, populated_storage, sample_trail):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group", trail_ids=[sample_trail.id])
        trails = mgr.trails_in(coll["id"])
        assert len(trails) == 1

    def test_trails_in_skips_stale(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group")
        populated_storage.update_collection(coll["id"], {"trail_ids": ["stale_id"]})
        assert mgr.trails_in(coll["id"]) == []

    def test_collections_for_trail(self, populated_storage, sample_trail):
        mgr = CollectionManager(populated_storage)
        mgr.create("A", trail_ids=[sample_trail.id])
        mgr.create("B", trail_ids=[sample_trail.id])
        cols = mgr.collections_for_trail(sample_trail.id)
        assert len(cols) == 2

    def test_merge(self, populated_storage, sample_trail, sample_trail2):
        mgr = CollectionManager(populated_storage)
        t = mgr.create("Target", trail_ids=[sample_trail.id])
        s = mgr.create("Source", trail_ids=[sample_trail2.id])
        merged = mgr.merge(t["id"], s["id"])
        assert sample_trail2.id in merged["trail_ids"]
        assert len(mgr.list_all()) == 1

    def test_merge_dedupes_overlap(self, populated_storage, sample_trail):
        mgr = CollectionManager(populated_storage)
        t = mgr.create("Target", trail_ids=[sample_trail.id])
        s = mgr.create("Source", trail_ids=[sample_trail.id])
        merged = mgr.merge(t["id"], s["id"])
        assert merged["trail_ids"].count(sample_trail.id) == 1

    def test_description_stored(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Herbs", description="Kitchen window")
        assert coll["description"] == "Kitchen window"

    def test_add_unknown_trail_raises(self, populated_storage):
        mgr = CollectionManager(populated_storage)
        coll = mgr.create("Group")
        with pytest.raises(NotFoundError):
            mgr.add_trail(coll["id"], "missing")
