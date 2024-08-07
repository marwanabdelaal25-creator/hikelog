"""Tests for hikelog.visit."""

from datetime import date, timedelta

import pytest

from hikelog.visit import (
    VisitPace,
    VisitEvent,
    VisitLog,
    VisitBatch,
    log_batch_visit,
    weekly_visit_stats,
    trails_visited_on,
    export_visit_csv_rows,
    detect_visit_drift,
    visit_history_summary,
    compare_trails_distance,
    missed_visits_estimate,
    filter_events_by_method,
    VisitAnalytics,
    merge_visit_logs,
)


class TestVisitEvent:
    def test_create(self, sample_trail):
        ev = VisitEvent.create(sample_trail.id, distance_km=250.0)
        assert ev.trail_id == sample_trail.id

    def test_skip(self, sample_trail):
        ev = VisitEvent.skip(sample_trail.id, reason="travel")
        assert ev.skipped is True

    def test_visited_date(self, sample_trail):
        ev = VisitEvent.create(
            sample_trail.id,
            visited_at="2024-06-01",
        )
        assert ev.visited_date == date(2024, 6, 1)

    def test_to_dict_from_dict(self, sample_trail):
        ev = VisitEvent.create(sample_trail.id, distance_km=200.0)
        restored = VisitEvent.from_dict(ev.to_dict())
        assert restored.distance_km == 200.0

    def test_summary(self, sample_trail):
        ev = VisitEvent.create(sample_trail.id, distance_km=250.0)
        assert "250ml" in ev.summary()

    def test_skip_summary(self, sample_trail):
        ev = VisitEvent.skip(sample_trail.id, reason="vacation")
        assert "skipped" in ev.summary()


class TestVisitLog:
    def test_record_and_get(self, visit_log, sample_visit_events):
        assert visit_log.count() == 3

    def test_duplicate_raises(self, visit_log, sample_visit_events):
        with pytest.raises(ValueError):
            visit_log.record(sample_visit_events[0])

    def test_log_visit(self, sample_trail):
        log = VisitLog()
        ev = log.log_visit(sample_trail.id, distance_km=300.0)
        assert ev.distance_km == 300.0

    def test_for_trail(self, visit_log, sample_trail):
        events = visit_log.for_trail(sample_trail.id)
        assert len(events) == 2

    def test_last_for_trail(self, visit_log, sample_trail):
        last = visit_log.last_for_trail(sample_trail.id)
        assert last is not None
        assert not last.skipped

    def test_between(self, visit_log):
        start = date.today() - timedelta(days=30)
        end = date.today()
        events = visit_log.between(start, end)
        assert len(events) >= 1

    def test_total_ml_for_trail(self, visit_log, sample_trail):
        total = visit_log.total_ml_for_trail(sample_trail.id, days=30)
        assert total == 450.0

    def test_average_interval_days(self, visit_log, sample_trail):
        avg = visit_log.average_interval_days(sample_trail.id)
        assert avg == 7.0

    def test_count_for_trail(self, visit_log, sample_trail):
        assert visit_log.count_for_trail(sample_trail.id) == 2

    def test_remove_for_trail(self, visit_log, sample_trail):
        removed = visit_log.remove_for_trail(sample_trail.id)
        assert removed == 2

    def test_streak_days(self, visit_log, sample_trail):
        assert visit_log.streak_days(sample_trail.id) == 3

    def test_from_dict_list(self, sample_visit_events):
        log = VisitLog.from_dict_list([e.to_dict() for e in sample_visit_events])
        assert log.count() == 3


class TestBatchVisit:
    def test_log_batch_visit(self, sample_trail, sample_trail2):
        log = VisitLog()
        batch = log_batch_visit(
            log,
            {sample_trail.id: 250.0, sample_trail2.id: 150.0},
        )
        assert batch.total_ml == 400.0
        assert len(batch.event_ids) == 2


class TestVisitHelpers:
    def test_weekly_visit_stats(self, visit_log):
        stats = weekly_visit_stats(visit_log, weeks=4)
        assert "total_ml" in stats

    def test_trails_visited_on(self, visit_log):
        today = date.today()
        ids = trails_visited_on(visit_log, today - timedelta(days=3))
        assert isinstance(ids, list)

    def test_export_visit_csv_rows(self, visit_log):
        rows = export_visit_csv_rows(visit_log)
        assert rows[0][0] == "id"
        assert len(rows) > 1

    def test_detect_visit_drift(self, visit_log, sample_trail):
        result = detect_visit_drift(visit_log, sample_trail.id, 7)
        assert result["trail_id"] == sample_trail.id

    def test_detect_drift_not_enough_data(self, sample_trail):
        log = VisitLog()
        log.log_visit(sample_trail.id, distance_km=100.0)
        result = detect_visit_drift(log, sample_trail.id, 7)
        assert result["drift"] is None

    def test_visit_history_summary(self, visit_log, sample_trail):
        summary = visit_history_summary(visit_log, sample_trail.id)
        assert summary["count"] == 2

    def test_compare_trails_distance(self, visit_log, sample_trail, sample_trail2):
        rows = compare_trails_distance(
            visit_log, [sample_trail.id, sample_trail2.id]
        )
        assert len(rows) == 2

    def test_missed_visits_estimate(self, visit_log, sample_trail):
        count = missed_visits_estimate(visit_log, sample_trail.id, 7)
        assert count >= 0

    def test_filter_events_by_method(self, visit_log):
        events = filter_events_by_method(visit_log, "foot_trail")
        assert all(e.method == "foot_trail" for e in events)

    def test_merge_visit_logs(self, visit_log, sample_trail):
        other = VisitLog()
        other.log_visit(sample_trail.id, distance_km=100.0)
        merged = merge_visit_logs(visit_log, other)
        assert merged.count() > visit_log.count()


class TestVisitAnalytics:
    def test_report(self, visit_log):
        analytics = VisitAnalytics(visit_log)
        report = analytics.report()
        assert report["total_events"] == 3
        assert "busiest_day" in report

    def test_total_volume_ml(self, visit_log):
        analytics = VisitAnalytics(visit_log)
        assert analytics.total_volume_ml() > 0

    def test_skip_rate(self, visit_log):
        analytics = VisitAnalytics(visit_log)
        assert analytics.skip_rate() == 0.0

    def test_method_breakdown(self, visit_log):
        analytics = VisitAnalytics(visit_log)
        breakdown = analytics.method_breakdown()
        assert "foot_trail" in breakdown

    def test_avg_amount_by_trail(self, visit_log, sample_trail):
        analytics = VisitAnalytics(visit_log)
        avgs = analytics.avg_amount_by_trail()
        assert sample_trail.id in avgs
