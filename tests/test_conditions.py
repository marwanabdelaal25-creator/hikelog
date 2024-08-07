"""Tests for hikelog.conditions."""

import pytest

from hikelog.errors import NotFoundError, ValidationError
from hikelog.conditions import ConditionsLogger


class TestConditionsLogger:
    def test_log_reading(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        row = logger.log(sample_trailhead.id, 55.0, notes="Morning reading")
        assert row["percent"] == 55.0
        assert row["trailhead_id"] == sample_trailhead.id

    def test_percent_out_of_range_low(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        with pytest.raises(ValidationError):
            logger.log(sample_trailhead.id, -1)

    def test_percent_out_of_range_high(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        with pytest.raises(ValidationError):
            logger.log(sample_trailhead.id, 101)

    def test_unknown_trailhead(self, empty_storage):
        logger = ConditionsLogger(empty_storage)
        with pytest.raises(NotFoundError):
            logger.log("missing", 50.0)

    def test_list_for_trailhead(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        logger.log(sample_trailhead.id, 45.0)
        logger.log(sample_trailhead.id, 50.0)
        rows = logger.list_for_trailhead(sample_trailhead.id)
        assert len(rows) == 2
        assert rows[0]["recorded_at"] >= rows[1]["recorded_at"]

    def test_list_with_limit(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        for pct in (40, 45, 50):
            logger.log(sample_trailhead.id, pct)
        rows = logger.list_for_trailhead(sample_trailhead.id, limit=2)
        assert len(rows) == 2

    def test_latest(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        assert logger.latest(sample_trailhead.id) is None
        logger.log(sample_trailhead.id, 48.0)
        latest = logger.latest(sample_trailhead.id)
        assert latest["percent"] == 48.0

    def test_average(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        logger.log(sample_trailhead.id, 40.0)
        logger.log(sample_trailhead.id, 60.0)
        assert logger.average(sample_trailhead.id) == 50.0

    def test_average_no_data(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        assert logger.average(sample_trailhead.id) is None

    def test_summary_by_trailhead(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        logger.log(sample_trailhead.id, 45.0)
        summary = logger.summary_by_trailhead()
        assert sample_trailhead.id in summary
        assert summary[sample_trailhead.id]["trailhead_name"] == sample_trailhead.name

    def test_delete(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        row = logger.log(sample_trailhead.id, 55.0)
        logger.delete(row["id"])
        assert logger.latest(sample_trailhead.id) is None

    def test_delete_missing_raises(self, populated_storage):
        logger = ConditionsLogger(populated_storage)
        with pytest.raises(NotFoundError):
            logger.delete("missing")

    def test_source_stored(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        row = logger.log(sample_trailhead.id, 50.0, source="sensor")
        assert row["source"] == "sensor"

    def test_persist_survives_reload(self, populated_storage, sample_trailhead, tmp_logbook_path):
        logger = ConditionsLogger(populated_storage)
        logger.log(sample_trailhead.id, 42.0)
        reloaded = ConditionsLogger(populated_storage.__class__(tmp_logbook_path))
        assert reloaded.latest(sample_trailhead.id) is not None

    def test_bucket_constant(self):
        assert ConditionsLogger.BUCKET == "conditions_readings"

    def test_rounded_percent(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        row = logger.log(sample_trailhead.id, 55.55)
        assert row["percent"] == 55.5

    def test_multiple_trailheads_isolated(self, populated_storage, sample_trailhead):
        loc2 = populated_storage.create_trailhead({"id": "loc2", "name": "Kitchen"})
        logger = ConditionsLogger(populated_storage)
        logger.log(sample_trailhead.id, 45.0)
        logger.log(loc2.id, 60.0)
        assert len(logger.list_for_trailhead(sample_trailhead.id)) == 1

    def test_summary_null_latest_for_empty(self, populated_storage, sample_trailhead):
        logger = ConditionsLogger(populated_storage)
        summary = logger.summary_by_trailhead()
        assert summary[sample_trailhead.id]["latest_percent"] is None
