"""Tests for hikelog.gear."""

from datetime import datetime, timedelta, timezone

import pytest

from hikelog.errors import NotFoundError, ValidationError
from hikelog.gear import GearManager


class TestGearManager:
    def test_apply(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        event = mgr.apply(sample_trail.id, "10-10-10", dilution="half")
        assert event["product"] == "10-10-10"
        assert event["trail_id"] == sample_trail.id

    def test_history(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        mgr.apply(sample_trail.id, "Fish emulsion")
        mgr.apply(sample_trail.id, "10-10-10")
        history = mgr.history(sample_trail.id)
        assert len(history) == 2

    def test_last_application(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        assert mgr.last_application(sample_trail.id) is None
        mgr.apply(sample_trail.id, "10-10-10")
        assert mgr.last_application(sample_trail.id) is not None

    def test_due_never_fertilized(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        due = mgr.due_for_gear(interval_days=30)
        trail_due = [d for d in due if d["trail_id"] == sample_trail.id]
        assert len(trail_due) >= 1
        assert trail_due[0]["reason"] == "never"

    def test_due_overdue(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        old = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        populated_storage.mutate(lambda d: d.setdefault("gear_events", []).append({
            "id": "fe1",
            "trail_id": sample_trail.id,
            "product": "10-10-10",
            "applied_at": old,
        }))
        due = mgr.due_for_gear(interval_days=30)
        trail_due = [d for d in due if d["trail_id"] == sample_trail.id]
        assert any(d.get("reason") == "overdue" for d in trail_due)

    def test_set_schedule(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        sched = mgr.set_schedule(sample_trail.id, interval_days=14)
        assert sched["metadata"]["gear_interval_days"] == 14

    def test_set_schedule_invalid_interval(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        with pytest.raises(ValidationError):
            mgr.set_schedule(sample_trail.id, interval_days=0)

    def test_delete_event(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        event = mgr.apply(sample_trail.id, "10-10-10")
        mgr.delete_event(event["id"])
        assert mgr.history(sample_trail.id) == []

    def test_delete_event_not_found(self, populated_storage):
        mgr = GearManager(populated_storage)
        with pytest.raises(NotFoundError):
            mgr.delete_event("missing")

    def test_unknown_trail_on_apply(self, empty_storage):
        mgr = GearManager(empty_storage)
        with pytest.raises(NotFoundError):
            mgr.apply("missing", "10-10-10")

    def test_custom_applied_at(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        ts = "2024-01-15T10:00:00+00:00"
        event = mgr.apply(sample_trail.id, "10-10-10", applied_at=ts)
        assert event["applied_at"] == ts

    def test_active_only_false(self, populated_storage, sample_trail):
        populated_storage.update_trail(sample_trail.id, {"archived": True})
        mgr = GearManager(populated_storage)
        due_active = mgr.due_for_gear(active_only=True)
        due_all = mgr.due_for_gear(active_only=False)
        assert len(due_all) >= len(due_active)

    def test_dilution_and_notes(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        event = mgr.apply(sample_trail.id, "10-10-10", dilution="quarter", notes="Monthly feed")
        assert event["dilution"] == "quarter"
        assert event["notes"] == "Monthly feed"

    def test_due_sorted_by_days_since(self, populated_storage, sample_trail, sample_trail2):
        mgr = GearManager(populated_storage)
        old = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        older = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        populated_storage.mutate(lambda d: d.setdefault("gear_events", []).extend([
            {
                "id": "fe_old",
                "trail_id": sample_trail.id,
                "product": "10-10-10",
                "applied_at": old,
            },
            {
                "id": "fe_older",
                "trail_id": sample_trail2.id,
                "product": "10-10-10",
                "applied_at": older,
            },
        ]))
        due = [d for d in mgr.due_for_gear(interval_days=30) if d.get("reason") == "overdue"]
        if len(due) >= 2:
            assert due[0]["days_since"] >= due[1]["days_since"]

    def test_interval_boundary_not_due(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        recent = datetime.now(timezone.utc).isoformat()
        mgr.apply(sample_trail.id, "10-10-10", applied_at=recent)
        due = mgr.due_for_gear(interval_days=30)
        trail_due = [d for d in due if d["trail_id"] == sample_trail.id]
        assert len(trail_due) == 0

    def test_history_sort_newest_first(self, populated_storage, sample_trail):
        mgr = GearManager(populated_storage)
        mgr.apply(sample_trail.id, "A", applied_at="2024-01-01T00:00:00+00:00")
        mgr.apply(sample_trail.id, "B", applied_at="2024-06-01T00:00:00+00:00")
        history = mgr.history(sample_trail.id)
        assert history[0]["product"] == "B"

    def test_set_schedule_metadata_merge(self, populated_storage, sample_trail):
        populated_storage.update_trail(sample_trail.id, {
            "metadata": {"gear_interval_days": 21},
        })
        mgr = GearManager(populated_storage)
        sched = mgr.set_schedule(sample_trail.id, interval_days=28)
        trail = populated_storage.get_trail(sample_trail.id)
        assert trail.metadata.get("gear_interval_days") == 28
