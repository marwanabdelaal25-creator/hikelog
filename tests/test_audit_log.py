"""Tests for hikelog.audit_log."""

from hikelog.audit_log import AuditLog


class TestAuditLog:
    def test_record(self, empty_storage):
        audit = AuditLog(empty_storage)
        entry = audit.record("create", "trail", "p1", details={"name": "Ridge Trail"})
        assert entry["action"] == "create"
        assert entry["entity_id"] == "p1"

    def test_default_actor(self, empty_storage):
        audit = AuditLog(empty_storage)
        entry = audit.record("update", "trail", "p1")
        assert entry["actor"] == "local"

    def test_list_entries(self, empty_storage):
        audit = AuditLog(empty_storage)
        audit.record("create", "trail", "p1")
        audit.record("water", "trail", "p1")
        entries = audit.list_entries()
        assert len(entries) == 2

    def test_list_filter_entity(self, empty_storage):
        audit = AuditLog(empty_storage)
        audit.record("create", "trail", "p1")
        audit.record("create", "trailhead", "l1")
        entries = audit.list_entries(entity="trail")
        assert all(e["entity"] == "trail" for e in entries)

    def test_list_filter_entity_id(self, empty_storage):
        audit = AuditLog(empty_storage)
        audit.record("create", "trail", "p1")
        audit.record("create", "trail", "p2")
        entries = audit.list_entries(entity_id="p1")
        assert len(entries) == 1

    def test_list_limit(self, empty_storage):
        audit = AuditLog(empty_storage)
        for i in range(5):
            audit.record("create", "trail", f"p{i}")
        entries = audit.list_entries(limit=2)
        assert len(entries) == 2

    def test_list_newest_first(self, empty_storage):
        audit = AuditLog(empty_storage)
        audit.record("create", "trail", "p1")
        audit.record("update", "trail", "p1")
        entries = audit.list_entries()
        assert len(entries) == 2
        assert entries[0]["timestamp"] >= entries[1]["timestamp"]
        assert {e["action"] for e in entries} == {"create", "update"}

    def test_since(self, empty_storage):
        audit = AuditLog(empty_storage)
        first = audit.record("create", "trail", "p1")
        entries = audit.since(first["timestamp"])
        assert len(entries) >= 1

    def test_wrap_mutation(self, empty_storage):
        audit = AuditLog(empty_storage)
        result = audit.wrap_mutation("delete", "trail", "p1", lambda: 42)
        assert result == 42
        assert len(audit.list_entries()) == 1

    def test_export_text(self, empty_storage):
        audit = AuditLog(empty_storage)
        audit.record("create", "trail", "p1")
        text = audit.export_text()
        assert "create" in text
        assert "trail:p1" in text

    def test_export_text_empty(self, empty_storage):
        audit = AuditLog(empty_storage)
        assert audit.export_text() == "(empty audit log)"

    def test_details_default_empty(self, empty_storage):
        audit = AuditLog(empty_storage)
        entry = audit.record("create", "trail", "p1")
        assert entry["details"] == {}

    def test_timestamp_iso(self, empty_storage):
        audit = AuditLog(empty_storage)
        entry = audit.record("create", "trail", "p1")
        assert "T" in entry["timestamp"]

    def test_id_length(self, empty_storage):
        audit = AuditLog(empty_storage)
        entry = audit.record("create", "trail", "p1")
        assert len(entry["id"]) == 16

    def test_custom_actor(self, empty_storage):
        audit = AuditLog(empty_storage)
        entry = audit.record("import", "trail", "p1", actor="csv")
        assert entry["actor"] == "csv"
