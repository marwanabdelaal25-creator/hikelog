"""Tests for hikelog.streaks."""

from datetime import datetime, timedelta, timezone

import pytest

from hikelog.errors import NotFoundError
from hikelog.streaks import StreakInfo, StreakTracker


class TestStreakInfo:
    def test_dataclass_fields(self):
        info = StreakInfo(
            trail_id="p1",
            trail_name="Ridge Trail",
            current_streak=3,
            longest_streak=5,
            on_schedule=True,
            last_visited="2024-06-01",
        )
        assert info.current_streak == 3


class TestStreakTracker:
    def test_compute_no_events(self, populated_storage, sample_trail2):
        tracker = StreakTracker(populated_storage)
        populated_storage.mutate(lambda d: d.update({"visit_events": []}))
        info = tracker.compute(sample_trail2.id)
        assert info.current_streak == 0
        assert info.on_schedule is False

    def test_compute_with_events(self, populated_storage, sample_trail):
        tracker = StreakTracker(populated_storage)
        info = tracker.compute(sample_trail.id)
        assert info.trail_id == sample_trail.id

    def test_compute_not_found(self, empty_storage):
        tracker = StreakTracker(empty_storage)
        with pytest.raises(NotFoundError):
            tracker.compute("missing")

    def test_leaderboard(self, populated_storage):
        tracker = StreakTracker(populated_storage)
        board = tracker.leaderboard(limit=5)
        assert isinstance(board, list)

    def test_broken_streaks(self, populated_storage, sample_trail):
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        populated_storage.update_trail(sample_trail.id, {"last_visited_at": old_date})
        tracker = StreakTracker(populated_storage)
        broken = tracker.broken_streaks()
        assert isinstance(broken, list)

    def test_longest_streak_multiple_events(self, populated_storage, sample_trail):
        tracker = StreakTracker(populated_storage)
        info = tracker.compute(sample_trail.id)
        assert info.longest_streak >= info.current_streak

    def test_on_schedule_recent_water(self, populated_storage, sample_trail):
        tracker = StreakTracker(populated_storage)
        info = tracker.compute(sample_trail.id)
        assert info.last_visited is not None

    def test_leaderboard_respects_limit(self, populated_storage):
        tracker = StreakTracker(populated_storage)
        board = tracker.leaderboard(limit=1)
        assert len(board) <= 1

    def test_grace_days_constant(self):
        assert StreakTracker.GRACE_DAYS == 1.5

    def test_season_calendar_optional(self, populated_storage):
        from hikelog.seasons import SeasonCalendar
        tracker = StreakTracker(populated_storage, seasons=SeasonCalendar())
        info = tracker.compute("trail001")
        assert info.trail_name

    def test_two_events_within_gap(self, empty_storage, sample_trail):
        empty_storage.create_trail(sample_trail)
        today = datetime.now(timezone.utc)
        for days_ago in (7, 0):
            empty_storage.create_visit_event({
                "id": f"we_{days_ago}",
                "trail_id": sample_trail.id,
                "visited_at": (today - timedelta(days=days_ago)).isoformat(),
                "distance_km": 200,
            })
        tracker = StreakTracker(empty_storage)
        info = tracker.compute(sample_trail.id)
        assert info.current_streak >= 1
