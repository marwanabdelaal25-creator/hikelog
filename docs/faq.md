# FAQ

*Marwan Helmy — questions friends actually ask*

---

## Where does my data live?

Default: `~/.hikelog/logbook.json` on your machine. Set `HIKELOG_HOME` to use a
different directory (still `logbook.json` inside it). Pass `--logbook /full/path.json`
to any CLI command for a one-off override. Nothing phones home — it's a local file.

---

## Why JSON instead of a real database?

Because I wanted to `grep` my logbook at 2am, email a backup to myself, and fix a bad
import with a text editor. SQLite is great; it's just overkill for ~30 mist-loop and a
visit log. See [architecture.md](architecture.md) for the full rant.

---

## Can it identify trails from photos?

No. Use PictureThis, iNaturalist, or post on r/trail types like the rest of us.
hikelog tracks care *after* you know what you have.

---

## I killed a trail. Should I delete it?

Archive instead of delete — you'll want the history. Import with `archived=yes` in CSV,
or set `"archived": true` in JSON. `hikelog list` hides archived trails by default;
`hikelog list --all` shows them.

---

## How do reminders know when something is due?

Each trail has `visit_interval_days` and `last_visited_at`. Reminders add a
**season multiplier** (visit less in winter). If you never logged a water, it falls
back to `acquired_at`. Run `hikelog reminders --overdue` to see the damage.

---

## What's the difference between visit and care logs?

**Visit events** = you hiked (or skipped). **Care logs** = repack, fertilize, prune,
hazard treatment, etc. Monthly reports count both separately.

---

## Import from AllTrails failed — now what?

Check you have a `Trail Name` (or `Name`) column. Run:

```bash
python -c "from pathlib import Path; from hikelog.io_alltrails import validate_alltrails_headers; print(validate_alltrails_headers(Path('your.csv')))"
```

Empty output = headers OK. Non-empty = missing columns. Restore pre-import backup if
the logbook looks wrong: `hikelog backup --restore <file>`.

---

## Can two people share one logbook file?

Technically yes (Dropbox, git, email). **Don't edit simultaneously** — there's no
merge conflict handling. One writer at a time. I use export CSV → partner imports for
shared trail-sitting handoffs.

---

## How do I move hikelog to a new laptop?

Copy `~/.hikelog/` (or your `HIKELOG_HOME` folder). Install hikelog on the new
machine. Done. Optional: `hikelog export backup.csv --format csv --kind bundle` as
a human-readable extra copy.

---

## Is there a web UI?

Read-only dashboard: `hikelog serve` → open `http://127.0.0.1:8765/`. It doesn't
edit data — use CLI or Python scripts for changes.

---

## What Python version do I need?

3.9 or newer (`requires-python >=3.9` in pyproject.toml). Dev extras: `pip install -e ".[dev]"`.

---

## I corrupted logbook.json. Help.

1. Check `~/.hikelog/backups/` for timestamped copies.
2. `hikelog backup --list`
3. `hikelog backup --restore path/to/logbook_YYYYMMDD_HHMMSS.json`

Restore always makes a safety copy of the current file first (`pre_restore` label).

---

## Can I use hikelog from my own Python scripts?

Yes — that's the point of `examples/`. Core entry:

```python
from hikelog.storage import JsonStorage
from hikelog.trail import Trail

storage = JsonStorage("~/.hikelog/logbook.json")
trail = storage.create_trail(Trail.create("New Friend", visit_interval_days=7))
```

Public API surface is in `hikelog.__init__` — trails, visit, schedules, parsers,
validators, errors.
- faq 0
