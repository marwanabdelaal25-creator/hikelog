"""Backup and restore helpers for logbook.json.

Author: Marwan Helmy
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .errors import ExportError, StorageError
from .storage import JsonStorage


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


class GardenBackup:
    def __init__(self, logbook_path: str | Path, backup_dir: str | Path):
        self.logbook_path = Path(logbook_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create(self, label: Optional[str] = None) -> Path:
        if not self.logbook_path.exists():
            raise StorageError("logbook file missing", str(self.logbook_path))
        suffix = f"_{label}" if label else ""
        dest = self.backup_dir / f"logbook_{_stamp()}{suffix}.json"
        try:
            shutil.copy2(self.logbook_path, dest)
        except OSError as exc:
            raise StorageError("backup failed: %s" % exc, str(dest)) from exc
        meta = dest.with_suffix(".meta.json")
        meta.write_text(json.dumps({
            "source": str(self.logbook_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "label": label,
        }, indent=2), encoding="utf-8")
        return dest

    def list_backups(self) -> list[Path]:
        files = sorted(self.backup_dir.glob("logbook_*.json"), reverse=True)
        return [f for f in files if not f.name.endswith(".meta.json")]

    def restore(self, backup_path: str | Path, *, verify: bool = True) -> Path:
        src = Path(backup_path)
        if not src.exists():
            raise StorageError("backup not found", str(src))
        if verify:
            try:
                json.loads(src.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise StorageError("backup corrupt: %s" % exc, str(src)) from exc
        safety = self.create(label="pre_restore")
        try:
            shutil.copy2(src, self.logbook_path)
        except OSError as exc:
            raise StorageError("restore failed: %s" % exc, str(self.logbook_path)) from exc
        return safety

    def restore_latest(self) -> Path:
        backups = self.list_backups()
        if not backups:
            raise StorageError("no backups available", str(self.backup_dir))
        return self.restore(backups[0])

    def export_snapshot(self, storage: JsonStorage, dest: str | Path) -> Path:
        out = Path(dest)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = storage.snapshot()
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return out

    def import_snapshot(self, storage: JsonStorage, src: str | Path) -> None:
        path = Path(src)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExportError(str(path), "import failed: %s" % exc) from exc
        storage.replace_all(data)

    def prune(self, keep: int = 10) -> list[Path]:
        removed = []
        backups = self.list_backups()
        for old in backups[keep:]:
            try:
                old.unlink()
                meta = old.with_suffix(".meta.json")
                if meta.exists():
                    meta.unlink()
                removed.append(old)
            except OSError:
                pass  # TODO: log failures
        return removed
