#!/usr/bin/env python3
"""Bulk import trails from CSV (and optionally AllTrails).

Author: Marwan Helmy
Run: python examples/bulk_import.py
     python examples/bulk_import.py path/to/trails.csv
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from hikelog import io_csv, io_alltrails
from hikelog.backup import GardenBackup
from hikelog.storage import JsonStorage


def logbook_path() -> Path:
    home = os.environ.get("HIKELOG_HOME")
    base = Path(home) if home else Path.home() / ".hikelog"
    return base / "logbook.json"


def sample_csv(path: Path) -> None:
    path.write_text(
        "name,visit_interval_days,visit_distance_km,health,notes\n"
        "Office ZZ Trail,21d,100ml,okay,Low maintenance\n"
        "Yosemite Valley Ficus,10d,400ml,struggling,Dropping leaves — check light\n"
        "Mist Loop,7d,8km,thriving,Trailing nicely\n",
        encoding="utf-8",
    )


def main() -> None:
    csv_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    use_temp_logbook = csv_file is None

    if use_temp_logbook:
        tmp = tempfile.mkdtemp(prefix="hikelog_import_")
        path = Path(tmp) / "logbook.json"
        csv_file = Path(tmp) / "trails.csv"
        sample_csv(csv_file)
        print(f"Demo mode — logbook: {path}")
    else:
        path = logbook_path()
        if not csv_file.exists():
            print(f"File not found: {csv_file}", file=sys.stderr)
            sys.exit(1)

    storage = JsonStorage(path)
    backup_dir = path.parent / "backups"
    if path.exists() and path.stat().st_size > 50:
        snap = GardenBackup(path, backup_dir).create(label="pre_bulk_import")
        print(f"Backup: {snap}")

    missing = io_csv.validate_csv_headers(csv_file, "trails")
    if missing:
        print(f"CSV missing columns: {missing}", file=sys.stderr)
        sys.exit(1)

    count = io_csv.import_trails_csv(storage, csv_file, update=True)
    print(f"Imported {count} trail(s) from {csv_file.name}")

    for trail in storage.list_trails():
        print(f"  - {trail.display_name}: every {trail.visit_interval_days}d, {trail.health.value}")

    if csv_file.name.lower().find("trailly") >= 0:
        n = io_alltrails.import_alltrails(storage, csv_file, update=True)
        print(f"AllTrails pass: {n} record(s)")


if __name__ == "__main__":
    main()
