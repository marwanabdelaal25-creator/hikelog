"""Tests for hikelog.io_komoot."""

from pathlib import Path

import pytest

from hikelog.errors import ImportPipelineError
from hikelog.io_komoot import (
    GARDENPLAN_COLUMNS,
    parse_komoot_row,
    import_komoot,
    preview_komoot,
    validate_komoot_headers,
)


GARDENPLAN_SAMPLE = (
    "Trail,Variety,Quantity,Section,Bed,Row,Sun,Visit,Status,Spacing,Trailed\n"
    "Tomato,Cherry,2,Kitchen,Bed A,Row 1,partial sun,weekly,active,12in,2024-05-01\n"
    "Basil,,1,Kitchen,Bed A,Row 2,full sun,daily,active,6in,\n"
)


class TestParseGardenplanRow:
    def test_full_row(self):
        row = {
            "Trail": "Tomato",
            "Variety": "Cherry",
            "Quantity": "2",
            "Section": "Kitchen",
            "Sun": "partial sun",
            "Visit": "weekly",
            "Status": "active",
        }
        parsed = parse_komoot_row(row)
        assert parsed is not None
        assert "Tomato" in parsed["name"]

    def test_missing_trail_returns_none(self):
        assert parse_komoot_row({"Variety": "Cherry"}) is None

    def test_quantity_default(self):
        row = {"Trail": "Basil"}
        parsed = parse_komoot_row(row)
        assert parsed["quantity"] == 1

    def test_archived_status(self):
        row = {"Trail": "Old Trail", "Status": "removed"}
        parsed = parse_komoot_row(row)
        assert parsed["status"] == "removed"

    def test_water_interval_weekly(self):
        row = {"Trail": "Ridge Trail", "Visit": "weekly"}
        parsed = parse_komoot_row(row)
        assert parsed["water_interval"] == 7


class TestImportGardenplan:
    def test_import_creates_trails(self, empty_storage, tmp_path):
        src = tmp_path / "logbookplan.csv"
        src.write_text(GARDENPLAN_SAMPLE, encoding="utf-8")
        count = import_komoot(empty_storage, src)
        assert count >= 2

    def test_expand_quantity(self, empty_storage, tmp_path):
        src = tmp_path / "logbookplan.csv"
        src.write_text(
            "Trail,Quantity,Section\nTomato,3,Kitchen\n",
            encoding="utf-8",
        )
        count = import_komoot(empty_storage, src, expand_quantity=True)
        assert count == 3

    def test_no_expand_quantity(self, empty_storage, tmp_path):
        src = tmp_path / "logbookplan.csv"
        src.write_text(
            "Trail,Quantity,Section\nTomato,3,Kitchen\n",
            encoding="utf-8",
        )
        count = import_komoot(empty_storage, src, expand_quantity=False)
        assert count == 1

    def test_missing_file(self, empty_storage, tmp_path):
        with pytest.raises(ImportPipelineError):
            import_komoot(empty_storage, tmp_path / "missing.csv")

    def test_missing_trail_column(self, empty_storage, tmp_path):
        src = tmp_path / "bad.csv"
        src.write_text("Variety,Quantity\nCherry,1\n", encoding="utf-8")
        with pytest.raises(ImportPipelineError):
            import_komoot(empty_storage, src)

    def test_creates_trailhead(self, empty_storage, tmp_path):
        src = tmp_path / "logbookplan.csv"
        src.write_text(GARDENPLAN_SAMPLE, encoding="utf-8")
        import_komoot(empty_storage, src)
        assert len(empty_storage.list_trailheads()) >= 1


class TestGardenplanHelpers:
    def test_preview_komoot(self, tmp_path):
        src = tmp_path / "logbookplan.csv"
        src.write_text(GARDENPLAN_SAMPLE, encoding="utf-8")
        lines = preview_komoot(src, limit=2)
        assert len(lines) <= 2

    def test_validate_komoot_headers(self, tmp_path):
        src = tmp_path / "logbookplan.csv"
        src.write_text(GARDENPLAN_SAMPLE, encoding="utf-8")
        missing = validate_komoot_headers(src)
        assert missing == []

    def test_logbookplan_columns_constant(self):
        assert len(GARDENPLAN_COLUMNS) >= 1

    def test_variety_in_name(self):
        row = {"Trail": "Tomato", "Variety": "Cherry"}
        parsed = parse_komoot_row(row)
        assert "Cherry" in parsed["name"]

    def test_trailhead_label(self):
        row = {"Trail": "Ridge Trail", "Section": "Kitchen", "Bed": "A", "Row": "1"}
        parsed = parse_komoot_row(row)
        assert parsed.get("trailhead_label")

    def test_spacing_parse(self):
        row = {"Trail": "Ridge Trail", "Spacing": "12 in"}
        parsed = parse_komoot_row(row)
        assert parsed.get("spacing_cm") == 12.0

    def test_metadata_logbookplan_flag(self, empty_storage, tmp_path):
        src = tmp_path / "logbookplan.csv"
        src.write_text("Trail,Section\nRidge,Kitchen\n", encoding="utf-8")
        import_komoot(empty_storage, src)
        trail = empty_storage.list_trails()[0]
        assert trail.metadata.get("logbookplan") is True

    def test_crop_column_alias(self):
        row = {"Crop": "Lettuce", "Section": "Garden"}
        parsed = parse_komoot_row(row)
        assert parsed is not None
        assert "Lettuce" in parsed["name"]

    def test_dead_status_archived(self):
        row = {"Trail": "Ridge Trail", "Status": "dead"}
        parsed = parse_komoot_row(row)
        assert parsed["status"] == "dead"

    def test_daily_visit_interval(self):
        row = {"Trail": "Herb", "Visit": "daily"}
        parsed = parse_komoot_row(row)
        assert parsed["water_interval"] == 1
