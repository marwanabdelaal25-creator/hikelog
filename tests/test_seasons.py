"""Tests for hikelog.seasons."""

from datetime import date, datetime

import pytest

from hikelog.seasons import (
    SeasonWindow,
    DEFAULT_SEASONS,
    SeasonCalendar,
    effective_visit_interval,
)


class TestSeasonWindow:
    def test_default_seasons_exist(self):
        assert len(DEFAULT_SEASONS) == 4


class TestSeasonCalendar:
    @pytest.mark.parametrize("month,expected", [
        (7, "summer"), (12, "winter"), (4, "spring"), (10, "fall"),
    ])
    def test_season_for_month(self, month, expected):
        cal = SeasonCalendar()
        assert cal.season_for(date(2024, month, 15)) == expected

    def test_multiplier_summer(self):
        cal = SeasonCalendar()
        assert cal.multiplier_for(date(2024, 7, 1)) == 0.85

    def test_multiplier_winter(self):
        cal = SeasonCalendar()
        assert cal.multiplier_for(date(2024, 1, 15)) == 1.25

    def test_datetime_input(self):
        cal = SeasonCalendar()
        assert cal.season_for(datetime(2024, 6, 1)) == "summer"

    def test_describe(self):
        cal = SeasonCalendar()
        desc = cal.describe(date(2024, 6, 15))
        assert desc["season"] == "summer"
        assert desc["multiplier"] == 0.85

    def test_describe_default_today(self):
        cal = SeasonCalendar()
        desc = cal.describe()
        assert "date" in desc

    def test_custom_seasons(self):
        custom = [SeasonWindow("dry", 1, 1, 12, 31, 1.5)]
        cal = SeasonCalendar(seasons=custom)
        assert cal.multiplier_for(date(2024, 6, 1)) == 1.5

    def test_winter_spans_year_end(self):
        cal = SeasonCalendar()
        assert cal.season_for(date(2024, 1, 15)) == "winter"
        assert cal.season_for(date(2024, 12, 15)) == "winter"

    def test_hemisphere_stored(self):
        cal = SeasonCalendar(hemisphere="south")
        assert cal.hemisphere == "south"

    def test_unknown_date_fallback(self):
        cal = SeasonCalendar()
        cal.seasons = []
        assert cal.season_for(date(2024, 6, 1)) == "spring"
        assert cal.multiplier_for(date(2024, 6, 1)) == 1.0

    def test_window_boundaries_start(self):
        cal = SeasonCalendar()
        assert cal.season_for(date(2024, 3, 1)) == "spring"

    def test_window_boundaries_end(self):
        cal = SeasonCalendar()
        assert cal.season_for(date(2024, 5, 31)) == "spring"


class TestEffectiveVisitInterval:
    def test_basic_multiplier(self):
        assert effective_visit_interval(7, 1.25) == 9

    def test_minimum_one_day(self):
        assert effective_visit_interval(1, 0.85) == 1

    def test_round_half_up(self):
        assert effective_visit_interval(10, 0.85) == 8

    def test_summer_shorter(self):
        summer = effective_visit_interval(7, 0.85)
        winter = effective_visit_interval(7, 1.25)
        assert summer < winter

    def test_leap_day(self):
        cal = SeasonCalendar()
        # Feb 29 falls outside the winter window (ends Feb 28); defaults to spring
        assert cal.season_for(date(2024, 2, 29)) == "spring"
