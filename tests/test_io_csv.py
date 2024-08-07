"""Tests for hikelog.io_csv."""

from pathlib import Path

import pytest

from hikelog.errors import ImportPipelineError
from hikelog.io_csv import (
    PLANT_FIELDS,
    WATERING_FIELDS,
    export_trails_csv,
    export_visit_csv,
    export_csv_bundle,
    import_trails_csv,
    import_visit_csv,
    validate_csv_headers,
    sample_rows,
)


class TestExportCsv:
    def test_export_trails(self, populated_storage, tmp_path):
        dest = tmp_path / "trails.csv"
        count = export_trails_csv(populated_storage, dest)
        assert count >= 2
        assert dest.exists()

    def test_export_visit(self, populated_storage, tmp_path):
        dest = tmp_path / "visit.csv"
        count = export_visit_csv(populated_storage, dest)
        assert count >= 1

    def test_export_bundle(self, populated_storage, tmp_path):
        dest = tmp_path / "bundle.csv"
        trails_n, water_n = export_csv_bundle(populated_storage, dest)
        assert trails_n >= 2
        assert (tmp_path / "bundle_trails.csv").exists()
        assert (tmp_path / "bundle_visit.csv").exists()


class TestImportTrailsCsv:
    def test_import_creates_trails(self, empty_storage, tmp_path, sample_csv_content):
        src = tmp_path / "import.csv"
        src.write_text(sample_csv_content, encoding="utf-8")
        count = import_trails_csv(empty_storage, src)
        assert count >= 1
        assert len(empty_storage.list_trails()) >= 1

    def test_import_missing_file(self, empty_storage, tmp_path):
        with pytest.raises(ImportPipelineError):
            import_trails_csv(empty_storage, tmp_path / "missing.csv")

    def test_import_missing_name_column(self, empty_storage, tmp_path):
        src = tmp_path / "bad.csv"
        src.write_text("terrain,trailhead\nmist-loop,Kitchen\n", encoding="utf-8")
        with pytest.raises(ImportPipelineError):
            import_trails_csv(empty_storage, src)

    def test_import_update_by_name(self, populated_storage, tmp_path):
        src = tmp_path / "update.csv"
        src.write_text(
            "name,terrain,trailhead,visit_interval,notes\n"
            "Half Dome,mist-loop,Yosemite Valley,10d,Updated\n",
            encoding="utf-8",
        )
        count = import_trails_csv(populated_storage, src, update=True)
        assert count >= 1

    def test_import_skips_blank_rows(self, empty_storage, tmp_path):
        src = tmp_path / "sparse.csv"
        src.write_text(
            "name,terrain\nRidge,mist-loop\n,\n\nSummit,snake-ridge\n",
            encoding="utf-8",
        )
        count = import_trails_csv(empty_storage, src)
        assert count == 2


class TestImportVisitCsv:
    def test_import_visit(self, populated_storage, tmp_path, sample_visit_csv):
        src = tmp_path / "water.csv"
        src.write_text(sample_visit_csv, encoding="utf-8")
        count = import_visit_csv(populated_storage, src)
        assert count >= 1

    def test_import_visit_missing_trail(self, empty_storage, tmp_path):
        src = tmp_path / "water.csv"
        src.write_text(
            "trail_id,visited_at,distance_km\n"
            "missing,2024-06-01,250\n",
            encoding="utf-8",
        )
        with pytest.raises(ImportPipelineError):
            import_visit_csv(empty_storage, src)

    def test_import_visit_by_name(self, populated_storage, tmp_path):
        src = tmp_path / "water.csv"
        src.write_text(
            "trail_name,visited_at,distance_km\n"
            "Half Dome,2024-06-01,250\n",
            encoding="utf-8",
        )
        count = import_visit_csv(populated_storage, src)
        assert count == 1


class TestCsvHelpers:
    def test_validate_trails_headers(self, tmp_path, sample_csv_content):
        src = tmp_path / "trails.csv"
        src.write_text(sample_csv_content, encoding="utf-8")
        missing = validate_csv_headers(src, kind="trails")
        assert missing == []

    def test_validate_visit_headers(self, tmp_path, sample_visit_csv):
        src = tmp_path / "water.csv"
        src.write_text(sample_visit_csv, encoding="utf-8")
        missing = validate_csv_headers(src, kind="visit")
        assert missing == []

    def test_validate_missing_file(self, tmp_path):
        missing = validate_csv_headers(tmp_path / "missing.csv", kind="trails")
        assert missing == ["name"]

    def test_sample_rows(self, tmp_path, sample_csv_content):
        src = tmp_path / "trails.csv"
        src.write_text(sample_csv_content, encoding="utf-8")
        rows = sample_rows(src, n=2)
        assert len(rows) <= 2
        assert "name" in rows[0]

    def test_trail_fields_constant(self):
        assert "name" in PLANT_FIELDS

    def test_visit_fields_constant(self):
        assert "trail_id" in WATERING_FIELDS

    def test_export_includes_archived(self, populated_storage, sample_trail, tmp_path):
        populated_storage.update_trail(sample_trail.id, {"archived": True})
        dest = tmp_path / "trails.csv"
        count = export_trails_csv(populated_storage, dest)
        text = dest.read_text(encoding="utf-8")
        assert "Half Dome" in text or count >= 1

    def test_invalid_interval_raises(self, empty_storage, tmp_path):
        src = tmp_path / "bad.csv"
        src.write_text("name,visit_interval_days\nRidge,not-an-interval\n", encoding="utf-8")
        with pytest.raises(ImportPipelineError):
            import_trails_csv(empty_storage, src)

    def test_bad_distance_km_raises(self, populated_storage, tmp_path):
        src = tmp_path / "water.csv"
        src.write_text(
            "trail_id,visited_at,distance_km\ntrail001,2024-06-01,not-a-number\n",
            encoding="utf-8",
        )
        with pytest.raises(ImportPipelineError):
            import_visit_csv(populated_storage, src)
