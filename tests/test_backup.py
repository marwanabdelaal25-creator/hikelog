"""Tests for hikelog.backup."""

import json

import pytest

from hikelog.backup import GardenBackup
from hikelog.errors import ExportError, StorageError
from hikelog.storage import JsonStorage


class TestGardenBackupCreate:
    def test_create_backup(self, populated_storage, tmp_path):
        backup = GardenBackup(populated_storage.path, tmp_path / "backups")
        dest = backup.create(label="test")
        assert dest.exists()
        meta = dest.with_suffix(".meta.json")
        assert meta.exists()

    def test_create_missing_logbook_raises(self, tmp_path):
        backup = GardenBackup(tmp_path / "missing.json", tmp_path / "backups")
        with pytest.raises(StorageError):
            backup.create()


class TestGardenBackupList:
    def test_list_backups(self, populated_storage, tmp_path):
        backup = GardenBackup(populated_storage.path, tmp_path / "backups")
        backup.create()
        backup.create(label="second")
        backups = backup.list_backups()
        assert len(backups) == 2
        assert not backups[0].name.endswith(".meta.json")


class TestGardenBackupRestore:
    def test_restore(self, populated_storage, tmp_path):
        backup_dir = tmp_path / "backups"
        backup = GardenBackup(populated_storage.path, backup_dir)
        populated_storage.update_trail("trail001", {"nickname": "Original"})
        snap = backup.create()

        populated_storage.update_trail("trail001", {"nickname": "Changed"})
        safety = backup.restore(snap)
        assert safety.exists()
        reloaded = JsonStorage(populated_storage.path)
        assert reloaded.get_trail("trail001").nickname == "Original"

    def test_restore_corrupt_raises(self, populated_storage, tmp_path):
        backup_dir = tmp_path / "backups"
        backup = GardenBackup(populated_storage.path, backup_dir)
        bad = backup_dir / "logbook_bad.json"
        bad.write_text("{bad json", encoding="utf-8")
        with pytest.raises(StorageError):
            backup.restore(bad)

    def test_restore_latest(self, populated_storage, tmp_path):
        backup = GardenBackup(populated_storage.path, tmp_path / "backups")
        backup.create()
        safety = backup.restore_latest()
        assert safety.exists()

    def test_restore_latest_empty_raises(self, tmp_path):
        backup = GardenBackup(tmp_path / "logbook.json", tmp_path / "backups")
        tmp_path.joinpath("logbook.json").write_text("{}", encoding="utf-8")
        with pytest.raises(StorageError):
            backup.restore_latest()


class TestGardenBackupSnapshot:
    def test_export_snapshot(self, populated_storage, tmp_path):
        backup = GardenBackup(populated_storage.path, tmp_path / "backups")
        dest = backup.export_snapshot(populated_storage, tmp_path / "export.json")
        data = json.loads(dest.read_text(encoding="utf-8"))
        assert "trails" in data

    def test_import_snapshot(self, populated_storage, tmp_path):
        backup = GardenBackup(populated_storage.path, tmp_path / "backups")
        src = tmp_path / "snapshot.json"
        backup.export_snapshot(populated_storage, src)
        empty = JsonStorage(tmp_path / "empty.json")
        backup.import_snapshot(empty, src)
        assert len(empty.list_trails()) >= 2

    def test_import_missing_raises(self, populated_storage, tmp_path):
        backup = GardenBackup(populated_storage.path, tmp_path / "backups")
        with pytest.raises(ExportError):
            backup.import_snapshot(populated_storage, tmp_path / "missing.json")


class TestGardenBackupPrune:
    def test_prune_old_backups(self, populated_storage, tmp_path):
        backup = GardenBackup(populated_storage.path, tmp_path / "backups")
        for i in range(5):
            backup.create(label=f"b{i}")
        removed = backup.prune(keep=2)
        assert len(removed) == 3
        assert len(backup.list_backups()) == 2

    def test_prune_nothing_when_under_limit(self, populated_storage, tmp_path):
        backup = GardenBackup(populated_storage.path, tmp_path / "backups")
        backup.create()
        removed = backup.prune(keep=10)
        assert len(removed) == 0
