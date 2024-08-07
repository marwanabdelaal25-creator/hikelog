"""Tests for hikelog.trailhead."""

import pytest

from hikelog.errors import NotFoundError
from hikelog.trailhead import (
    AspectDirection,
    Trailhead,
    TrailheadRegistry,
    TrailheadClimateProfile,
    default_trailheads,
    compare_light,
    suggest_trails_for_trailhead,
    trailhead_report,
    reassign_trail,
    estimate_daily_light_hours,
    rank_trailheads_for_terrain,
    build_trailhead_map,
    trails_without_trailhead,
    trailhead_capacity_report,
    RoomSnapshot,
    RoomHistory,
    sync_trailhead_trail_ids,
    format_trailhead_tree,
)
from hikelog.terrain import TerrainCatalog


class TestAspectDirection:
    def test_str(self):
        assert str(AspectDirection.SOUTH) == "south"


class TestTrailhead:
    def test_create(self, sample_trailhead):
        assert sample_trailhead.name == "Yosemite Valley"

    def test_add_remove_trail(self, sample_trailhead):
        sample_trailhead.add_trail("trail001")
        assert "trail001" in sample_trailhead.trail_ids
        assert sample_trailhead.remove_trail("trail001") is True

    def test_effective_light_south(self):
        loc = Trailhead.create(
            "Bright Room",
            difficulty="medium",
            window_direction=AspectDirection.SOUTH,
        )
        assert compare_light(loc.effective_light(), "medium") >= 0

    def test_label(self, sample_trailhead):
        assert "Yosemite Valley" in sample_trailhead.label()

    def test_to_dict_from_dict(self, sample_trailhead):
        restored = Trailhead.from_dict(sample_trailhead.to_dict())
        assert restored.name == sample_trailhead.name

    def test_summary(self, sample_trailhead):
        summary = sample_trailhead.summary()
        assert "Yosemite Valley" in summary


class TestTrailheadRegistry:
    def test_add_and_get(self, trailhead_registry, sample_trailhead):
        assert trailhead_registry.get(sample_trailhead.id) is not None

    def test_duplicate_id_raises(self, sample_trailhead):
        reg = TrailheadRegistry()
        reg.add(sample_trailhead)
        with pytest.raises(ValueError):
            reg.add(sample_trailhead)

    def test_get_by_name(self, trailhead_registry, sample_trailhead):
        assert trailhead_registry.get_by_name("Yosemite Valley") is not None

    def test_require_raises(self):
        reg = TrailheadRegistry()
        with pytest.raises(NotFoundError):
            reg.require("missing")

    def test_remove(self, trailhead_registry, sample_trailhead):
        assert trailhead_registry.remove(sample_trailhead.id) is True

    def test_assign_unassign_trail(self, trailhead_registry, sample_trailhead):
        trailhead_registry.assign_trail(sample_trailhead.id, "trail001")
        assert "trail001" in trailhead_registry.get(sample_trailhead.id).trail_ids
        trailhead_registry.unassign_trail("trail001")
        assert "trail001" not in trailhead_registry.get(sample_trailhead.id).trail_ids

    def test_find_by_light(self, trailhead_registry):
        found = trailhead_registry.find_by_light("moderate")
        assert len(found) >= 1

    def test_find_by_zone(self, trailhead_registry, sample_trailhead):
        found = trailhead_registry.find_by_zone("main")
        assert sample_trailhead in found

    def test_total_trails_assigned(self, trailhead_registry, sample_trailhead):
        sample_trailhead.add_trail("p1")
        trailhead_registry._trailheads[sample_trailhead.id] = sample_trailhead
        assert trailhead_registry.total_trails_assigned() >= 1

    def test_trailheads_needing_humidifier(self, trailhead_registry):
        low = trailhead_registry.trailheads_needing_humidifier(threshold=50)
        assert isinstance(low, list)

    def test_merge(self, trailhead_registry, sample_trailhead):
        other = TrailheadRegistry()
        other.add(Trailhead.create("Kitchen", id="loc002"))
        merged = trailhead_registry.merge(other)
        assert merged.count() == 2


class TestClimateProfile:
    def test_from_trailhead(self, sample_trailhead):
        profile = TrailheadClimateProfile.from_trailhead(sample_trailhead)
        assert profile.trailhead_id == sample_trailhead.id

    def test_visit_factor_high_conditions(self):
        profile = TrailheadClimateProfile(
            trailhead_id="loc1",
            avg_conditions=70.0,
        )
        assert profile.visit_factor() > 1.0

    def test_visit_factor_draft(self, sample_trailhead):
        sample_trailhead.notes = "drafty window"
        profile = TrailheadClimateProfile.from_trailhead(sample_trailhead)
        assert profile.draft_risk is True


class TestTrailheadHelpers:
    def test_default_trailheads(self):
        reg = default_trailheads()
        assert reg.count() >= 4

    def test_compare_light(self):
        assert compare_light("low", "full_sun") == -1
        assert compare_light("full_sun", "low") == 1
        assert compare_light("medium", "medium") == 0

    def test_suggest_trails_for_trailhead(self, sample_trailhead):
        keys = suggest_trails_for_trailhead(sample_trailhead)
        assert isinstance(keys, list)

    def test_trailhead_report(self, trailhead_registry):
        report = trailhead_report(trailhead_registry)
        assert "trailhead_count" in report

    def test_reassign_trail(self, trailhead_registry, sample_trailhead):
        kitchen = Trailhead.create("Kitchen", id="loc_k")
        trailhead_registry.add(kitchen)
        reassign_trail(trailhead_registry, "trail001", sample_trailhead.id, kitchen.id)
        assert "trail001" in kitchen.trail_ids

    def test_estimate_daily_light_hours(self, sample_trailhead):
        hours = estimate_daily_light_hours(sample_trailhead, month=7)
        assert hours > 0

    def test_rank_trailheads_for_terrain(self, trailhead_registry, sample_terrain):
        ranked = rank_trailheads_for_terrain(trailhead_registry, sample_terrain)
        assert len(ranked) >= 1

    def test_build_trailhead_map(self, trailhead_registry):
        mapping = build_trailhead_map(trailhead_registry)
        assert "yosemite valley" in mapping

    def test_trails_without_trailhead(self, trailhead_registry):
        missing = trails_without_trailhead(trailhead_registry, ["trail001", "trail999"])
        assert "trail999" in missing

    def test_trailhead_capacity_report(self, trailhead_registry, sample_trailhead):
        sample_trailhead.trail_ids = ["p1", "p2"]
        report = trailhead_capacity_report(trailhead_registry, max_per_room=1)
        assert len(report["crowded"]) >= 1

    def test_room_history(self):
        hist = RoomHistory()
        snap = RoomSnapshot(trailhead_id="loc1", recorded_at="2024-06-01", elevation_gain_m=50)
        hist.record(snap)
        assert len(hist.for_trailhead("loc1")) == 1
        assert hist.avg_conditions("loc1") == 50.0

    def test_sync_trailhead_trail_ids(self, trailhead_registry, sample_trail):
        sync_trailhead_trail_ids(trailhead_registry, [sample_trail])
        loc = trailhead_registry.get(sample_trail.trailhead_id)
        assert sample_trail.id in loc.trail_ids

    def test_format_trailhead_tree(self, trailhead_registry):
        text = format_trailhead_tree(trailhead_registry)
        assert "Yosemite Valley" in text
