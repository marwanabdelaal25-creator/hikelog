#!/usr/bin/env python3
"""Generate large trail logbook JSON fixtures (stdlib only)."""

from __future__ import annotations

import json
import random
import string
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "logbooks"

TRAILHEADS = ["valley-gate", "ridge-lot", "creek-crossing", "summit-parking", "campground", "visitor-center"]
TERRAIN_KEYS = [
    "alpine-ridge", "coastal-bluff", "desert-canyon", "old-growth", "volcanic-loop",
    "meadow-walk", "cascade-falls", "granite-domes", "redwood-grove", "basalt-plateau",
]
PERSONAS = [
    "day_hiker", "peak_bagger", "family_trails", "trail_runner", "photographer",
    "winter_snowshoe", "desert_dawn", "coastal_weekend", "backpacker", "minimalist",
]


def _trail_name(rng: random.Random, n: int) -> str:
    adj = rng.choice(["Misty", "Windy", "Steep", "Shady", "Rocky", "Quiet", "Long"])
    terrain = rng.choice(TERRAIN_KEYS).replace("-", " ").title()
    return f"{adj} {terrain} #{n}"


def _trail_entry(rng: random.Random, idx: int, year: int) -> dict:
    acquired = date(year, rng.randint(1, 12), rng.randint(1, 28))
    interval = rng.choice([7, 14, 21, 30, 45, 60])
    last = acquired + timedelta(days=rng.randint(0, interval * 3))
    return {
        "id": f"tr-{year}-{idx:06d}",
        "name": _trail_name(rng, idx),
        "terrain_key": rng.choice(TERRAIN_KEYS),
        "trailhead_id": f"th-{rng.choice(TRAILHEADS)}",
        "visit_interval_days": interval,
        "last_visited": last.isoformat(),
        "first_hiked": acquired.isoformat(),
        "status": rng.choice(["favorite", "planned", "done", "seasonal"]),
        "pack_liters": rng.choice([18, 24, 32, 40, 55]),
        "notes": " ".join(
            "".join(rng.choice(string.ascii_letters + " ") for _ in range(rng.randint(20, 80)))
            for _ in range(rng.randint(0, 2))
        ).strip(),
        "tag_ids": [f"tag-{rng.randint(1, 80)}" for _ in range(rng.randint(0, 4))],
    }


def _visit_events(rng: random.Random, trails: list[dict], count: int) -> list[dict]:
    events = []
    for i in range(count):
        trail = rng.choice(trails)
        d = date.fromisoformat(trail["last_visited"]) - timedelta(days=rng.randint(0, 120))
        events.append({
            "id": f"vi-{i:07d}",
            "trail_id": trail["id"],
            "visited_at": d.isoformat(),
            "distance_km": round(rng.uniform(2.5, 18.0), 2),
            "elevation_gain_m": rng.choice([120, 240, 380, 520, 760, 980]),
            "pace": rng.choice(["easy", "moderate", "hard", "scramble"]),
            "notes": "",
        })
    return events


def _logbook_blob(rng: random.Random, *, trails_n: int, label: str) -> dict:
    year = 2024
    if label[-4:].isdigit():
        year = int(label[-4:])
    trails = [_trail_entry(rng, i, year - rng.randint(0, 2)) for i in range(trails_n)]
    return {
        "version": 3,
        "label": label,
        "persona": rng.choice(PERSONAS),
        "generated": True,
        "trails": trails,
        "terrain": [{"key": t, "display_name": t.replace("-", " ").title()} for t in TERRAIN_KEYS],
        "trailheads": [{"id": f"th-{h}", "name": h.replace("-", " ").title(), "zone": h} for h in TRAILHEADS],
        "visit_events": _visit_events(rng, trails, min(trails_n * 3, 9000)),
        "trip_logs": [],
        "tags": [],
        "notes": [],
        "audit": [],
        "plugins": {},
        "recurring": [],
    }


def _write_json(path: Path, data: dict) -> int:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0

    for i, n in enumerate((4200, 4800, 3600), start=1):
        rng = random.Random(3100 + i)
        data = _logbook_blob(rng, trails_n=n, label=f"megatrail-{i}")
        sz = _write_json(OUT / f"megatrail-{i}.json", data)
        total += sz
        print(f"megatrail-{i}.json: {sz / (1024 * 1024):.2f} MB")

    for year in range(2019, 2026):
        rng = random.Random(year + 900)
        snap = _logbook_blob(rng, trails_n=rng.randint(90, 200), label=f"snapshot-{year}")
        total += _write_json(OUT / f"snapshot-{year}.json", snap)

    for persona in PERSONAS:
        rng = random.Random(hash(persona) & 0xFFFFFFFF)
        blob = _logbook_blob(rng, trails_n=rng.randint(45, 130), label=f"persona-{persona}")
        total += _write_json(OUT / f"persona-{persona}.json", blob)

    sample = _logbook_blob(random.Random(42), trails_n=14, label="sample")
    sample["generated"] = False
    _write_json(ROOT / "tests" / "fixtures" / "sample_logbook.json", sample)

    print(f"total fixture JSON: {total / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    main()
