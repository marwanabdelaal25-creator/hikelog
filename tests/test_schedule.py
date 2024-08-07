"""Tests for hikelog.schedule."""

from datetime import date, timedelta

import pytest

from hikelog.trail import TrailStatus, TrailCatalog
from hikelog.schedule import (
    Season,
    detect_season,
    ScheduleEntry,
    ScheduleOptions,
    ScheduleEngine,
    compute_next_visit,
    month_calendar,
    format_schedule_text,
    group_by_trailhead,
    estimate_weekly_water_ml,
    reschedule_after_visit,
    compare_seasons,
    ScheduleReport,
    build_schedule_report,
    trails_by_urgency,
    next_n_days,
    interval_audit,
    apply_seasonal_intervals,
    schedule_conflicts,
)


class TestDetectSeason:
    @pytest.mark.parametrize("month,expected", [
        (6, Season.SUMMER), (12, Season.WINTER), (3, Season.SPRING), (10, Season.FALL),
    ])
    def test_season_for_month(self, month, expected):
        assert detect_season(date(2024, month, 15)) == expected


class TestScheduleEntry:
    def test_days_until_due(self):
        entry = ScheduleEntry(
            trail_id="p1",
            trail_name="Ridge Trail",
            next_due=(date.today() + timedelta(days=3)).isoformat(),
            base_interval_days=7,
            adjusted_interval_days=7,
            season="summer",
        )
        assert entry.days_until_due() == 3

    def test_to_dict_from_dict(self):
        entry = ScheduleEntry(
            trail_id="p1",
            trail_name="Ridge Trail",
            next_due=date.today().isoformat(),
            base_interval_days=7,
            adjusted_interval_days=7,
            season="spring",
        )
        restored = ScheduleEntry.from_dict(entry.to_dict())
        assert restored.trail_id == "p1"


class TestScheduleEngine:
    def test_build_entry(self, trail_catalog, terrain_catalog, trailhead_registry, sample_trail):
        engine = ScheduleEngine(
            trails=trail_catalog,
            terrain=terrain_catalog,
            trailheads=trailhead_registry,
        )
        entry = engine.build_entry(sample_trail)
        assert entry.trail_id == sample_trail.id

    def test_overdue(self, trail_catalog, terrain_catalog, sample_trail):
        sample_trail.last_visited_at = (date.today() - timedelta(days=30)).isoformat()
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        overdue = engine.overdue()
        assert len(overdue) >= 1

    def test_today(self, trail_catalog, terrain_catalog, sample_trail):
        sample_trail.last_visited_at = (date.today() - timedelta(days=30)).isoformat()
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        due = engine.today()
        assert len(due) >= 1

    def test_week_schedule(self, trail_catalog, terrain_catalog):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        entries = engine.week_schedule()
        assert isinstance(entries, list)

    def test_full_schedule(self, trail_catalog, terrain_catalog):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        entries = engine.full_schedule()
        assert len(entries) == 2

    def test_adjusted_interval_season(self, trail_catalog, terrain_catalog, sample_trail):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        engine.set_options(season_override=Season.WINTER)
        interval = engine.adjusted_interval(sample_trail)
        assert interval >= engine.options.min_interval_days

    def test_health_multiplier_critical(self, trail_catalog, terrain_catalog, sample_trail):
        sample_trail.set_health(TrailStatus.CRITICAL)
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        mult = engine.health_multiplier(sample_trail)
        assert mult < 1.0

    def test_trailhead_multiplier(self, trail_catalog, terrain_catalog, trailhead_registry, sample_trail):
        engine = ScheduleEngine(
            trails=trail_catalog,
            terrain=terrain_catalog,
            trailheads=trailhead_registry,
        )
        mult = engine.trailhead_multiplier(sample_trail)
        assert mult > 0

    def test_pack_multiplier_small_pack(self, trail_catalog, terrain_catalog, sample_trail):
        sample_trail.pack.diameter = 3.0
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        assert engine.pack_multiplier(sample_trail) < 1.0

    def test_preview_interval_change(self, trail_catalog, terrain_catalog, sample_trail):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        preview = engine.preview_interval_change(sample_trail, 14)
        assert preview["new_base_days"] == 14

    def test_summarize_week(self, trail_catalog, terrain_catalog):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        summary = engine.summarize_week()
        assert "total_due" in summary

    def test_sync_trail_intervals_from_terrain(self, trail_catalog, terrain_catalog, sample_trail2):
        sample_trail2.visit_interval_days = 7
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        updated = engine.sync_trail_intervals_from_terrain()
        assert updated >= 0


class TestScheduleHelpers:
    def test_compute_next_visit(self, sample_trail):
        nxt = compute_next_visit(sample_trail)
        assert isinstance(nxt, date)

    def test_format_schedule_text(self, trail_catalog, terrain_catalog, sample_trail):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        text = format_schedule_text([engine.build_entry(sample_trail)])
        assert "Visit schedule" in text

    def test_group_by_trailhead(self, trail_catalog, terrain_catalog, trailhead_registry):
        engine = ScheduleEngine(
            trails=trail_catalog,
            terrain=terrain_catalog,
            trailheads=trailhead_registry,
        )
        groups = group_by_trailhead(engine)
        assert isinstance(groups, dict)

    def test_estimate_weekly_water_ml(self, trail_catalog, terrain_catalog):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        ml = estimate_weekly_water_ml(engine)
        assert ml >= 0

    def test_reschedule_after_visit(self, trail_catalog, terrain_catalog, sample_trail):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        entry = reschedule_after_visit(engine, sample_trail)
        assert entry.last_visited_at == date.today().isoformat()

    def test_compare_seasons(self, trail_catalog, terrain_catalog, sample_trail):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        seasons = compare_seasons(engine, sample_trail)
        assert "winter" in seasons
        assert seasons["winter"] >= seasons["summer"]

    def test_build_schedule_report(self, trail_catalog, terrain_catalog):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        report = build_schedule_report(engine)
        assert isinstance(report, ScheduleReport)
        assert report.due_today >= 0

    def test_trails_by_urgency(self, trail_catalog, terrain_catalog):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        entries = trails_by_urgency(engine)
        assert len(entries) == 2

    def test_next_n_days(self, trail_catalog, terrain_catalog):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        buckets = next_n_days(engine, n=14)
        assert isinstance(buckets, dict)

    def test_interval_audit(self, trail_catalog, terrain_catalog):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        rows = interval_audit(engine)
        assert len(rows) == 2

    def test_apply_seasonal_intervals_dry_run(self, trail_catalog, terrain_catalog):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        changes = apply_seasonal_intervals(engine, dry_run=True)
        assert len(changes) == 2

    def test_schedule_conflicts(self, trail_catalog, terrain_catalog, trailhead_registry):
        engine = ScheduleEngine(
            trails=trail_catalog,
            terrain=terrain_catalog,
            trailheads=trailhead_registry,
        )
        entries = engine.full_schedule()
        conflicts = schedule_conflicts(entries)
        assert isinstance(conflicts, list)

    def test_month_calendar(self, trail_catalog, terrain_catalog):
        engine = ScheduleEngine(trails=trail_catalog, terrain=terrain_catalog)
        cal = month_calendar(engine, date.today().year, date.today().month)
        assert isinstance(cal, dict)
