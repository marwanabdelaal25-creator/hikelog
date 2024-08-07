"""Tests for hikelog.trip_log."""

from datetime import date, timedelta

import pytest

from hikelog.trip_log import (
    TripEventType,
    TripEvent,
    GearSchedule,
    TripLog,
    RepackRecord,
    extract_repack_records,
    care_summary,
    log_repack,
    upcoming_care,
    merge_trip_logs,
    care_events_in_month,
    prune_history,
    fertilize_history,
    export_care_timeline,
    care_activity_heatmap,
)


class TestTripEvent:
    def test_create(self, sample_trail):
        ev = TripEvent.create(sample_trail.id, TripEventType.FERTILIZE, product="10-10-10")
        assert ev.event_type == TripEventType.FERTILIZE

    def test_occurred_date(self, sample_trail):
        ev = TripEvent.create(sample_trail.id, TripEventType.PRUNE, occurred_at="2024-06-01")
        assert ev.occurred_date == date(2024, 6, 1)

    def test_to_dict_from_dict(self, sample_trail):
        ev = TripEvent.create(sample_trail.id, TripEventType.MIST)
        restored = TripEvent.from_dict(ev.to_dict())
        assert restored.event_type == TripEventType.MIST

    def test_summary(self, sample_trail):
        ev = TripEvent.create(sample_trail.id, TripEventType.FERTILIZE, product="Fish emulsion")
        assert "Fertilize" in ev.summary()


class TestGearSchedule:
    def test_is_due_no_last(self, sample_trail):
        sched = GearSchedule(trail_id=sample_trail.id, interval_weeks=4)
        assert sched.is_due() is True

    def test_is_due_recent(self, sample_trail):
        sched = GearSchedule(
            trail_id=sample_trail.id,
            interval_weeks=4,
            last_fertilized_at=date.today().isoformat(),
        )
        assert sched.is_due() is False

    def test_to_dict_from_dict(self, sample_trail):
        sched = GearSchedule(trail_id=sample_trail.id)
        restored = GearSchedule.from_dict(sched.to_dict())
        assert restored.trail_id == sample_trail.id


class TestTripLog:
    def test_log_and_count(self, trip_log):
        assert trip_log.count() == 2

    def test_duplicate_raises(self, trip_log, sample_trail):
        ev = TripEvent.create(sample_trail.id, TripEventType.INSPECT, id="dup001")
        trip_log.record(ev)
        with pytest.raises(ValueError):
            trip_log.record(ev)

    def test_for_trail(self, trip_log, sample_trail):
        events = trip_log.for_trail(sample_trail.id)
        assert len(events) == 2

    def test_of_type(self, trip_log):
        fert = trip_log.of_type(TripEventType.FERTILIZE)
        assert len(fert) == 1

    def test_gear_schedule(self, trip_log, sample_trail):
        sched = trip_log.gear_schedule(sample_trail.id)
        assert sched is not None

    def test_due_gear(self, trip_log):
        due = trip_log.due_gear()
        assert len(due) >= 1

    def test_between(self, trip_log):
        start = date.today() - timedelta(days=30)
        events = trip_log.between(start, date.today())
        assert len(events) >= 1

    def test_count_by_type(self, trip_log):
        counts = trip_log.count_by_type()
        assert counts.get("fertilize") == 1

    def test_to_dict_from_dict(self, trip_log):
        restored = TripLog.from_dict(trip_log.to_dict())
        assert restored.count() == trip_log.count()

    def test_remove_for_trail(self, trip_log, sample_trail):
        removed = trip_log.remove_for_trail(sample_trail.id)
        assert removed == 2

    def test_fertilize_updates_schedule(self, sample_trail):
        log = TripLog()
        log.set_gear_schedule(GearSchedule(trail_id=sample_trail.id))
        log.log(sample_trail.id, TripEventType.FERTILIZE, product="10-10-10")
        sched = log.gear_schedule(sample_trail.id)
        assert sched.last_fertilized_at is not None

    def test_repack_sets_metadata(self, sample_trail):
        log = TripLog()
        log.log(sample_trail.id, TripEventType.REPOT)
        ev = log.last_repack(sample_trail.id)
        assert ev.metadata.get("repack") is True


class TestCareHelpers:
    def test_extract_repack_records(self, sample_trail):
        log = TripLog()
        log_repack(log, sample_trail.id, old_diameter=4.0, new_diameter=6.0)
        records = extract_repack_records(log)
        assert len(records) == 1
        assert isinstance(records[0], RepackRecord)

    def test_care_summary(self, trip_log, sample_trail):
        summary = care_summary(trip_log, sample_trail.id)
        assert summary["total_events"] == 2

    def test_log_repack(self, sample_trail):
        log = TripLog()
        ev = log_repack(log, sample_trail.id, old_diameter=4, new_diameter=6)
        assert ev.event_type == TripEventType.REPOT

    def test_upcoming_care(self, trip_log):
        upcoming = upcoming_care(trip_log)
        assert "gear_due" in upcoming

    def test_merge_trip_logs(self, trip_log, sample_trail):
        other = TripLog()
        other.log(sample_trail.id, TripEventType.ROTATE)
        merged = merge_trip_logs(trip_log, other)
        assert merged.count() >= 3

    def test_care_events_in_month(self, trip_log):
        today = date.today()
        events = care_events_in_month(trip_log, today.year, today.month)
        assert len(events) >= 1

    def test_prune_history(self, trip_log, sample_trail):
        history = prune_history(trip_log, sample_trail.id)
        assert len(history) == 1

    def test_fertilize_history(self, trip_log, sample_trail):
        history = fertilize_history(trip_log, sample_trail.id)
        assert len(history) == 1

    def test_export_care_timeline(self, trip_log, sample_trail):
        timeline = export_care_timeline(trip_log, sample_trail.id)
        assert len(timeline) == 2

    def test_care_activity_heatmap(self, trip_log):
        heatmap = care_activity_heatmap(trip_log, weeks=4)
        assert isinstance(heatmap, dict)
