#!/usr/bin/env python3
"""Generate multi-source hiking import fixtures (stdlib only)."""

from __future__ import annotations

import csv
import json
import random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "imports"

SOURCES = [
    "alltrails", "komoot", "csv_native", "jsonl_events",
    "peakbagger", "caltopo", "gaiagps", "trailforks",
]
YEARS = list(range(2019, 2026))
TERRAINS = ["Alpine", "Coastal", "Desert", "Forest", "Volcanic"]
TRAILHEADS = ["North Lot", "South Gate", "Visitor Center", "Campground Loop"]


def _rng(source: str, year: int, month: int) -> random.Random:
    return random.Random(hash((source, year, month)) & 0xFFFFFFFF)


def _trail_rows(rng: random.Random, n: int) -> list[dict]:
    rows = []
    for i in range(n):
        d = date(rng.randint(2019, 2025), rng.randint(1, 12), rng.randint(1, 28))
        rows.append({
            "name": f"Trail {i}",
            "terrain": rng.choice(TERRAINS),
            "trailhead": rng.choice(TRAILHEADS),
            "interval_days": rng.choice([7, 14, 21, 30]),
            "last_visited": d.isoformat(),
            "notes": "x" * rng.randint(0, 24),
        })
    return rows


def _write_alltrails_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "Trail Name", "Terrain", "Trailhead", "Revisit Every (days)",
        "Last Hiked", "Notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({
                "Trail Name": r["name"],
                "Terrain": r["terrain"],
                "Trailhead": r["trailhead"],
                "Revisit Every (days)": r["interval_days"],
                "Last Hiked": r["last_visited"],
                "Notes": r["notes"],
            })


def _write_native_csv(path: Path, rows: list[dict]) -> None:
    fields = ["name", "terrain_key", "trailhead", "visit_interval_days", "last_visited", "notes"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({
                "name": r["name"],
                "terrain_key": r["terrain"].lower().replace(" ", "-"),
                "trailhead": r["trailhead"],
                "visit_interval_days": r["interval_days"],
                "last_visited": r["last_visited"],
                "notes": r["notes"],
            })


def _write_komoot_csv(path: Path, rows: list[dict]) -> None:
    fields = ["segment", "region", "route", "trail_name", "terrain", "distance_km", "notes"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, r in enumerate(rows):
            w.writerow({
                "segment": f"Seg-{i % 5 + 1}",
                "region": r["trailhead"],
                "route": f"Route-{i % 8 + 1}",
                "trail_name": r["name"],
                "terrain": r["terrain"],
                "distance_km": round(random.Random(i).uniform(3.0, 16.0), 1),
                "notes": r["notes"],
            })


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    lines = []
    for r in rows:
        lines.append(json.dumps({"type": "visit", "trail": r["name"], "date": r["last_visited"]}))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_generic_json(path: Path, source: str, rows: list[dict]) -> None:
    path.write_text(
        json.dumps({"source": source, "version": 1, "trails": rows}, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    total_files = 0
    for source in SOURCES:
        for year in YEARS:
            src_dir = OUT / source / str(year)
            src_dir.mkdir(parents=True, exist_ok=True)
            for month in range(1, 13):
                rng = _rng(source, year, month)
                rows = _trail_rows(rng, rng.randint(18, 48))
                stem = f"{source}_{year}_{month:02d}"
                if source == "alltrails":
                    _write_alltrails_csv(src_dir / f"{stem}.csv", rows)
                elif source == "csv_native":
                    _write_native_csv(src_dir / f"{stem}.csv", rows)
                elif source == "komoot":
                    _write_komoot_csv(src_dir / f"{stem}.csv", rows)
                elif source == "jsonl_events":
                    _write_jsonl(src_dir / f"{stem}.jsonl", rows)
                else:
                    if month % 3 == 0:
                        _write_alltrails_csv(src_dir / f"{stem}.csv", rows)
                    elif month % 3 == 1:
                        _write_generic_json(src_dir / f"{stem}.json", source, rows)
                    else:
                        _write_native_csv(src_dir / f"{stem}.csv", rows)
                total_files += 1
    print(f"wrote {total_files} import fixtures under {OUT}")


if __name__ == "__main__":
    main()
