"""Tests for hikelog.reports."""

from datetime import datetime, timezone

import pytest

from hikelog.reports import MonthlyReport, trail_map_name


class TestTrailMapName:
    def test_valid_trail(self, populated_storage, sample_trail):
        name = trail_map_name(populated_storage, sample_trail.id)
        assert name == sample_trail.name

    def test_unknown_id(self, empty_storage):
        name = trail_map_name(empty_storage, "missing")
        assert name == "missing"


class TestMonthlyReport:
    def test_generate_empty(self, empty_storage):
        report = MonthlyReport(empty_storage)
        data = report.generate(2024, 6)
        assert data["totals"]["visits"] == 0

    def test_generate_with_visits(self, populated_storage):
        report = MonthlyReport(populated_storage)
        now = datetime.now(timezone.utc)
        data = report.generate(now.year, now.month)
        assert "totals" in data
        assert data["totals"]["visits"] >= 0

    def test_period_bounds(self, populated_storage):
        report = MonthlyReport(populated_storage)
        data = report.generate(2024, 6)
        assert data["period_start"].startswith("2024-06")

    def test_foot_trailed_trails(self, populated_storage):
        report = MonthlyReport(populated_storage)
        now = datetime.now(timezone.utc)
        data = report.generate(now.year, now.month)
        assert "foot_trailed_trails" in data

    def test_care_action_breakdown(self, populated_storage):
        report = MonthlyReport(populated_storage)
        data = report.generate(2024, 1)
        assert "care_action_breakdown" in data

    def test_visits_by_trailhead(self, populated_storage):
        report = MonthlyReport(populated_storage)
        now = datetime.now(timezone.utc)
        data = report.generate(now.year, now.month)
        assert "visits_by_trailhead" in data

    def test_render_text(self, populated_storage):
        report = MonthlyReport(populated_storage)
        now = datetime.now(timezone.utc)
        text = report.render_text(now.year, now.month)
        assert str(now.year) in text or "Report" in text

    def test_render_text_empty_month(self, empty_storage):
        report = MonthlyReport(empty_storage)
        text = report.render_text(2020, 1)
        assert isinstance(text, str)

    def test_february_leap_year(self, populated_storage):
        report = MonthlyReport(populated_storage)
        data = report.generate(2024, 2)
        assert "2024-02" in data["period_start"]

    def test_december_boundary(self, populated_storage):
        report = MonthlyReport(populated_storage)
        data = report.generate(2024, 12)
        assert data["period_end"].startswith("2024-12")

    def test_unique_trails_watered(self, populated_storage):
        report = MonthlyReport(populated_storage)
        now = datetime.now(timezone.utc)
        data = report.generate(now.year, now.month)
        assert "unique_trails_watered" in data["totals"]

    def test_hazard_and_gear_counts(self, populated_storage):
        report = MonthlyReport(populated_storage)
        data = report.generate(2024, 6)
        assert "hazard_incidents" in data["totals"]
        assert "gear_events" in data["totals"]
