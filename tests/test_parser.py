"""Tests for hikelog.parser."""

from datetime import date, timedelta

import pytest

from hikelog.parser import (
    parse_date,
    parse_relative_date,
    parse_datetime,
    parse_interval,
    parse_interval_range,
    parse_distance_km,
    parse_difficulty,
    parse_conditions,
    parse_temperature,
    parse_bool,
    coerce_int,
    coerce_float,
    parse_key_value,
    parse_key_value_pairs,
    parse_tags,
    parse_pack_size,
    parse_soil_mix,
    parse_visit_method,
    parse_ph,
    parse_season_hint,
    split_csv_line,
    parse_duration_minutes,
    parse_gear_strength,
    parse_health_note,
    normalize_trail_name,
    try_parse_date,
    try_parse_interval,
    format_interval_days,
    format_distance_km,
    format_difficulty,
    parse_soil_ph_range,
    parse_weekday,
    parse_weekly_schedule,
    parse_trail_list,
    parse_health_status,
    parse_reminder_offset,
    parse_npk,
    parse_growth_rate,
    parse_misting_frequency,
    coerce_light_list,
    parse_trailhead_descriptor,
    parse_import_row,
    normalize_enum,
    parse_care_frequency,
    format_conditions,
    format_temperature_c,
    format_health_status,
    tokenize_search_query,
)


class TestParseDate:
    def test_today(self):
        assert parse_date("today") == date.today()

    def test_yesterday(self):
        assert parse_date("yesterday") == date.today() - timedelta(days=1)

    def test_iso_format(self):
        assert parse_date("2024-06-15") == date(2024, 6, 15)

    @pytest.mark.parametrize("text", ["not-a-date", "99/99/9999"])
    def test_invalid_raises(self, text):
        with pytest.raises(ValueError):
            parse_date(text)


class TestParseRelativeDate:
    def test_plus_days(self):
        result = parse_relative_date("+3d")
        assert result == date.today() + timedelta(days=3)

    def test_minus_weeks(self):
        result = parse_relative_date("-2w")
        assert result == date.today() - timedelta(weeks=2)

    def test_bad_relative(self):
        with pytest.raises(ValueError):
            parse_relative_date("+xyz")


class TestParseInterval:
    @pytest.mark.parametrize("text,expected", [
        ("7d", 7), ("2 weeks", 14), ("every 5 days", 5), ("14", 14),
    ])
    def test_intervals(self, text, expected):
        assert parse_interval(text) == expected

    def test_bad_interval(self):
        with pytest.raises(ValueError):
            parse_interval("never")


class TestParseAmount:
    def test_ml(self):
        assert parse_distance_km("250ml") == 250.0

    def test_liters(self):
        assert parse_distance_km("1.5L") == 1500.0

    def test_cups(self):
        assert parse_distance_km("1 cup") == pytest.approx(236.588, rel=0.01)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_distance_km("")


class TestParseLight:
    @pytest.mark.parametrize("text,expected", [
        ("low", "low"), ("bright indirect", "moderate"), ("full sun", "full_sun"),
    ])
    def test_aliases(self, text, expected):
        assert parse_difficulty(text) == expected

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            parse_difficulty("moonlight")


class TestParseConditionsAndTemp:
    def test_conditions_percent(self):
        assert parse_conditions("55%") == 55.0

    def test_temperature_celsius(self):
        assert parse_temperature("22c") == 22.0

    def test_temperature_fahrenheit(self):
        assert parse_temperature("32f") == pytest.approx(0.0, abs=0.1)


class TestParseBool:
    @pytest.mark.parametrize("raw,expected", [("yes", True), ("0", False), ("on", True)])
    def test_bool_values(self, raw, expected):
        assert parse_bool(raw) == expected


class TestCoerce:
    def test_coerce_int_default(self):
        assert coerce_int("abc", default=5) == 5

    def test_coerce_float(self):
        assert coerce_float("3.14") == 3.14


class TestKeyValue:
    def test_colon_separator(self):
        assert parse_key_value("name: Half Dome") == ("name", "Half Dome")

    def test_pairs_dict(self):
        result = parse_key_value_pairs("a=1, b=2")
        assert result == {"a": "1", "b": "2"}


class TestTagsAndPack:
    def test_parse_tags_dedupes(self):
        assert parse_tags("beginner, Beginner; pet-safe") == ["beginner", "pet-safe"]

    def test_parse_pack_size(self):
        result = parse_pack_size("6in ceramic")
        assert result["diameter"] == 6.0
        assert result["material"] == "ceramic"


class TestSoilAndMethod:
    def test_soil_mix(self):
        assert parse_soil_mix("peat, perlite, bark") == ["peat", "perlite", "bark"]

    def test_visit_method(self):
        assert parse_visit_method("bottom water") == "switchback"


class TestPhAndSeason:
    def test_parse_ph(self):
        assert parse_ph("6.5") == 6.5

    def test_ph_out_of_range(self):
        with pytest.raises(ValueError):
            parse_ph("15")

    def test_season_hint(self):
        assert parse_season_hint("autumn") == "fall"


class TestCsvAndDuration:
    def test_split_csv_quoted(self):
        assert split_csv_line('"Ridge, big",kitchen,7d') == ["Ridge, big", "kitchen", "7d"]

    def test_duration_minutes(self):
        assert parse_duration_minutes("1h 30m") == 90


class TestGearAndHealth:
    def test_half_strength(self):
        assert parse_gear_strength("half strength")["dilution"] == 0.5

    def test_health_note_flags(self):
        flags = parse_health_note("Yellow leaves and drooping")
        assert flags.get("yellowing") is True
        assert flags.get("drooping") is True


class TestFormatters:
    def test_format_interval_weeks(self):
        assert format_interval_days(14) == "2w"

    def test_format_amount_liters(self):
        assert format_distance_km(1500) == "1.5L"

    def test_format_difficulty(self):
        assert "Bright" in format_difficulty("moderate")


class TestWeekdayAndSchedule:
    def test_parse_weekday(self):
        assert parse_weekday("Monday") == 0

    def test_weekly_schedule(self):
        assert parse_weekly_schedule("mon,wed,fri") == [0, 2, 4]


class TestHealthAndNpk:
    def test_health_status(self):
        assert parse_health_status("great") == "thriving"

    def test_npk(self):
        assert parse_npk("10-10-10") == (10.0, 10.0, 10.0)


class TestTryParse:
    def test_try_parse_date_default(self):
        assert try_parse_date("bad", default=date(2020, 1, 1)) == date(2020, 1, 1)

    def test_try_parse_interval(self):
        assert try_parse_interval("bad", default=7) == 7


class TestTrailheadAndImport:
    def test_trailhead_descriptor(self):
        result = parse_trailhead_descriptor("Yosemite Valley | bright indirect | 55%")
        assert result["name"] == "Yosemite Valley"
        assert result["difficulty"] == "moderate"

    def test_import_row(self):
        row = parse_import_row(["Ridge Trail", "mist-loop", "Kitchen", "7d", "note"])
        assert row["name"] == "Ridge Trail"
        assert row["visit_interval"] == "7d"

    def test_import_row_too_short(self):
        with pytest.raises(ValueError):
            parse_import_row(["only"])


class TestMisc:
    def test_normalize_trail_name(self):
        assert normalize_trail_name("  Half Dome   Deliciosa  ") == "Half Dome Deliciosa"

    def test_parse_interval_range(self):
        assert parse_interval_range("5-7d") == (5, 7)

    def test_parse_datetime_iso(self):
        dt = parse_datetime("2024-06-01T14:30:00")
        assert dt.year == 2024 and dt.hour == 14

    def test_parse_soil_ph_range(self):
        assert parse_soil_ph_range("6.0-7.0") == (6.0, 7.0)

    def test_parse_trail_list(self):
        assert parse_trail_list("A\nB\nC") == ["A", "B", "C"]

    def test_reminder_offset(self):
        assert parse_reminder_offset("1d") == 86400

    def test_growth_rate(self):
        assert parse_growth_rate("slow grower") == "slow"

    def test_misting_frequency(self):
        assert parse_misting_frequency("3d") == 3

    def test_coerce_light_list(self):
        assert coerce_light_list("low, medium") == ["low", "medium"]

    def test_normalize_enum(self):
        allowed = {"ok": "okay", "good": "okay"}
        assert normalize_enum("OK", allowed) == "okay"

    def test_care_frequency(self):
        result = parse_care_frequency("water:7d,fertilize:4w")
        assert result["water"] == 7
        assert result["fertilize"] == 28

    def test_format_conditions(self):
        assert format_conditions(55.5) == "56%"

    def test_format_temperature_f(self):
        assert "°F" in format_temperature_c(0.0, use_f=True)

    def test_format_health_status(self):
        assert format_health_status("struggling") == "Struggling"

    def test_tokenize_search_query(self):
        assert tokenize_search_query("  Half Dome  green  ") == ["half", "dome", "green"]
