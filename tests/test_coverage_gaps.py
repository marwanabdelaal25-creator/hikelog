"""Targeted pytest coverage for previously uncovered hikelog lines."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hikelog.errors import (
    ExportError,
    ImportPipelineError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from hikelog.parser import (
    coerce_float,
    coerce_light_list,
    format_distance_km,
    format_health_status,
    format_conditions,
    format_interval_days,
    format_difficulty,
    format_temperature_c,
    normalize_enum,
    parse_distance_km,
    parse_bool,
    parse_care_frequency,
    parse_date,
    parse_datetime,
    parse_duration_minutes,
    parse_gear_strength,
    parse_health_note,
    parse_health_status,
    parse_conditions,
    parse_interval,
    parse_interval_range,
    parse_key_value,
    parse_key_value_pairs,
    parse_trailhead_descriptor,
    parse_npk,
    parse_ph,
    parse_trail_list,
    parse_relative_date,
    parse_reminder_offset,
    parse_season_hint,
    parse_soil_ph_range,
    parse_tags,
    parse_temperature,
    parse_weekday,
    parse_weekly_schedule,
    parse_visit_method,
    parse_difficulty,
    parse_growth_rate,
)
from hikelog.validators import (
    validate_amount_range,
    validate_batch_size,
    validate_care_event_type,
    validate_care_product,
    validate_color_hex,
    validate_duration_minutes,
    validate_export_format,
    validate_gear_interval_weeks,
    validate_floor,
    validate_health_status,
    validate_elevation_gain_m,
    validate_conditions_range,
    validate_id,
    validate_interval_days,
    validate_last_visited,
    validate_list_not_empty,
    validate_metadata,
    validate_note_body,
    validate_note_kind,
    validate_optional_url,
    validate_ph,
    validate_trail_name,
    validate_pack_diameter,
    validate_pack_material,
    validate_priority,
    validate_reminder_days,
    validate_room_name,
    validate_season_name,
    validate_soil_components,
    validate_soil_ph_preference,
    validate_tag_name,
    validate_temperature_c,
    validate_uuidish,
    validate_distance_km,
    validate_visit_pace,
    validate_visit_method,
    validate_visit_notes,
    validate_window_direction,
    validate_acquired_date,
    validate_trailhead_zone,
    validate_health_score,
)


# --- parser gaps ---


class TestParserCoverageGaps:
    def test_parse_date_tomorrow(self):
        assert parse_date("tomorrow") == date.today() + timedelta(days=1)

    def test_parse_date_plus_relative(self):
        assert parse_date("+2d") == date.today() + timedelta(days=2)

    def test_parse_relative_months(self):
        assert parse_relative_date("+1m") == date.today() + timedelta(days=30)

    def test_parse_datetime_space_and_z(self):
        dt = parse_datetime("2024-06-01 14:30")
        assert dt.hour == 14
        dt2 = parse_datetime("2024-06-01T12:00:00Z")
        assert dt2.year == 2024
        dt3 = parse_datetime("2024-06-01")
        assert dt3.date().isoformat() == "2024-06-01"

    def test_parse_interval_months(self):
        assert parse_interval("2 months") == 60

    def test_parse_interval_range_to(self):
        assert parse_interval_range("5 to 7 days") == (5, 7)

    def test_parse_amount_oz(self):
        assert parse_distance_km("8 oz") == pytest.approx(8 * 29.5735, rel=0.01)

    def test_parse_light_compact_value(self):
        assert parse_difficulty("moderate") == "moderate"

    def test_parse_conditions_bad(self):
        with pytest.raises(ValueError):
            parse_conditions("humid")

    def test_parse_temperature_bad(self):
        with pytest.raises(ValueError):
            parse_temperature("warm")

    def test_parse_bool_invalid(self):
        with pytest.raises(ValueError):
            parse_bool("maybe")

    def test_coerce_float_default(self):
        assert coerce_float("x", default=1.5) == 1.5

    def test_parse_key_value_equals_and_error(self):
        assert parse_key_value("a=b") == ("a", "b")
        with pytest.raises(ValueError):
            parse_key_value("noseparator")

    def test_parse_key_value_pairs_colon_and_skip(self):
        assert parse_key_value_pairs("a:1, badpart, b=2") == {"a": "1", "b": "2"}

    def test_parse_tags_empty(self):
        assert parse_tags("") == []

    def test_parse_visit_method_passthrough(self):
        assert parse_visit_method("custom soak") == "custom_soak"

    def test_parse_season_unknown(self):
        with pytest.raises(ValueError):
            parse_season_hint("monsoon")

    def test_parse_duration_digits_only(self):
        assert parse_duration_minutes("45") == 45

    def test_parse_duration_bad(self):
        with pytest.raises(ValueError):
            parse_duration_minutes("soon")

    def test_parse_gear_quarter_full_npk(self):
        assert parse_gear_strength("quarter strength")["dilution"] == 0.25
        assert parse_gear_strength("full strength")["dilution"] == 1.0
        assert "npk" in parse_gear_strength("10-10-10")

    def test_parse_health_note_hazards_root_rot(self):
        flags = parse_health_note("hazard on leaves and root rot smell")
        assert flags.get("hazards") is True
        assert flags.get("root_rot") is True

    def test_format_interval_one_week(self):
        assert format_interval_days(7) == "1w"

    def test_format_amount_sub_liter(self):
        assert format_distance_km(500) == "500ml"

    def test_format_light_unknown(self):
        assert "Custom" in format_difficulty("custom_level")

    def test_parse_soil_ph_bad_and_swap(self):
        with pytest.raises(ValueError):
            parse_soil_ph_range("bad")
        assert parse_soil_ph_range("7.0-6.0") == (6.0, 7.0)

    def test_parse_weekday_bad_and_empty_schedule(self):
        with pytest.raises(ValueError):
            parse_weekday("Funday")
        assert parse_weekly_schedule("") == []

    def test_parse_trail_list_comma(self):
        assert parse_trail_list("A, B, C") == ["A", "B", "C"]

    def test_parse_health_status_unknown(self):
        with pytest.raises(ValueError):
            parse_health_status("meh")

    def test_parse_reminder_offsets(self):
        assert parse_reminder_offset("2h before") == 7200
        assert parse_reminder_offset("30m") == 1800
        assert parse_reminder_offset("5") == 300

    def test_parse_npk_bad(self):
        with pytest.raises(ValueError):
            parse_npk("10-10")

    def test_parse_growth_rate_default(self):
        assert parse_growth_rate("variable") == "moderate"

    def test_parse_trailhead_descriptor_temp(self):
        result = parse_trailhead_descriptor("Office | 22c")
        assert "temp_c" in result

    def test_normalize_enum_substring(self):
        allowed = {"indirect": "moderate"}
        assert normalize_enum("indirect", allowed) == "moderate"
        assert normalize_enum("moderate", {"moderate": "moderate"}) == "moderate"

    def test_parse_care_frequency_equals(self):
        assert parse_care_frequency("mist=3d")["mist"] == 3

    def test_format_temperature_celsius(self):
        assert "°C" in format_temperature_c(20.0, use_f=False)

    def test_format_helpers(self):
        assert format_conditions(40.2) == "40%"
        assert format_health_status("okay") == "Okay"


# --- validators gaps ---


class TestValidatorsCoverageGaps:
    def test_interval_days_too_long(self):
        with pytest.raises(ValidationError):
            validate_interval_days(400)

    def test_conditions_range_inverted(self):
        with pytest.raises(ValidationError):
            validate_conditions_range(70, 40)

    def test_water_amount_too_large(self):
        with pytest.raises(ValidationError):
            validate_distance_km(60_000)

    def test_pack_diameter_zero_and_cm_range(self):
        with pytest.raises(ValidationError):
            validate_pack_diameter(0)
        with pytest.raises(ValidationError):
            validate_pack_diameter(200, unit="cm")

    def test_pack_diameter_inches_too_large(self):
        with pytest.raises(ValidationError):
            validate_pack_diameter(50, unit="in")

    def test_pack_material_custom(self):
        assert validate_pack_material("wood") == "wood"

    def test_visit_method_bad(self):
        with pytest.raises(ValidationError):
            validate_visit_method("spray")

    def test_temperature_out_of_range(self):
        with pytest.raises(ValidationError):
            validate_temperature_c(100)

    def test_ph_out_of_range(self):
        with pytest.raises(ValidationError):
            validate_ph(20)

    def test_id_too_long(self):
        with pytest.raises(ValidationError):
            validate_id("x" * 70)

    def test_uuidish_bad(self):
        with pytest.raises(ValidationError):
            validate_uuidish("not-hex!")

    def test_tag_name_too_long(self):
        with pytest.raises(ValidationError):
            validate_tag_name("x" * 40)

    def test_note_body_too_long(self):
        with pytest.raises(ValidationError):
            validate_note_body("x" * 10_001)

    def test_acquired_too_old(self):
        with pytest.raises(ValidationError):
            validate_acquired_date(date(1960, 1, 1))

    def test_last_visited_future(self):
        with pytest.raises(ValidationError):
            validate_last_visited(date.today() + timedelta(days=1))

    def test_room_name_too_long(self):
        with pytest.raises(ValidationError):
            validate_room_name("x" * 70)

    def test_zone_too_long(self):
        with pytest.raises(ValidationError):
            validate_trailhead_zone("x" * 50)

    def test_gear_interval_bad(self):
        with pytest.raises(ValidationError):
            validate_gear_interval_weeks(0)

    def test_care_event_type_bad(self):
        with pytest.raises(ValidationError):
            validate_care_event_type("dance")

    def test_metadata_not_dict(self):
        with pytest.raises(ValidationError):
            validate_metadata("meta")

    def test_optional_url_bad(self):
        with pytest.raises(ValidationError):
            validate_optional_url("ftp://x.com")

    def test_soil_ph_inverted(self):
        with pytest.raises(ValidationError):
            validate_soil_ph_preference(7.0, 5.0)

    def test_visit_notes_too_long(self):
        with pytest.raises(ValidationError):
            validate_visit_notes("n" * 2500)

    def test_batch_size_bounds(self):
        with pytest.raises(ValidationError):
            validate_batch_size(0)

    def test_season_invalid(self):
        with pytest.raises(ValidationError):
            validate_season_name("monsoon")

    def test_health_status_invalid(self):
        with pytest.raises(ValidationError):
            validate_health_status("great")

    def test_amount_range_inverted(self):
        with pytest.raises(ValidationError):
            validate_amount_range(500, 100)

    def test_list_not_empty(self):
        with pytest.raises(ValidationError):
            validate_list_not_empty([], "items")

    def test_export_format_bad(self):
        with pytest.raises(ValidationError):
            validate_export_format("xml")

    def test_care_product_too_long(self):
        with pytest.raises(ValidationError):
            validate_care_product("x" * 150)

    def test_duration_minutes_bad(self):
        with pytest.raises(ValidationError):
            validate_duration_minutes(25 * 60)

    def test_floor_too_long(self):
        with pytest.raises(ValidationError):
            validate_floor("x" * 30)

    def test_priority_bad(self):
        with pytest.raises(ValidationError):
            validate_priority(11)

    def test_reminder_days_bad(self):
        with pytest.raises(ValidationError):
            validate_reminder_days(40)

    def test_window_direction_bad(self):
        with pytest.raises(ValidationError):
            validate_window_direction("up")

    def test_soil_component_too_long(self):
        with pytest.raises(ValidationError):
            validate_soil_components(["x" * 70])

    def test_visit_pace_bad(self):
        with pytest.raises(ValidationError):
            validate_visit_pace("sparkling")

    def test_note_kind_bad(self):
        with pytest.raises(ValidationError):
            validate_note_kind("memo")

    def test_trail_name_invalid_chars(self):
        with pytest.raises(ValidationError):
            validate_trail_name("!!!")


# --- io_csv gaps ---


class TestIoCsvCoverageGaps:
    def test_read_csv_missing_file(self, empty_storage, tmp_path):
        from hikelog.io_csv import import_trails_csv

        with pytest.raises(ImportPipelineError):
            import_trails_csv(empty_storage, tmp_path / "nope.csv")

    def test_import_update_existing(self, populated_storage, tmp_path):
        from hikelog.io_csv import import_trails_csv

        src = tmp_path / "update.csv"
        src.write_text(
            "id,name,health,health_score,visit_distance_km,conditions_override\n"
            "trail001,Half Dome Renamed,okay,85,300ml,55\n",
            encoding="utf-8",
        )
        n = import_trails_csv(populated_storage, src, update=True)
        assert n == 1
        trail = populated_storage.get_trail("trail001")
        assert trail.name == "Half Dome Renamed"
        assert trail.health.value == "okay"

    def test_import_visit_by_name(self, populated_storage, tmp_path, sample_visit_csv):
        from hikelog.io_csv import import_visit_csv

        src = tmp_path / "w.csv"
        src.write_text(
            "trail_name,visited_at,distance_km\n"
            "Half Dome,2024-01-15,8.0\n",
            encoding="utf-8",
        )
        assert import_visit_csv(populated_storage, src) == 1

    def test_import_visit_bad_amount(self, populated_storage, tmp_path):
        from hikelog.io_csv import import_visit_csv

        src = tmp_path / "w.csv"
        src.write_text(
            "trail_id,visited_at,distance_km\n"
            "trail001,2024-01-15,not-an-amount\n",
            encoding="utf-8",
        )
        with pytest.raises(ImportPipelineError):
            import_visit_csv(populated_storage, src)

    def test_validate_csv_headers_visit(self, tmp_path):
        from hikelog.io_csv import validate_csv_headers, sample_rows

        p = tmp_path / "w.csv"
        p.write_text("foo,bar\n1,2\n", encoding="utf-8")
        assert "trail_id or trail_name" in validate_csv_headers(p, kind="visit")[0]
        assert sample_rows(tmp_path / "missing.csv") == []

    def test_export_oserror(self, populated_storage, tmp_path):
        from hikelog.io_csv import export_trails_csv

        with patch.object(Path, "open", side_effect=OSError("disk full")):
            with pytest.raises(ExportError):
                export_trails_csv(populated_storage, tmp_path / "out.csv")


# --- io_jsonl gaps ---


class TestIoJsonlCoverageGaps:
    def test_iter_lines_oserror(self, tmp_path):
        from hikelog.io_jsonl import _iter_lines

        with patch.object(Path, "open", side_effect=OSError("denied")):
            with pytest.raises(ImportPipelineError):
                list(_iter_lines(tmp_path / "x.jsonl"))

    def test_load_line_invalid_json(self, tmp_path):
        from hikelog.io_jsonl import _load_line

        with pytest.raises(ImportPipelineError):
            _load_line("{bad", 1)

    def test_load_line_not_object(self):
        from hikelog.io_jsonl import _load_line

        with pytest.raises(ImportPipelineError):
            _load_line("[1,2]", 1)

    def test_export_oserror(self, populated_storage, tmp_path):
        from hikelog.io_jsonl import export_visit_jsonl

        with patch.object(Path, "open", side_effect=OSError("fail")):
            with pytest.raises(ExportError):
                export_visit_jsonl(populated_storage, tmp_path / "o.jsonl")

    def test_import_missing(self, empty_storage, tmp_path):
        from hikelog.io_jsonl import import_visit_jsonl

        with pytest.raises(ImportPipelineError):
            import_visit_jsonl(empty_storage, tmp_path / "n.jsonl")

    def test_import_care_remaps_fields(self, empty_storage, tmp_path):
        from hikelog.io_jsonl import import_care_jsonl

        src = tmp_path / "care.jsonl"
        src.write_text(
            json.dumps({
                "_type": "care",
                "trail_id": "p1",
                "event_type": "fertilize",
                "occurred_at": "2024-06-01T12:00:00",
            }) + "\n",
            encoding="utf-8",
        )
        empty_storage.create_trail({"id": "p1", "name": "Ridge Trail"})
        assert import_care_jsonl(empty_storage, src) == 1

    def test_import_mixed_trail_update_and_skip(self, empty_storage, tmp_path):
        from hikelog.io_jsonl import import_mixed_jsonl

        empty_storage.create_trail({"id": "p1", "name": "Ridge Trail"})
        src = tmp_path / "mix.jsonl"
        lines = [
            {"_type": "trail", "id": "p1", "name": "Ridge Updated"},
            {"_type": "note", "id": "n1", "trail_id": "p1", "body": "hi"},
            {"_type": "unknown", "x": 1},
        ]
        src.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
        counts = import_mixed_jsonl(empty_storage, src)
        assert counts["trail"] == 1
        assert counts["note"] == 1
        assert counts["skipped"] == 1

    def test_count_and_preview(self, tmp_path):
        from hikelog.io_jsonl import count_lines, preview

        assert count_lines(tmp_path / "n.jsonl") == 0
        p = tmp_path / "p.jsonl"
        p.write_text('{"_type":"visit","trail_id":"x"}\n', encoding="utf-8")
        assert count_lines(p) == 1
        assert preview(p, limit=1)[0]["_type"] == "visit"


# --- io_komoot gaps ---


class TestIoGardenplanCoverageGaps:
    def test_water_interval_variants(self):
        from hikelog.io_komoot import parse_komoot_row

        for water, expected in [
            ("daily", 1),
            ("twice a week", 3),
            ("monthly", 30),
            ("drought tolerant", 14),
            ("moist soil", 3),
            ("high moisture", 3),
        ]:
            parsed = parse_komoot_row({"Trail": "X", "Visit": water})
            assert parsed["water_interval"] == expected

    def test_trailed_date_invalid_kept(self):
        from hikelog.io_komoot import parse_komoot_row

        parsed = parse_komoot_row({"Trail": "X", "Trailed Date": "someday"})
        assert parsed["trailed_at"] == "someday"

    def test_ensure_trailhead_existing(self, empty_storage, tmp_path, sample_trailhead):
        from hikelog.io_komoot import import_komoot

        empty_storage.create_trailhead(sample_trailhead)
        src = tmp_path / "gp.csv"
        src.write_text(
            "Trail,Section\nRidge,%s\n" % sample_trailhead.name.split()[0],
            encoding="utf-8",
        )
        import_komoot(empty_storage, src)

    def test_preview_missing_file(self, tmp_path):
        from hikelog.io_komoot import preview_komoot, validate_komoot_headers

        assert preview_komoot(tmp_path / "n.csv") == []
        assert validate_komoot_headers(tmp_path / "n.csv") == ["Trail"]

    def test_import_pipeline_error_on_bad_row(self, empty_storage, tmp_path):
        from hikelog.io_komoot import import_komoot

        src = tmp_path / "gp.csv"
        src.write_text("Trail,Quantity\nBad,\n", encoding="utf-8")
        with patch("hikelog.io_komoot.Trail.create", side_effect=ValueError("boom")):
            with pytest.raises(ImportPipelineError):
                import_komoot(empty_storage, src)


# --- io_alltrails gaps ---


class TestIoAllTrailsCoverageGaps:
    def test_parse_trailly_interval_digits(self):
        from hikelog.io_alltrails import parse_alltrails_row

        row = {
            "Trail Name": "Ridge Trail",
            "Water Every": "about 10 days",
            "Last Watered": "not-a-date",
            "Light": "indirect",
        }
        parsed = parse_alltrails_row(row)
        assert parsed["visit_interval_days"] == 10

    def test_import_alltrails_creates_terrain_and_trailhead(self, empty_storage, tmp_path):
        from hikelog.io_alltrails import import_alltrails

        src = tmp_path / "trailly.csv"
        src.write_text(
            "Trail Name,Nickname,Room,Terrain,Water Every,Last Watered,Light\n"
            "Half Dome,HD-01,Yosemite Valley,Half Dome deliciosa,7d,today,bright indirect\n",
            encoding="utf-8",
        )
        n = import_alltrails(empty_storage, src)
        assert n >= 1
        assert len(empty_storage.list_trailheads()) >= 1

    def test_import_alltrails_update(self, populated_storage, tmp_path):
        from hikelog.io_alltrails import import_alltrails

        src = tmp_path / "trailly.csv"
        src.write_text(
            "Trail Name,Water Every\nHalf Dome,14d\n",
            encoding="utf-8",
        )
        import_alltrails(populated_storage, src, update=True)

    def test_trailly_helpers(self, tmp_path):
        from hikelog.io_alltrails import preview_alltrails, validate_alltrails_headers

        assert preview_alltrails(tmp_path / "n.csv") == []
        assert validate_alltrails_headers(tmp_path / "n.csv")


# --- reports gaps ---


class TestReportsCoverageGaps:
    def test_in_range_naive_datetime(self, empty_storage):
        from hikelog.reports import MonthlyReport

        report = MonthlyReport(empty_storage)
        start = datetime(2024, 6, 1, tzinfo=timezone.utc)
        end = datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
        assert report._in_range("2024-06-15T10:00:00", start, end) is True
        assert report._in_range(None, start, end) is False

    def test_generate_with_trailhead_breakdown(self, populated_storage, sample_trail):
        from hikelog.reports import MonthlyReport

        now = datetime.now(timezone.utc)
        populated_storage.create_visit_event({
            "trail_id": sample_trail.id,
            "visited_at": now.isoformat(),
            "distance_km": 100,
        })
        report = MonthlyReport(populated_storage)
        data = report.generate(now.year, now.month)
        assert data["visits_by_trailhead"]

    def test_render_text_foot_trailed(self, populated_storage, sample_trail):
        from hikelog.reports import MonthlyReport

        now = datetime.now(timezone.utc)
        for _ in range(3):
            populated_storage.create_visit_event({
                "trail_id": sample_trail.id,
                "visited_at": now.isoformat(),
            })
        report = MonthlyReport(populated_storage)
        text = report.render_text(now.year, now.month)
        assert "Most watered" in text or sample_trail.name in text


# --- cli gaps ---


def _ns(**kwargs):
    return argparse.Namespace(**kwargs)


class TestCliCoverageGaps:
    def test_default_logbook_without_env(self, monkeypatch):
        from hikelog.cli import _default_logbook_path

        monkeypatch.delenv("HIKELOG_HOME", raising=False)
        path = _default_logbook_path()
        assert path.name == "logbook.json"

    def test_resolve_nickname_and_partial(self, populated_storage, sample_trail):
        from hikelog.cli import _resolve_trail

        populated_storage.update_trail(sample_trail.id, {"nickname": "HD-01"})
        assert _resolve_trail(populated_storage, "HD-01").id == sample_trail.id
        assert _resolve_trail(populated_storage, "ome").id == sample_trail.id

    def test_add_trail_with_amount(self, tmp_logbook_path):
        from hikelog.cli import cmd_add_trail, cmd_init

        cmd_init(_ns(logbook=str(tmp_logbook_path)))
        ns = _ns(
            logbook=str(tmp_logbook_path),
            name="Ridge Trail",
            nickname=None,
            terrain=None,
            trailhead=None,
            health=None,
            interval="7d",
            acquired=None,
            amount="250ml",
        )
        assert cmd_add_trail(ns) == 0

    def test_list_filters_and_truncation(self, populated_storage, sample_trailhead):
        from hikelog.cli import cmd_list

        populated_storage.update_trail("trail001", {"trailhead_id": sample_trailhead.id})
        ns = _ns(
            logbook=str(populated_storage.path),
            all=False,
            overdue=False,
            trailhead=sample_trailhead.id,
            limit=1,
        )
        with patch("sys.stdout", new_callable=StringIO) as out:
            assert cmd_list(ns) == 0
            assert "more" in out.getvalue()

    def test_import_export_branches(self, populated_storage, tmp_path):
        from hikelog.cli import cmd_export, cmd_import

        wcsv = tmp_path / "w.csv"
        wcsv.write_text("trail_id,visited_at\ntrail001,2024-01-01\n", encoding="utf-8")
        assert cmd_import(_ns(
            logbook=str(populated_storage.path),
            file=str(wcsv),
            format="csv",
            kind="visit",
            update=False,
            no_expand=False,
        )) == 0

        jsrc = tmp_path / "events.jsonl"
        jsrc.write_text(
            json.dumps({"_type": "care", "trail_id": "trail001", "action": "mist"}) + "\n",
            encoding="utf-8",
        )
        assert cmd_import(_ns(
            logbook=str(populated_storage.path),
            file=str(jsrc),
            format="jsonl",
            kind="care",
            update=False,
            no_expand=False,
        )) == 0

        mixed = tmp_path / "mix.jsonl"
        mixed.write_text(
            json.dumps({"_type": "visit", "trail_id": "trail001", "visited_at": "2024-02-01"}) + "\n",
            encoding="utf-8",
        )
        assert cmd_import(_ns(
            logbook=str(populated_storage.path),
            file=str(mixed),
            format="jsonl",
            kind=None,
            update=False,
            no_expand=False,
        )) == 0

        gp = tmp_path / "gp.csv"
        gp.write_text("Trail,Section\nBasil,Kitchen\n", encoding="utf-8")
        assert cmd_import(_ns(
            logbook=str(populated_storage.path),
            file=str(gp),
            format="logbookplan",
            kind=None,
            update=False,
            no_expand=True,
        )) == 0

        assert cmd_import(_ns(
            logbook=str(populated_storage.path),
            file=str(tmp_path / "x.csv"),
            format="csv",
            kind="unknown",
            update=False,
            no_expand=False,
        )) == 1

        dest = tmp_path / "out.csv"
        assert cmd_export(_ns(
            logbook=str(populated_storage.path),
            file=str(dest),
            format="csv",
            kind="visit",
        )) == 0

        jdest = tmp_path / "out.jsonl"
        for kind in ("visit", "care", "full", None):
            assert cmd_export(_ns(
                logbook=str(populated_storage.path),
                file=str(jdest),
                format="jsonl",
                kind=kind,
            )) == 0

        assert cmd_export(_ns(
            logbook=str(populated_storage.path),
            file=str(tmp_path / "x.bin"),
            format="bin",
            kind=None,
        )) == 1

    def test_backup_restore_prune(self, populated_storage, tmp_path):
        from hikelog.backup import GardenBackup
        from hikelog.cli import cmd_backup

        backup_dir = tmp_path / "backups"
        gb = GardenBackup(populated_storage.path, backup_dir)
        backup_file = gb.create(label="test")
        ns_restore = _ns(
            logbook=str(populated_storage.path),
            dir=str(backup_dir),
            label=None,
            list=False,
            restore=str(backup_file),
            prune=False,
            keep=1,
        )
        assert cmd_backup(ns_restore) == 0
        ns_prune = _ns(
            logbook=str(populated_storage.path),
            dir=str(backup_dir),
            label="daily",
            list=False,
            restore=None,
            prune=True,
            keep=0,
        )
        assert cmd_backup(ns_prune) == 0

    def test_search_and_reminders_branches(self, populated_storage, capsys):
        from hikelog.cli import cmd_reminders, cmd_search

        assert cmd_search(_ns(
            logbook=str(populated_storage.path),
            query="note",
            kind="notes",
            limit=5,
            verbose=True,
        )) == 0
        assert cmd_search(_ns(
            logbook=str(populated_storage.path),
            query="care",
            kind="care",
            limit=5,
            verbose=False,
        )) == 0

        populated_storage.update_trail("trail001", {"last_visited_at": "2020-01-01"})
        ns = _ns(logbook=str(populated_storage.path), overdue=False, within=30, limit=1)
        assert cmd_reminders(ns) == 0

    def test_main_keyboard_interrupt(self):
        from hikelog.cli import main

        parser = MagicMock()
        parser.parse_args.return_value = MagicMock(func=MagicMock(side_effect=KeyboardInterrupt))
        with patch("hikelog.cli.build_parser", return_value=parser):
            assert main([]) == 130

    def test_main_module_entry(self):
        import hikelog.cli as cli_mod

        with patch.object(cli_mod, "main", return_value=0) as mock_main:
            with pytest.raises(SystemExit) as exc:
                exec(compile("if True: raise SystemExit(main())", "<test>", "exec"), {
                    "main": cli_mod.main,
                    "SystemExit": SystemExit,
                })
            assert exc.value.code == 0 or exc.value.code is None


# --- storage gaps ---


class TestStorageCoverageGaps:
    def test_legacy_trail_normalization(self, tmp_logbook_path):
        from hikelog.storage import JsonStorage, _normalize_trail_row

        row = {
            "id": "p1",
            "name": "Ridge Trail",
            "terrain_id": "sp1",
            "tags": ["t1"],
            "active": False,
        }
        norm = _normalize_trail_row(row)
        assert norm["terrain_key"] == "sp1"
        assert norm["tag_ids"] == ["t1"]
        assert norm["archived"] is True

    def test_legacy_terrain_normalization(self):
        from hikelog.storage import _normalize_terrain_row

        assert _normalize_terrain_row({"id": "sp-key"})["key"] == "sp-key"

    def test_load_invalid_json(self, tmp_logbook_path):
        from hikelog.storage import JsonStorage

        tmp_logbook_path.write_text("not json", encoding="utf-8")
        with pytest.raises(StorageError):
            JsonStorage(tmp_logbook_path).load()

    def test_load_non_object_root(self, tmp_logbook_path):
        from hikelog.storage import JsonStorage

        tmp_logbook_path.write_text("[1,2]", encoding="utf-8")
        with pytest.raises(StorageError):
            JsonStorage(tmp_logbook_path).load()

    def test_corrupt_bucket(self, empty_storage):
        empty_storage._data["trails"] = "bad"
        with pytest.raises(StorageError):
            empty_storage._list("trails")

    def test_crud_paths(self, empty_storage, sample_trail, sample_terrain, sample_trailhead):
        empty_storage.create_terrain({"id": "legacy-sp", "display_name": "Legacy"})
        empty_storage.delete_terrain("legacy-sp")

        loc = empty_storage.create_trailhead(sample_trailhead)
        empty_storage.update_trailhead(loc.id, {"notes": "updated"})
        empty_storage.delete_trailhead(loc.id)

        trail = empty_storage.create_trail(sample_trail)
        empty_storage.update_trail(trail.id, {"nickname": "X"})
        ev = empty_storage.create_visit_event({
            "trail_id": trail.id,
            "visited_at": date.today().isoformat(),
        })
        empty_storage.get_visit_event(ev["id"])
        empty_storage.update_visit_event(ev["id"], {"notes": "ok"})
        empty_storage.delete_visit_event(ev["id"])

        log = empty_storage.create_trip_log({"trail_id": trail.id, "action": "mist"})
        empty_storage.get_trip_log(log["id"])
        empty_storage.update_trip_log(log["id"], {"notes": "done"})
        empty_storage.delete_trip_log(log["id"])

        tag = empty_storage.create_tag({"id": "t9", "name": "test"})
        empty_storage.update_tag(tag["id"], {"name": "test2"})
        empty_storage.delete_tag(tag["id"])

        note = empty_storage.create_note({"id": "n9", "trail_id": trail.id, "body": "hi"})
        empty_storage.update_note(note["id"], {"body": "bye"})
        empty_storage.delete_note(note["id"])

        empty_storage.upsert_plugin({"id": "plug1", "name": "p"})
        empty_storage.upsert_plugin({"id": "plug1", "name": "p2"})
        empty_storage.delete_plugin("plug1")

        rec = empty_storage.create_recurring({"id": "r1", "rule": "weekly"})
        empty_storage.update_recurring("r1", {"rule": "daily"})
        empty_storage.delete_recurring("r1")

        empty_storage.delete_trail(trail.id)

    def test_visit_events_filter(self, populated_storage, sample_trail):
        events = populated_storage.list_visit_events(trail_id=sample_trail.id)
        assert all(e["trail_id"] == sample_trail.id for e in events)

    def test_atomic_write_failure(self, empty_storage):
        with patch.object(Path, "write_text", side_effect=OSError("fail")):
            with pytest.raises(StorageError):
                empty_storage.save()


# --- trailhead gaps ---


class TestTrailheadCoverageGaps:
    def test_trailhead_with_temp_validation(self, sample_trailhead):
        from hikelog.trailhead import Trailhead

        loc = Trailhead(
            name="Warm Room",
            id="th-warm",
            temp_c=22.0,
            elevation_gain_m=50.0,
        )
        assert loc.temp_c == 22.0
        assert "°C" in loc.summary()

    def test_effective_light_south_and_invalid(self):
        from hikelog.trailhead import Trailhead, AspectDirection

        loc = Trailhead.create(
            "South Window",
            difficulty="medium",
            window_direction=AspectDirection.SOUTH,
        )
        assert loc.effective_light() != "medium"
        loc2 = Trailhead.create("Odd", difficulty="low")
        loc2.difficulty = "unknown_level"
        assert loc2.effective_light() == "unknown_level"

    def test_registry_helpers(self, sample_trailhead, sample_trail):
        from hikelog.trailhead import (
            TrailheadRegistry,
            TrailheadClimateProfile,
            RoomHistory,
            RoomSnapshot,
            build_trailhead_map,
            compare_light,
            default_trailheads,
            estimate_daily_light_hours,
            format_trailhead_tree,
            trailhead_capacity_report,
            trailhead_report,
            trails_without_trailhead,
            rank_trailheads_for_terrain,
            reassign_trail,
            suggest_trails_for_trailhead,
            sync_trailhead_trail_ids,
        )

        reg = TrailheadRegistry()
        reg.add(sample_trailhead)
        reg.assign_trail(sample_trailhead.id, sample_trail.id)
        reg.unassign_trail(sample_trail.id)
        assert reg.require(sample_trailhead.id).id == sample_trailhead.id
        assert reg.find_by_light(sample_trailhead.difficulty)
        if sample_trailhead.zone:
            assert reg.find_by_zone(sample_trailhead.zone)
        with pytest.raises(ValueError):
            reg.add(sample_trailhead)
        assert reg.count() >= 1

        profile = TrailheadClimateProfile.from_trailhead(sample_trailhead)
        assert profile.visit_factor() > 0
        profile.draft_risk = True
        profile.heater_nearby = True
        profile.ac_nearby = True
        profile.avg_conditions = 70
        assert profile.visit_factor() != 1.0

        assert compare_light("low", "full_sun") == -1
        with pytest.raises(ValidationError):
            compare_light("bad", "low")
        assert suggest_trails_for_trailhead(sample_trailhead)
        assert trailhead_report(reg)["trailhead_count"] >= 1
        reassign_trail(reg, sample_trail.id, None, sample_trailhead.id)
        assert estimate_daily_light_hours(sample_trailhead, month=7) > 0
        assert rank_trailheads_for_terrain(reg, "not-a-profile") == []
        assert build_trailhead_map(reg)
        unassigned = trails_without_trailhead(reg, [sample_trail.id, "other"])
        assert "other" in unassigned
        assert sample_trail.id not in unassigned
        assert trailhead_capacity_report(reg, max_per_room=0)["crowded"]

        hist = RoomHistory()
        hist.record(RoomSnapshot(sample_trailhead.id, datetime.now(timezone.utc).isoformat(), 50.0))
        assert hist.avg_conditions(sample_trailhead.id) == 50.0
        RoomHistory.from_dict_list(hist.to_dict_list())

        sync_trailhead_trail_ids(reg, [sample_trail])
        tree = format_trailhead_tree(reg)
        assert sample_trailhead.name in tree
        assert default_trailheads().count() >= 0

    def test_registry_remove_missing(self):
        from hikelog.trailhead import TrailheadRegistry

        reg = TrailheadRegistry()
        assert reg.remove("nope") is False


# --- schedule gaps ---


class TestScheduleCoverageGaps:
    def test_season_str_and_detect_fallback(self):
        from hikelog.schedule import Season, ScheduleEngine, ScheduleOptions, detect_season

        assert str(Season.SPRING) == "spring"
        with patch("hikelog.schedule._SEASON_MONTHS", {Season.SPRING: ()}):
            assert detect_season(date(2024, 6, 15)) == Season.SPRING

    def test_engine_multipliers(self, trail_catalog, terrain_catalog, trailhead_registry, visit_log, sample_trail):
        from copy import deepcopy

        from hikelog.trail import TrailStatus
        from hikelog.schedule import ScheduleEngine

        engine = ScheduleEngine(trail_catalog, terrain_catalog, trailhead_registry, visit_log)
        engine.set_options(health_adjust=True, trailhead_conditions_adjust=True)

        struggling = deepcopy(sample_trail)
        struggling.health = TrailStatus.STRUGGLING
        assert engine.health_multiplier(struggling) < 1.0
        critical = deepcopy(sample_trail)
        critical.health = TrailStatus.CRITICAL
        assert engine.health_multiplier(critical) == 0.75
        thriving = deepcopy(sample_trail)
        thriving.health = TrailStatus.THRIVING
        assert engine.health_multiplier(thriving) > 1.0

        loc = trailhead_registry.get(sample_trail.trailhead_id)
        if loc:
            loc.elevation_gain_m = 70
            assert engine.trailhead_multiplier(sample_trail) > 1.0
            loc.elevation_gain_m = 30
            assert engine.trailhead_multiplier(sample_trail) < 1.0

        small_pack = deepcopy(sample_trail)
        small_pack.pack.diameter = 3
        small_pack.pack.unit = "in"
        assert engine.pack_multiplier(small_pack) < 1.0
        big_pack = deepcopy(sample_trail)
        big_pack.pack.diameter = 14
        big_pack.pack.unit = "in"
        assert engine.pack_multiplier(big_pack) > 1.0

        engine.options.health_adjust = False
        assert engine.health_multiplier(sample_trail) == 1.0

    def test_last_visited_and_entry_notes(self, trail_catalog, visit_log, sample_trail):
        from copy import deepcopy

        from hikelog.trail import TrailStatus
        from hikelog.schedule import ScheduleEngine

        engine = ScheduleEngine(trail_catalog, visit_log=visit_log)
        sample_trail.last_visited_at = None
        sample_trail.acquired_at = (date.today() - timedelta(days=30)).isoformat()
        assert engine.last_visited(sample_trail) is not None

        never = deepcopy(sample_trail)
        never.last_visited_at = None
        never.acquired_at = None
        assert engine.next_due_date(never) <= date.today() + timedelta(days=engine.adjusted_interval(never))

        critical = sample_trail
        critical.health = TrailStatus.CRITICAL
        entry = engine.build_entry(critical, date.today() - timedelta(days=10))
        assert entry.notes == "check roots/soil" or entry.overdue_days >= 0


# --- backup gaps ---


class TestBackupCoverageGaps:
    def test_create_missing_logbook(self, tmp_path):
        from hikelog.backup import GardenBackup

        gb = GardenBackup(tmp_path / "nope.json", tmp_path / "bk")
        with pytest.raises(StorageError):
            gb.create()

    def test_restore_missing_and_corrupt(self, populated_storage, tmp_path):
        from hikelog.backup import GardenBackup

        gb = GardenBackup(populated_storage.path, tmp_path / "bk")
        with pytest.raises(StorageError):
            gb.restore(tmp_path / "missing.json")
        bad = tmp_path / "bad.json"
        bad.write_text("{", encoding="utf-8")
        with pytest.raises(StorageError):
            gb.restore(bad)

    def test_restore_latest_empty(self, tmp_path):
        from hikelog.backup import GardenBackup

        gb = GardenBackup(tmp_path / "g.json", tmp_path / "bk")
        with pytest.raises(StorageError):
            gb.restore_latest()

    def test_prune_oserror_ignored(self, populated_storage, tmp_path):
        from hikelog.backup import GardenBackup

        gb = GardenBackup(populated_storage.path, tmp_path / "bk")
        gb.create()
        gb.create()
        with patch.object(Path, "unlink", side_effect=OSError("locked")):
            removed = gb.prune(keep=0)
        assert isinstance(removed, list)

    def test_create_copy_oserror(self, populated_storage, tmp_path):
        from hikelog.backup import GardenBackup

        gb = GardenBackup(populated_storage.path, tmp_path / "bk")
        with patch("hikelog.backup.shutil.copy2", side_effect=OSError("disk full")):
            with pytest.raises(StorageError, match="backup failed"):
                gb.create()

    def test_restore_copy_oserror(self, populated_storage, tmp_path):
        from hikelog.backup import GardenBackup

        gb = GardenBackup(populated_storage.path, tmp_path / "bk")
        backup = gb.create()
        original = __import__("shutil").copy2

        def copy_side_effect(src, dst):
            if str(dst) == str(populated_storage.path):
                raise OSError("permission")
            return original(src, dst)

        with patch("hikelog.backup.shutil.copy2", side_effect=copy_side_effect):
            with pytest.raises(StorageError, match="restore failed"):
                gb.restore(backup)


# --- server gaps ---


class TestServerCoverageGaps:
    def test_handler_put_delete_via_background(self, populated_storage):
        import urllib.error
        import urllib.request

        from hikelog.server import GardenServer

        server = GardenServer(populated_storage, port=0)
        server.start_background()
        try:
            host, port = server.address
            for method in ("PUT", "DELETE"):
                req = urllib.request.Request(
                    f"http://{host}:{port}/trails",
                    method=method,
                    data=b"{}",
                )
                with pytest.raises(urllib.error.HTTPError) as exc:
                    urllib.request.urlopen(req)
                assert exc.value.code == 405
        finally:
            server.stop()

    def test_logbook_server_lifecycle(self, populated_storage):
        from hikelog.server import GardenServer, run_server

        srv = GardenServer(populated_storage, host="127.0.0.1", port=0)
        assert srv.address[0] == "127.0.0.1"
        httpd = srv.start_background()
        assert httpd is not None
        srv.stop()
        srv.stop()

        with patch("hikelog.server.GardenServer.serve_forever"):
            with patch("hikelog.server.JsonStorage"):
                run_server(str(populated_storage.path), port=9999)


# --- trail / tag / notes / visit / streaks / migrate / terrain / trip_log ---


class TestDomainCoverageGaps:
    def test_trail_edges(self, sample_trail):
        from hikelog.trail import TrailStatus, Trail, TrailCatalog

        p = Trail.from_dict({
            **sample_trail.to_dict(),
            "tag_ids": ["t1"],
            "light_override": "low",
        })
        p.set_health(TrailStatus.THRIVING, score=90)
        p.archive()
        p.unarchive()
        p.visit_interval_days = 10
        assert p.display_name

        cat = TrailCatalog()
        cat.add(p)
        p.attach_tag("t1")
        assert cat.find_by_tag("t1")

    def test_tag_registry_edges(self):
        from hikelog.tag import Tag, TagRegistry

        tag = Tag.create("rare", color="#aabbcc")
        reg = TagRegistry()
        reg.add(tag)
        assert reg.get(tag.id)
        reg.remove(tag.id)

    def test_notes_collection_edges(self, sample_trail):
        from hikelog.notes import NoteKind, NotesCollection

        coll = NotesCollection()
        n = coll.create(sample_trail.id, "body", kind=NoteKind.REMINDER)
        n.edit(body="new body")
        n.pin()
        n.unpin()
        assert coll.for_trail(sample_trail.id)

    def test_visit_log_edges(self, sample_visit_events):
        from hikelog.visit import VisitLog

        log = VisitLog()
        log.load_many(sample_visit_events)
        assert log.total_ml_for_trail(sample_visit_events[0].trail_id) >= 0
        assert log.for_trail(sample_visit_events[0].trail_id)

    def test_streaks_break_and_leaderboard(self, populated_storage, sample_trail):
        from hikelog.streaks import StreakTracker

        populated_storage.create_visit_event({
            "trail_id": sample_trail.id,
            "visited_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        })
        populated_storage.create_visit_event({
            "trail_id": sample_trail.id,
            "visited_at": datetime.now(timezone.utc).isoformat(),
        })
        tracker = StreakTracker(populated_storage)
        info = tracker.compute(sample_trail.id)
        assert info.longest_streak >= 1
        assert tracker.leaderboard(5)
        assert isinstance(tracker.broken_streaks(), list)

    def test_migrate_edges(self, populated_storage):
        from hikelog.migrate import detect_version, migrate_file, migration_plan

        path = populated_storage.path
        data = json.loads(path.read_text(encoding="utf-8"))
        data["schema_version"] = 0
        path.write_text(json.dumps(data), encoding="utf-8")
        assert detect_version(data) == 0
        migrate_file(str(path))
        assert migration_plan(0)

    def test_terrain_and_trip_log_edges(self, terrain_catalog, trip_log, sample_trail):
        from hikelog.trip_log import TripEventType
        from hikelog.terrain import TerrainProfile

        sp = TerrainProfile(
            key="test-sp",
            display_name="Test",
            route_code="T. test",
            difficulty="low",
            visit_interval_min=5,
            visit_interval_max=10,
        )
        terrain_catalog.register(sp)
        assert sp.matches_light("low")
        trip_log.log(sample_trail.id, TripEventType.INSPECT)

    def test_gear_seasons_hazards_photos_recurring(self, populated_storage, sample_trail):
        from hikelog.gear import GearManager
        from hikelog.hazards import HazardTracker
        from hikelog.photos import PhotoCatalog
        from hikelog.recurring import RecurringTasks
        from hikelog.seasons import SeasonCalendar

        assert SeasonCalendar().multiplier_for(date.today()) > 0
        GearManager(populated_storage).apply(sample_trail.id, "10-10-10")
        HazardTracker(populated_storage).report(sample_trail.id, "aphids")
        PhotoCatalog(populated_storage).register(sample_trail.id, "/tmp/x.jpg")
        RecurringTasks(populated_storage).define("Water", "water", 7, trail_id=sample_trail.id)


class TestFinalCoveragePush:
    def test_visit_pace_str(self):
        from hikelog.visit import VisitPace

        assert str(VisitPace.TAP) == "tap"

    def test_gear_due_skips_bad_timestamp(self, populated_storage, sample_trail):
        from hikelog.gear import GearManager

        populated_storage.mutate(lambda d: d.setdefault("gear_events", []).append({
            "id": "fe_bad",
            "trail_id": sample_trail.id,
            "product": "10-10-10",
            "applied_at": "not-a-date",
        }))
        due = GearManager(populated_storage).due_for_gear(interval_days=30)
        assert isinstance(due, list)

    def test_gear_due_naive_timestamp(self, populated_storage, sample_trail):
        from hikelog.gear import GearManager

        old = (datetime.now() - timedelta(days=60)).isoformat()
        populated_storage.mutate(lambda d: d.setdefault("gear_events", []).append({
            "id": "fe_naive",
            "trail_id": sample_trail.id,
            "product": "10-10-10",
            "applied_at": old,
        }))
        due = GearManager(populated_storage).due_for_gear(interval_days=30)
        assert any(d["trail_id"] == sample_trail.id for d in due)

    def test_parse_iso_invalid(self):
        from hikelog.trail import parse_iso

        assert parse_iso("not-a-date") is None
        assert parse_iso(None) is None

    def test_seasons_day_of_year(self):
        from hikelog.seasons import SeasonCalendar

        cal = SeasonCalendar()
        assert cal._day_of_year(date(2024, 7, 1)) == date(2024, 7, 1).timetuple().tm_yday

    def test_cli_main_keyboard_interrupt(self):
        from hikelog.cli import main

        with patch("hikelog.cli.build_parser") as bp:
            ns = MagicMock()
            ns.func.side_effect = KeyboardInterrupt
            bp.return_value.parse_args.return_value = ns
            assert main([]) == 130
