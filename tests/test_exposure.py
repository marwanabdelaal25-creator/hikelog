"""Tests for hikelog.exposure."""

import pytest

from hikelog.errors import NotFoundError, ValidationError
from hikelog.exposure import ExposureLogger, VALID_LEVELS


class TestExposureLogger:
    def test_log_with_trail(self, populated_storage, sample_trail):
        logger = ExposureLogger(populated_storage)
        row = logger.log(trail_id=sample_trail.id, level="bright", hours=6.0)
        assert row["trail_id"] == sample_trail.id

    def test_log_with_trailhead(self, populated_storage, sample_trailhead):
        logger = ExposureLogger(populated_storage)
        row = logger.log(trailhead_id=sample_trailhead.id, level="medium")
        assert row["trailhead_id"] == sample_trailhead.id

    def test_neither_id_raises(self, populated_storage):
        logger = ExposureLogger(populated_storage)
        with pytest.raises(ValidationError):
            logger.log(level="medium")

    def test_invalid_level_raises(self, populated_storage, sample_trail):
        logger = ExposureLogger(populated_storage)
        with pytest.raises(ValidationError):
            logger.log(trail_id=sample_trail.id, level="supernova")

    def test_level_normalized(self, populated_storage, sample_trail):
        logger = ExposureLogger(populated_storage)
        row = logger.log(trail_id=sample_trail.id, level="MEDIUM")
        assert row["level"] == "medium"

    def test_unknown_trail_raises(self, empty_storage):
        logger = ExposureLogger(empty_storage)
        with pytest.raises(NotFoundError):
            logger.log(trail_id="missing", level="low")

    def test_for_trail(self, populated_storage, sample_trail):
        logger = ExposureLogger(populated_storage)
        logger.log(trail_id=sample_trail.id, level="low")
        logger.log(trail_id=sample_trail.id, level="medium")
        rows = logger.for_trail(sample_trail.id)
        assert len(rows) == 2

    def test_for_trailhead(self, populated_storage, sample_trailhead):
        logger = ExposureLogger(populated_storage)
        logger.log(trailhead_id=sample_trailhead.id, level="bright")
        rows = logger.for_trailhead(sample_trailhead.id)
        assert len(rows) == 1

    def test_latest_for_trail(self, populated_storage, sample_trail):
        logger = ExposureLogger(populated_storage)
        assert logger.latest_for_trail(sample_trail.id) is None
        logger.log(trail_id=sample_trail.id, level="low")
        assert logger.latest_for_trail(sample_trail.id) is not None

    def test_delete(self, populated_storage, sample_trail):
        logger = ExposureLogger(populated_storage)
        row = logger.log(trail_id=sample_trail.id, level="low")
        logger.delete(row["id"])
        assert logger.latest_for_trail(sample_trail.id) is None

    def test_delete_missing_raises(self, populated_storage):
        logger = ExposureLogger(populated_storage)
        with pytest.raises(NotFoundError):
            logger.delete("missing")

    @pytest.mark.parametrize("level", list(VALID_LEVELS))
    def test_all_valid_levels(self, populated_storage, sample_trail, level):
        logger = ExposureLogger(populated_storage)
        row = logger.log(trail_id=sample_trail.id, level=level)
        assert row["level"] == level

    def test_hours_optional(self, populated_storage, sample_trail):
        logger = ExposureLogger(populated_storage)
        row = logger.log(trail_id=sample_trail.id, level="medium")
        assert row.get("hours") is None

    def test_notes_persisted(self, populated_storage, sample_trail):
        logger = ExposureLogger(populated_storage)
        row = logger.log(trail_id=sample_trail.id, level="low", notes="Cloudy day")
        assert row["notes"] == "Cloudy day"

    def test_both_ids(self, populated_storage, sample_trail, sample_trailhead):
        logger = ExposureLogger(populated_storage)
        row = logger.log(
            trail_id=sample_trail.id,
            trailhead_id=sample_trailhead.id,
            level="direct",
        )
        assert row["trail_id"] == sample_trail.id

    def test_trailhead_only_excluded_from_for_trail(self, populated_storage, sample_trailhead):
        logger = ExposureLogger(populated_storage)
        logger.log(trailhead_id=sample_trailhead.id, level="medium")
        assert logger.for_trail("any") == []

    def test_observed_at_present(self, populated_storage, sample_trail):
        logger = ExposureLogger(populated_storage)
        row = logger.log(trail_id=sample_trail.id, level="low")
        assert "observed_at" in row

    def test_valid_levels_constant(self):
        assert "medium" in VALID_LEVELS
        assert "direct" in VALID_LEVELS
