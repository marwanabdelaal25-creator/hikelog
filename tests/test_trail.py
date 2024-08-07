"""Tests for hikelog.trail."""

from datetime import date, timedelta

import pytest

from hikelog.errors import NotFoundError
from hikelog.trail import (
    TrailStatus,
    PackInfo,
    Trail,
    TrailCatalog,
    trail_health_report,
    apply_terrain_defaults,
    sort_by_visit_priority,
    clone_trail,
    bulk_update_interval,
    catalog_to_summary_lines,
    find_duplicates_by_name,
    parse_iso,
)
from hikelog.terrain import TerrainProfile


class TestTrailStatus:
    def test_emoji(self):
        assert TrailStatus.THRIVING.emoji == "🌿"

    def test_score_hint(self):
        assert TrailStatus.CRITICAL.score_hint() == 15


class TestPackInfo:
    def test_to_dict_roundtrip(self):
        pack = PackInfo(diameter=6.0, unit="in", material="ceramic")
        restored = PackInfo.from_dict(pack.to_dict())
        assert restored.diameter == 6.0

    def test_label(self):
        pack = PackInfo(diameter=6.0, unit="in", material="ceramic")
        assert "6.0in" in pack.label()

    def test_label_no_drainage(self):
        pack = PackInfo(diameter=6.0, has_drainage=False)
        assert "no drainage" in pack.label()


class TestTrail:
    def test_create(self, sample_trail):
        assert sample_trail.name == "Half Dome"
        assert sample_trail.id == "trail001"

    def test_display_name_with_nickname(self, sample_trail):
        assert "HD-01" in sample_trail.display_name

    def test_set_health(self, sample_trail):
        sample_trail.set_health(TrailStatus.THRIVING, 90)
        assert sample_trail.health == TrailStatus.THRIVING
        assert sample_trail.health_score == 90

    def test_record_visit(self, sample_trail):
        when = date.today()
        sample_trail.record_visit(when)
        assert sample_trail.last_visited_at == when.isoformat()

    def test_days_since_visited(self, sample_trail):
        assert sample_trail.days_since_visited() == 3

    def test_is_overdue(self, sample_trail):
        sample_trail.last_visited_at = (date.today() - timedelta(days=20)).isoformat()
        assert sample_trail.is_overdue() is True

    def test_overdue_by_days(self, sample_trail):
        sample_trail.last_visited_at = (date.today() - timedelta(days=20)).isoformat()
        assert sample_trail.overdue_by_days() == 13

    def test_attach_detach_tag(self, sample_trail):
        sample_trail.attach_tag("tag001")
        assert "tag001" in sample_trail.tag_ids
        assert sample_trail.detach_tag("tag001") is True

    def test_detach_missing_tag(self, sample_trail):
        assert sample_trail.detach_tag("missing") is False

    def test_archive_unarchive(self, sample_trail):
        sample_trail.archive()
        assert sample_trail.archived is True
        sample_trail.unarchive()
        assert sample_trail.archived is False

    def test_to_dict_from_dict(self, sample_trail):
        restored = Trail.from_dict(sample_trail.to_dict())
        assert restored.name == sample_trail.name

    def test_summary_line(self, sample_trail):
        line = sample_trail.summary_line()
        assert "Half Dome" in line or "HD-01" in line


class TestTrailCatalog:
    def test_add_and_get(self, trail_catalog, sample_trail):
        assert trail_catalog.get(sample_trail.id) is not None

    def test_duplicate_id_raises(self, sample_trail):
        cat = TrailCatalog()
        cat.add(sample_trail)
        with pytest.raises(ValueError):
            cat.add(sample_trail)

    def test_require_raises(self):
        cat = TrailCatalog()
        with pytest.raises(NotFoundError):
            cat.require("missing")

    def test_all_excludes_archived(self, trail_catalog, sample_trail):
        sample_trail.archive()
        assert sample_trail not in trail_catalog.all()

    def test_find_by_name(self, trail_catalog, sample_trail):
        assert sample_trail in trail_catalog.find_by_name("Half Dome")

    def test_find_by_trailhead(self, trail_catalog, sample_trail, sample_trailhead):
        found = trail_catalog.find_by_trailhead(sample_trailhead.id)
        assert len(found) >= 1

    def test_find_by_terrain(self, trail_catalog, sample_trail):
        found = trail_catalog.find_by_terrain("mist-loop")
        assert sample_trail in found

    def test_find_overdue(self, trail_catalog, sample_trail):
        sample_trail.last_visited_at = (date.today() - timedelta(days=30)).isoformat()
        assert sample_trail in trail_catalog.find_overdue()

    def test_find_by_tag(self, trail_catalog, sample_trail):
        sample_trail.attach_tag("tag001")
        assert sample_trail in trail_catalog.find_by_tag("tag001")

    def test_remove(self, trail_catalog, sample_trail):
        assert trail_catalog.remove(sample_trail.id) is True
        assert trail_catalog.get(sample_trail.id) is None

    def test_count_by_health(self, trail_catalog):
        counts = trail_catalog.count_by_health()
        assert isinstance(counts, dict)

    def test_merge(self, trail_catalog, sample_trail2):
        other = TrailCatalog()
        other.add(sample_trail2)
        merged = trail_catalog.merge(other)
        assert merged.count() == 2


class TestTrailHelpers:
    def test_trail_health_report(self, trail_catalog):
        report = trail_health_report(trail_catalog)
        assert "total" in report
        assert "overdue_count" in report

    def test_apply_terrain_defaults(self, sample_trail, sample_terrain):
        sample_trail.visit_interval_days = 7
        apply_terrain_defaults(sample_trail, sample_terrain)
        assert sample_trail.terrain_key == sample_terrain.key

    def test_sort_by_visit_priority(self, sample_trail, sample_trail2):
        sample_trail.last_visited_at = (date.today() - timedelta(days=30)).isoformat()
        sorted_trails = sort_by_visit_priority([sample_trail2, sample_trail])
        assert sorted_trails[0].id == sample_trail.id

    def test_clone_trail(self, sample_trail):
        clone = clone_trail(sample_trail, "Half Dome Jr")
        assert clone.id != sample_trail.id
        assert clone.name == "Half Dome Jr"
        assert clone.metadata.get("propagated_from") == sample_trail.id

    def test_bulk_update_interval(self, trail_catalog, sample_trail):
        updated = bulk_update_interval(trail_catalog, [sample_trail.id], 10)
        assert updated == 1
        assert trail_catalog.get(sample_trail.id).visit_interval_days == 10

    def test_catalog_to_summary_lines(self, trail_catalog):
        lines = catalog_to_summary_lines(trail_catalog)
        assert len(lines) >= 1

    def test_find_duplicates_by_name(self, sample_trail):
        cat = TrailCatalog()
        cat.add(sample_trail)
        dup = Trail.create("Half Dome", id="dup001")
        cat.add(dup)
        dupes = find_duplicates_by_name(cat)
        assert "half dome" in dupes

    def test_parse_iso(self):
        assert parse_iso("2024-06-01T12:00:00") is not None

    def test_parse_iso_none(self):
        assert parse_iso(None) is None

    def test_record_visit_bumps_struggling_health(self):
        trail = Trail.create("Ridge Trail", health=TrailStatus.STRUGGLING, health_score=40)
        trail.record_visit()
        assert trail.health_score >= 40
