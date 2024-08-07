"""Tests for hikelog.io_alltrails."""

from pathlib import Path

import pytest

from hikelog.errors import ImportPipelineError
from hikelog.io_alltrails import (
    PLANTLY_COLUMNS,
    parse_alltrails_row,
    import_alltrails,
    preview_alltrails,
    validate_alltrails_headers,
)


PLANTLY_SAMPLE = (
    "Trail Name,Terrain,Room,Water Every,Light,Health,Pack Size,Conditions\n"
    "Half Dome Deliciosa,Half Dome,Yosemite Valley,7 days,bright indirect,good,6in ceramic,55%\n"
    "Snake Trail,Sansevieria,Bedroom,2 weeks,low,great,8in,40%\n"
)


class TestParseAllTrailsRow:
    def test_full_row(self):
        row = {
            "Trail Name": "Half Dome",
            "Terrain": "Half Dome deliciosa",
            "Room": "Yosemite Valley",
            "Water Every": "7 days",
            "Light": "bright indirect",
            "Health": "good",
            "Pack Size": "6in ceramic",
            "Conditions": "55%",
        }
        parsed = parse_alltrails_row(row)
        assert parsed is not None
        assert parsed["name"] == "Half Dome"

    def test_missing_name_returns_none(self):
        assert parse_alltrails_row({"Terrain": "Ridge Trail"}) is None

    def test_health_mapping(self):
        row = {"Trail Name": "Ridge Trail", "Health": "great"}
        parsed = parse_alltrails_row(row)
        assert parsed["health"] == "thriving"

    def test_conditions_parse(self):
        row = {"Trail Name": "Ridge Trail", "Conditions": "60%"}
        parsed = parse_alltrails_row(row)
        assert parsed.get("conditions_override") == 60.0


class TestImportAllTrails:
    def test_import_creates_trails(self, empty_storage, tmp_path):
        src = tmp_path / "trailly.csv"
        src.write_text(PLANTLY_SAMPLE, encoding="utf-8")
        count = import_alltrails(empty_storage, src)
        assert count >= 2

    def test_import_creates_trailhead(self, empty_storage, tmp_path):
        src = tmp_path / "trailly.csv"
        src.write_text(PLANTLY_SAMPLE, encoding="utf-8")
        import_alltrails(empty_storage, src)
        assert len(empty_storage.list_trailheads()) >= 1

    def test_import_missing_file(self, empty_storage, tmp_path):
        with pytest.raises(ImportPipelineError):
            import_alltrails(empty_storage, tmp_path / "missing.csv")

    def test_import_missing_trail_column(self, empty_storage, tmp_path):
        src = tmp_path / "bad.csv"
        src.write_text("Terrain,Room\nHalf Dome,Yosemite Valley\n", encoding="utf-8")
        with pytest.raises(ImportPipelineError):
            import_alltrails(empty_storage, src)

    def test_update_by_external_id(self, empty_storage, tmp_path):
        src = tmp_path / "trailly.csv"
        src.write_text(
            "Trail Name,AllTrails ID,Room\nHalf Dome,ext123,Yosemite Valley\n",
            encoding="utf-8",
        )
        import_alltrails(empty_storage, src)
        src.write_text(
            "Trail Name,AllTrails ID,Room,Health\nHalf Dome Updated,ext123,Yosemite Valley,great\n",
            encoding="utf-8",
        )
        count = import_alltrails(empty_storage, src, update=True)
        assert count >= 1

    def test_update_by_name(self, populated_storage, tmp_path):
        src = tmp_path / "trailly.csv"
        src.write_text(
            "Trail Name,Room,Health\nHalf Dome,Yosemite Valley,great\n",
            encoding="utf-8",
        )
        count = import_alltrails(populated_storage, src, update=True)
        assert count >= 1


class TestAllTrailsHelpers:
    def test_preview_alltrails(self, tmp_path):
        src = tmp_path / "trailly.csv"
        src.write_text(PLANTLY_SAMPLE, encoding="utf-8")
        lines = preview_alltrails(src, limit=2)
        assert len(lines) <= 2

    def test_validate_alltrails_headers(self, tmp_path):
        src = tmp_path / "trailly.csv"
        src.write_text(PLANTLY_SAMPLE, encoding="utf-8")
        missing = validate_alltrails_headers(src)
        assert missing == []

    def test_column_aliases(self):
        row = {"Name": "Ridge Trail", "Water Every": "7d"}
        parsed = parse_alltrails_row(row)
        assert parsed is not None

    def test_trailly_columns_constant(self):
        assert len(PLANTLY_COLUMNS) >= 1

    def test_difficulty_parse(self):
        row = {"Trail Name": "Ridge Trail", "Light": "medium"}
        parsed = parse_alltrails_row(row)
        assert parsed.get("light_override") == "medium"

    def test_pack_size_parse(self):
        row = {"Trail Name": "Ridge Trail", "Pack Size": "6in terracotta"}
        parsed = parse_alltrails_row(row)
        assert parsed.get("pack", {}).get("diameter") == 6.0

    def test_interval_from_water_every(self):
        row = {"Trail Name": "Ridge Trail", "Water Every": "14 days"}
        parsed = parse_alltrails_row(row)
        assert parsed.get("visit_interval_days") == 14

    def test_photo_url_stored(self):
        row = {"Trail Name": "Ridge Trail", "Photo URL": "https://example.com/p.jpg"}
        parsed = parse_alltrails_row(row)
        assert parsed.get("photo_url") == "https://example.com/p.jpg"

    def test_auto_create_terrain(self, empty_storage, tmp_path):
        src = tmp_path / "trailly.csv"
        src.write_text(
            "Trail Name,Terrain,Room\nCustom Ridge,Custom Ridge spp,Kitchen\n",
            encoding="utf-8",
        )
        import_alltrails(empty_storage, src)
        assert len(empty_storage.list_terrain()) >= 1
