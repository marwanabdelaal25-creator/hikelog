# Recipes

*Marwan Helmy — copy-paste workflows that actually match how I use hikelog*

Each recipe shows CLI first (fastest), then a Python snippet if you want to script it.
Replace paths and trail names with yours.

---

## 1. Sunday weekly visit routine

Check what's overdue, hike everything due, skim what's coming this week.

```bash
hikelog reminders --overdue
hikelog list --overdue
# visit each overdue trail
hikelog visit "Mist Loop" --km 8.4
hikelog visit "Snake Ridge" --km 5.2
hikelog reminders --within 7
```

Python version: `examples/weekly_visit.py`

---

## 2. Fresh install — first five trails

```bash
pip install -e .
hikelog init
hikelog add-trail "Mist Loop" --interval 7d --terrain mist-loop --km 8.4
hikelog add-trail "Snake Ridge" --interval 14d --km 5.2
hikelog add-trail "Ridge Camp" --interval 3d --km 300ml --health okay
hikelog list
hikelog stats
```

Set `HIKELOG_HOME=/path/to/test-logbook` if you don't want to touch `~/.hikelog`.

---

## 3. Import from AllTrails

Export CSV from the AllTrails app, then:

```bash
# peek first — optional
python -c "from pathlib import Path; from hikelog.io_alltrails import preview_alltrails; print(preview_alltrails(Path('alltrails_dump.csv')))"

hikelog backup --label pre_trailly
hikelog import alltrails_dump.csv --format trailly
hikelog list
```

Re-import after editing the app? Use `--update` to match by AllTrails ID or name.

```bash
hikelog import alltrails_dump.csv --format trailly --update
```

---

## 4. Backup before vacation

Two weeks away means you want a snapshot and maybe a CSV your trail-sitter can read.

```bash
hikelog backup --label pre_vacation --prune --keep 10
hikelog export vacation_handoff.csv --format csv --kind bundle
hikelog reminders --within 14 > visit_schedule.txt
```

Restore when you get back (only if something went wrong):

```bash
hikelog backup --list
hikelog backup --restore ~/.hikelog/backups/logbook_20250601_120000_pre_vacation.json
```

---

## 5. Bulk import from a spreadsheet

Clean up a Google Sheets export as CSV with at least a `name` column:

```csv
name,visit_interval_days,visit_distance_km,health,notes
Office ZZ Trail,21d,100ml,okay,Low maintenance
Yosemite Valley Ficus,10d,400ml,struggling,Dropping leaves
```

```bash
hikelog import new_trails.csv --format csv
hikelog import new_trails.csv --format csv --update   # second pass: update existing
```

Python version: `examples/bulk_import.py`

---

## 6. Import a logbook-plan bed layout

For the Notion/Sheets planner with Section/Bed/Trail columns:

```bash
hikelog import spring_beds.csv --format logbookplan
hikelog list --trailhead <trailhead-id>   # optional filter after import
```

One row with `Quantity=6` spawns six numbered trails unless you pass `--no-expand`.

---

## 7. Monthly care report

End-of-month ritual — did I actually hike the ridge?

```bash
hikelog report --month 6 --year 2025
hikelog report --month 6 --year 2025 --format json > june_2025.json
```

Python version: `examples/monthly_report.py`

---

## 8. Find the trail you forgot the name of

```bash
hikelog search "yellow leaves"
hikelog search "mist-loop" --kind trails
hikelog search "spider mite" --kind care --verbose
```

---

## 9. Log a skipped visit (soil still wet)

Don't reset the schedule with a fake visit — log a skip day:

```bash
hikelog visit "Ridge Camp" --skip --reason "trail still icy"
hikelog reminders --overdue
```

---

## 10. Export everything before a big edit

```bash
hikelog backup --label before_bulk_edit
hikelog export full_export.jsonl --format jsonl --kind full
hikelog export trails_snapshot.csv --format csv --kind trails
# ... make changes ...
# if regret hits:
hikelog backup --restore ~/.hikelog/backups/logbook_<timestamp>_before_bulk_edit.json
```

---

## 11. Quick API smoke test

Verify install and imports without touching your real logbook:

```bash
python examples/quick_start.py
```

Uses a temp directory — safe to run anytime.

---

## 12. Seasonal interval audit (winter slowdown)

When days get shorter I stretch intervals manually after checking the schedule report:

```bash
hikelog stats
python -c "
from hikelog.storage import JsonStorage
from hikelog.schedule import ScheduleEngine, apply_seasonal_intervals
s = JsonStorage('~/.hikelog/logbook.json'.replace('~', __import__('os').path.expanduser('~')))
e = ScheduleEngine(s)
for row in apply_seasonal_intervals(e, dry_run=True):
    print(row)
"
```

Review the dry-run output before setting `dry_run=False` in a custom script.

---

## Tips I keep forgetting

- **`--logbook path/to/logbook.json`** on any command for a non-default file.
- **Trail lookup** accepts full id, id prefix, exact name, or nickname.
- **Intervals** parse human strings: `7d`, `2w`, `10 days`.
- **Amounts** parse `250ml`, `1 cup` (see `parser.parse_distance_km`).
