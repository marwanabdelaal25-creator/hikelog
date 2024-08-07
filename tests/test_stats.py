"""Tests for hikelog.stats."""

import json

from hikelog.stats import GardenStats


class TestGardenStats:
    def test_snapshot_empty(self, empty_storage):
        stats = GardenStats(empty_storage)
        snap = stats.snapshot()
        assert snap["trails_total"] == 0

    def test_snapshot_populated(self, populated_storage):
        stats = GardenStats(populated_storage)
        snap = stats.snapshot()
        assert snap["trails_total"] >= 2
        assert snap["trails_active"] >= 1

    def test_generated_at(self, populated_storage):
        stats = GardenStats(populated_storage)
        snap = stats.snapshot()
        assert "generated_at" in snap

    def test_terrain_trailheads_tags_counts(self, populated_storage):
        stats = GardenStats(populated_storage)
        snap = stats.snapshot()
        assert snap["terrain_count"] >= 1
        assert snap["trailheads_count"] >= 1

    def test_watered_last_7_days(self, populated_storage):
        stats = GardenStats(populated_storage)
        snap = stats.snapshot()
        assert "watered_last_7_days" in snap

    def test_watered_last_30_days(self, populated_storage):
        stats = GardenStats(populated_storage)
        snap = stats.snapshot()
        assert snap["watered_last_30_days"] >= 0

    def test_overdue_count(self, populated_storage):
        stats = GardenStats(populated_storage)
        snap = stats.snapshot()
        assert "overdue_count" in snap

    def test_due_today_count(self, populated_storage):
        stats = GardenStats(populated_storage)
        snap = stats.snapshot()
        assert "due_today_count" in snap

    def test_avg_visit_interval(self, populated_storage):
        stats = GardenStats(populated_storage)
        snap = stats.snapshot()
        assert snap["avg_visit_interval_days"] > 0

    def test_trip_logs_and_notes_totals(self, populated_storage):
        stats = GardenStats(populated_storage)
        snap = stats.snapshot()
        assert snap["notes_total"] >= 1

    def test_render_text(self, populated_storage):
        stats = GardenStats(populated_storage)
        text = stats.render_text()
        assert "trails" in text.lower() or "Garden" in text

    def test_render_text_empty(self, empty_storage):
        stats = GardenStats(empty_storage)
        text = stats.render_text()
        assert isinstance(text, str)

    def test_archived_not_in_active_count(self, populated_storage, sample_trail):
        populated_storage.update_trail(sample_trail.id, {"archived": True})
        stats = GardenStats(populated_storage)
        snap = stats.snapshot()
        assert snap["trails_active"] < snap["trails_total"]

    def test_collections_total(self, empty_storage):
        stats = GardenStats(empty_storage)
        snap = stats.snapshot()
        assert snap.get("collections_total", 0) == 0

    def test_snapshot_json_serializable(self, populated_storage):
        stats = GardenStats(populated_storage)
        snap = stats.snapshot()
        json.dumps(snap)
