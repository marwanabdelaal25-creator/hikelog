# Architecture

*Marwan Helmy — how hikelog is put together*

I built hikelog as a single-user CLI first, then grew modules around it when I kept
needing "just one more thing" (seasonal intervals, AllTrails imports, hazard notes). Nothing
here is microservices. It's one JSON file and a bunch of Python modules that know how
to read it.

## High-level picture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  cli.py     │────▶│ JsonStorage  │────▶│  logbook.json    │
│  (commands) │     │  storage.py  │     │  (~/.hikelog) │
└─────────────┘     └──────┬───────┘     └─────────────────┘
       │                   │
       │            ┌──────┴───────┐
       ▼            ▼              ▼
  reports.py   trail.py       io_*.py (import/export)
  reminders.py visit.py    backup.py / migrate.py
  schedule.py  trip_log.py
```

The CLI is the main entry point (`hikelog` console script → `cli.py`). Everything
else is library code you can import in scripts — see `examples/` for that.

## Module map

| Module | Role |
|--------|------|
| `storage.py` | **Core.** `JsonStorage` reads/writes `logbook.json`, atomic writes, thread-safe CRUD for every bucket. |
| `trail.py` | Trail entity, health status, overdue math, `TrailCatalog` in-memory helpers. |
| `terrain.py` | Terrain profiles (water/light/conditions defaults). |
| `trailhead.py` | Rooms, windows, light levels, trailhead registry. |
| `visit.py` | `VisitEvent`, batch logging, analytics helpers. |
| `trip_log.py` | Repackting, fertilizing, pruning — anything that isn't visit. |
| `schedule.py` | Season-aware schedule engine, calendar views, interval audits. |
| `reminders.py` | "What's due today / overdue" sorted by urgency. |
| `seasons.py` | Season multipliers (visit less in winter, etc.). |
| `parser.py` | Human-friendly parsing: `7d`, `250ml`, `bright indirect`, `yesterday`. |
| `validators.py` | Shared validation — keeps CLI and imports from accepting nonsense. |
| `errors.py` | Typed exceptions (`NotFoundError`, `ImportPipelineError`, …). |
| `io_csv.py` | CSV import/export for trails and visit logs. |
| `io_alltrails.py` | AllTrails app CSV → hikelog trails. |
| `io_komoot.py` | Komoot spreadsheet → trails + auto-trailheads. |
| `io_jsonl.py` | JSONL streams for events / full export. |
| `backup.py` | Timestamped copies + restore with safety snapshot. |
| `migrate.py` | Schema version upgrades (v0 flat list → v3 full logbook). |
| `reports.py` | Monthly care summaries. |
| `stats.py` | Garden-wide snapshot stats. |
| `search.py` | Fuzzy search across trails, care logs, notes. |
| `audit_log.py` | Append-only audit trail in the JSON file. |
| `tags_manager.py`, `tag.py` | Tag CRUD and filtering. |
| `notes.py` | Per-trail notes with kinds (hazard, repack, …). |
| `photos.py`, `hazards.py`, `gear.py`, `conditions.py`, `exposure.py` | Extended care tracking buckets. |
| `collections.py`, `recurring.py`, `plugins.py`, `streaks.py` | Grouping, recurring tasks, plugin hooks, visit streaks. |
| `server.py` | Read-only HTTP dashboard (`hikelog serve`). |
| `cli.py` | Argument parsing and command wiring. |

## Why JSON, not SQLite

Honest answer: I killed three mist-loop, not because I lacked JOIN syntax.

1. **I want to read my logbook.** `cat ~/.hikelog/logbook.json | jq` at 2am beats
   `sqlite3 ... ".schema"`.
2. **Backups are obvious.** Copy the file. Email it to myself. Put it in git (private
   repo). Done.
3. **Recovery from my own mistakes.** I've hand-edited a bad import more than once.
   Text beats opaque binary when you're panicking.
4. **No migration treadmill.** SQLite is great when you have a schema that changes
   weekly. I have ~30 trails and a visit log. A version field + `migrate.py` is
   enough.
5. **Import/export symmetry.** CSV/AllTrails/logbook-plan pipelines write into the same
   structure the CLI uses. No ORM impedance mismatch.

Trade-offs I accept:

- No concurrent writers across machines (fine for one apartment).
- Full-file load on every command (fine at hundreds of trails, not thousands).
- No ad-hoc SQL queries (I use `search` and small Python scripts instead).

## Storage design

### Single file, many buckets

`logbook.json` is one object with named arrays ("buckets"). `JsonStorage` in
`storage.py` owns the shape:

```json
{
  "schema_version": 2,
  "trails": [],
  "terrain": [],
  "trailheads": [],
  "visit_events": [],
  "trip_logs": [],
  "tags": [],
  "notes": [],
  "audit": [],
  "plugins": [],
  "recurring": [],
  "collections": [],
  "conditions_readings": [],
  "exposure_logs": [],
  "hazard_incidents": [],
  "gear_events": [],
  "photos": []
}
```

Each bucket is a list of records with an `id` field (terrain use `key`). Generic
`_create` / `_read` / `_update` / `_delete` methods handle most buckets; trails and
terrain get typed wrappers returning `Trail` / `TerrainProfile` objects.

### Atomic writes

Saves go to `logbook.json.tmp` then `os.replace()` into place. If Python dies mid-write,
you still have the previous file. I learned this the hard way with a half-written export.

### Thread safety

`JsonStorage` uses an `RLock` so a background server thread and CLI commands don't
corrupt the same file in the same process.

### Side effects worth knowing

Creating a visit event also patches the trail's `last_visited_at`. Lazy coupling,
but it means reminders stay correct even if you only ever call `create_visit_event`.

### Paths and env

| Variable | Default |
|----------|---------|
| `HIKELOG_HOME` | `~/.hikelog/` (directory) |
| (implicit) | `HIKELOG_HOME/logbook.json` or `~/.hikelog/logbook.json` |
| CLI `--logbook` | Override full path to JSON file |

Backups land in `HIKELOG_HOME/backups/` unless you pass `--dir`.

### Schema evolution

`migrate.py` bumps `schema_version` through stepped transforms. `JsonStorage` merges
missing buckets with defaults on load so older files don't explode — but run
`hikelog` once after upgrading so migrations can apply cleanly.

## Data flow examples

**Add trail:** CLI → `Trail.create()` → `storage.create_trail()` → atomic save.

**Water:** CLI resolves name → `VisitEvent.create()` → `storage.create_visit_event()`
→ trail `last_visited_at` updated → audit entry.

**Import CSV:** `io_csv.import_trails_csv()` → row loop → `Trail.create()` or
`storage.update_trail()` → save per row (safe but not batched — imports are rare).

**Monthly report:** `reports.MonthlyReport.generate()` reads visit/care buckets,
filters by date range, returns aggregates — no separate analytics DB.

## What I'd change if I started over

Maybe split `visit_events` into a monthly JSONL archive once logs get huge. For now,
one file matches how I actually use it: open, tweak, close, go hike Half Dome.
