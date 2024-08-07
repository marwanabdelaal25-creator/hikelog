"""Tests for hikelog.validators."""

from datetime import date, timedelta

import pytest

from hikelog.errors import ValidationError
from hikelog.validators import (
    require_non_empty,
    validate_trail_name,
    validate_nickname,
    validate_slug,
    validate_interval_days,
    validate_interval_range,
    validate_elevation_gain_m,
    validate_conditions_range,
    validate_difficulty,
    validate_distance_km,
    validate_pack_diameter,
    validate_pack_material,
    validate_visit_method,
    validate_temperature_c,
    validate_ph,
    validate_health_score,
    validate_id,
    validate_uuidish,
    validate_tag_name,
    validate_note_body,
    validate_acquired_date,
    validate_last_visited,
    validate_id_list,
    validate_dict_keys,
    clamp_int,
    clamp_float,
    validate_room_name,
    validate_trailhead_zone,
    validate_terrain_key,
    validate_gear_interval_weeks,
    validate_care_event_type,
    validate_color_hex,
    validate_metadata,
    validate_optional_url,
    validate_drainage,
    validate_soil_ph_preference,
    chk_positive_int,
    ensure_unique_names,
    validate_visit_notes,
    validate_batch_size,
    validate_season_name,
    validate_health_status,
    validate_amount_range,
    validate_list_not_empty,
    soft_validate_conditions,
    validate_export_format,
    validate_care_product,
    validate_duration_minutes,
    validate_floor,
    validate_source,
    validate_priority,
    validate_reminder_days,
    validate_window_direction,
    validate_soil_components,
    validate_visit_pace,
    validate_note_kind,
    batch_validate_trails,
)


class TestRequireNonEmpty:
    def test_valid(self):
        assert require_non_empty("hello", "field") == "hello"

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            require_non_empty("", "field")


class TestTrailName:
    def test_valid_name(self):
        assert validate_trail_name("Half Dome") == "Half Dome"

    def test_too_short_raises(self):
        with pytest.raises(ValidationError):
            validate_trail_name("X")


class TestNickname:
    def test_none_returns_none(self):
        assert validate_nickname(None) is None

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_nickname("x" * 50)


class TestSlug:
    def test_valid_slug(self):
        assert validate_slug("mist-loop") == "mist-loop"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            validate_slug("BAD SLUG!")


class TestIntervals:
    def test_valid_days(self):
        assert validate_interval_days(7) == 7

    def test_zero_raises(self):
        with pytest.raises(ValidationError):
            validate_interval_days(0)

    def test_range_valid(self):
        assert validate_interval_range(5, 10) == (5, 10)

    def test_range_inverted_raises(self):
        with pytest.raises(ValidationError):
            validate_interval_range(10, 5)


class TestConditions:
    def test_valid_pct(self):
        assert validate_elevation_gain_m(55.0) == 55.0

    def test_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            validate_elevation_gain_m(150)

    def test_range_valid(self):
        assert validate_conditions_range(40, 60) == (40.0, 60.0)


class TestLightAndWater:
    def test_difficulty(self):
        assert validate_difficulty("moderate") == "moderate"

    def test_bad_light_raises(self):
        with pytest.raises(ValidationError):
            validate_difficulty("supernova")

    def test_water_amount(self):
        assert validate_distance_km(250.0) == 250.0

    def test_zero_amount_raises(self):
        with pytest.raises(ValidationError):
            validate_distance_km(0)

    def test_visit_method(self):
        assert validate_visit_method("foot_trail") == "foot_trail"


class TestPackAndTemp:
    def test_pack_diameter(self):
        assert validate_pack_diameter(6.0) == 6.0

    def test_pack_material(self):
        assert validate_pack_material("ceramic") == "ceramic"

    def test_temperature(self):
        assert validate_temperature_c(22.0) == 22.0

    def test_ph(self):
        assert validate_ph(6.5) == 6.5


class TestHealthAndId:
    def test_health_score(self):
        assert validate_health_score(70) == 70

    def test_health_score_out_of_range(self):
        with pytest.raises(ValidationError):
            validate_health_score(101)

    def test_id(self):
        assert validate_id("trail001") == "trail001"

    def test_uuidish(self):
        assert validate_uuidish("abcdef12345678") == "abcdef12345678"


class TestTagsAndNotes:
    def test_tag_name(self):
        assert validate_tag_name("Beginner") == "beginner"

    def test_note_body(self):
        assert validate_note_body("Hello world") == "Hello world"


class TestDates:
    def test_acquired_date_future_raises(self):
        future = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError):
            validate_acquired_date(future)

    def test_last_visited_before_acquired(self):
        acquired = date.today() - timedelta(days=5)
        watered = date.today() - timedelta(days=10)
        with pytest.raises(ValidationError):
            validate_last_visited(watered, acquired)


class TestListsAndDicts:
    def test_id_list_dedupes(self):
        assert validate_id_list(["a", "a", "b"]) == ["a", "b"]

    def test_dict_keys_missing(self):
        with pytest.raises(ValidationError):
            validate_dict_keys({"a": 1}, ["a", "b"])


class TestClamp:
    def test_clamp_int(self):
        assert clamp_int(150, 0, 100) == 100

    def test_clamp_float(self):
        assert clamp_float(-5.0, 0.0, 100.0) == 0.0


class TestTrailheadFields:
    def test_room_name(self):
        assert validate_room_name("Yosemite Valley") == "Yosemite Valley"

    def test_zone(self):
        assert validate_trailhead_zone("main") == "main"


class TestTerrainAndCare:
    def test_terrain_key(self):
        assert validate_terrain_key("alpine-ridge") == "alpine-ridge"

    def test_gear_interval(self):
        assert validate_gear_interval_weeks(4) == 4

    def test_care_event_type(self):
        assert validate_care_event_type("fertilize") == "fertilize"


class TestColorAndMetadata:
    def test_color_hex(self):
        assert validate_color_hex("#4caf50") == "#4caf50"

    def test_bad_color_raises(self):
        with pytest.raises(ValidationError):
            validate_color_hex("red")

    def test_metadata_none(self):
        assert validate_metadata(None) == {}


class TestUrlAndDrainage:
    def test_optional_url(self):
        assert validate_optional_url("https://example.com/img.jpg") == "https://example.com/img.jpg"

    def test_drainage_default(self):
        assert validate_drainage(None) is True


class TestSoilPh:
    def test_soil_ph_preference(self):
        assert validate_soil_ph_preference(6.0, 7.0) == (6.0, 7.0)


class TestMiscValidators:
    def test_chk_positive_int(self):
        assert chk_positive_int(5, "field") == 5

    def test_ensure_unique_names(self):
        assert ensure_unique_names(["A", "B"]) == ["A", "B"]

    def test_duplicate_names_raises(self):
        with pytest.raises(ValidationError):
            ensure_unique_names(["A", "a"])

    def test_visit_notes(self):
        assert validate_visit_notes(None) == ""

    def test_batch_size(self):
        assert validate_batch_size(50) == 50

    def test_season_name(self):
        assert validate_season_name("summer") == "summer"

    def test_health_status(self):
        assert validate_health_status("thriving") == "thriving"

    def test_amount_range(self):
        assert validate_amount_range(100, 500) == (100.0, 500.0)

    def test_list_not_empty(self):
        assert validate_list_not_empty([1], "items") == [1]

    def test_soft_validate_conditions(self):
        assert soft_validate_conditions(150) == 100.0

    def test_export_format(self):
        assert validate_export_format("csv") == "csv"

    def test_care_product(self):
        assert validate_care_product("10-10-10") == "10-10-10"

    def test_duration_minutes(self):
        assert validate_duration_minutes(30) == 30

    def test_floor(self):
        assert validate_floor("2nd") == "2nd"

    def test_source_permissive(self):
        assert validate_source("unknown") == "manual"

    def test_priority(self):
        assert validate_priority(5) == 5

    def test_reminder_days(self):
        assert validate_reminder_days(7) == 7

    def test_window_direction(self):
        assert validate_window_direction("south") == "south"

    def test_soil_components(self):
        assert validate_soil_components(["peat", "perlite"]) == ["peat", "perlite"]

    def test_visit_pace(self):
        assert validate_visit_pace("filtered") == "filtered"

    def test_note_kind(self):
        assert validate_note_kind("hazard") == "hazard"

    def test_batch_validate_trails(self):
        assert batch_validate_trails(["Ridge Trail", "Aloe"]) == ["Ridge Trail", "Aloe"]
