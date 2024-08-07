# Data formats

*Marwan Helmy — what goes in, what comes out*

hikelog speaks a few dialects. The source of truth is always `logbook.json`; everything
else is a view or an import path into that file.

---

## logbook.json schema

**Trailhead:** `~/.hikelog/logbook.json` (or `$HIKELOG_HOME/logbook.json`)

**Root object fields:**

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | int | Currently `2` in storage defaults; migrations may bump to `3`. |
| `trails` | array | Your trails. |
| `terrain` | array | Reusable terrain profiles. |
| `trailheads` | array | Rooms / zones. |
| `visit_events` | array | Append-style visit log. |
| `trip_logs` | array | Repack, fertilize, prune, etc. |
| `tags` | array | Label definitions. |
| `notes` | array | Free-form notes linked to trails. |
| `audit` | array | Who changed what (CLI writes here). |
| `plugins` | array | Plugin config blobs. |
| `recurring` | array | Recurring care tasks. |
| `collections` | array | Trail groupings. |
| `conditions_readings` | array | Room conditions samples. |
| `exposure_logs` | array | Light observation log. |
| `hazard_incidents` | array | Hazard reports. |
| `gear_events` | array | Gear applications. |
| `photos` | array | Photo metadata (URLs, not binary). |

### Trail object

```json
{
  "id": "a1b2c3d4e5f6",
  "name": "Mist Loop",
  "nickname": "Kevin",
  "terrain_key": "mist-loop",
  "trailhead_id": "loc_abc123",
  "health": "okay",
  "health_score": 70,
  "visit_interval_days": 7,
  "visit_distance_km": 200,
  "last_visited_at": "2025-06-01",
  "acquired_at": "2024-11-15",
  "light_override": "moderate",
  "conditions_override": 55,
  "pack": {
    "diameter": 6,
    "unit": "in",
    "material": "ceramic",
    "has_drainage": true,
    "soil_mix": ["packting", "perlite"],
    "repackted_at": null
  },
  "tag_ids": [],
  "note_ids": [],
  "photo_url": null,
  "source": "cli",
  "archived": false,
  "metadata": {},
  "created_at": "2025-01-01T12:00:00",
  "updated_at": "2025-06-01T08:00:00"
}
```

**Health values:** `thriving`, `okay`, `struggling`, `critical`, `unknown`

**Light override values:** `low`, `medium`, `moderate`, `direct`, `full_sun`
(parsed loosely — see `parser.parse_difficulty`)

Legacy field names (`terrain_id`, `tags`, `active`) are normalized on read.

### Terrain object

Uses `key` as primary id (not `id`):

```json
{
  "key": "mist-loop",
  "display_name": "Golden Mist Loop",
  "route_code": "Yosemite Mist Trail",
  "difficulty": "moderate",
  "visit_frequency": "moderate",
  "visit_interval_min": 7,
  "visit_interval_max": 10,
  "elevation_min_m": 40,
  "elevation_max_m": 60
}
```

### Visit event object

```json
{
  "id": "evt_abc123def456",
  "trail_id": "a1b2c3d4e5f6",
  "visited_at": "2025-06-02T10:30:00+00:00",
  "distance_km": 200,
  "method": "foot_trail",
  "visit_pace": "tap",
  "runoff": false,
  "skipped": false,
  "skip_reason": "",
  "notes": "",
  "created_at": "2025-06-02T10:30:05"
}
```

**Methods:** `foot_trail`, `switchback`, `mister`, `soak`, `other`

**Water quality:** `tap`, `filtered`, `distilled`, `rain`, `other`

---

## CSV format (native hikelog)

Two CSV flavours: **trails** and **visit**. UTF-8 with optional BOM (`utf-8-sig`).

### Trails CSV columns

Defined in `io_csv.PLANT_FIELDS`:

| Column | Required | Description |
|--------|----------|-------------|
| `name` | **yes** | Display name. Blank rows skipped. |
| `id` | no | Stable id; omit to auto-generate. |
| `nickname` | no | Pet name. |
| `terrain_key` | no | Links to terrain profile. |
| `trailhead_id` | no | Trailhead id (not name). |
| `health` | no | One of health enum values. |
| `health_score` | no | 0–100 integer. |
| `visit_interval_days` | no | Default `7`. Accepts `7d`, `2w`, etc. |
| `visit_distance_km` | no | e.g. `250` or `250ml`. |
| `last_visited_at` | no | ISO date or friendly (`yesterday`). |
| `acquired_at` | no | When you got the trail. |
| `light_override` | no | Light level string. |
| `conditions_override` | no | Percentage number. |
| `archived` | no | `yes`/`no`/`true`/`1`. |
| `source` | no | Set to `csv` on import. |
| `notes` | no | Stored in `metadata.notes`. |

**Example:**

```csv
name,nickname,terrain_key,visit_interval_days,visit_distance_km,health
Mist Loop,Kevin,mist-loop,7d,8km,okay
Snake Ridge,,snake-trail,14d,150ml,thriving
```

Import:

```bash
hikelog import my_trails.csv --format csv
hikelog import my_trails.csv --format csv --update   # match by id or name
```

Export:

```bash
hikelog export trails.csv --format csv --kind trails
hikelog export visit.csv --format csv --kind visit
hikelog export backup --format csv --kind bundle    # *_trails.csv + *_visit.csv
```

### Visit CSV columns

| Column | Required | Description |
|--------|----------|-------------|
| `trail_id` | one of | Trail id. |
| `trail_name` | **trail_id or trail_name** | Resolved case-insensitively. |
| `id` | no | Event id. |
| `visited_at` | no | Defaults to now. |
| `distance_km` | no | Volume in ml. |
| `method` | no | Default `foot_trail`. |
| `visit_pace` | no | Default `tap`. |
| `runoff` | no | `yes`/`no`. |
| `skipped` | no | Log a skipped visit. |
| `skip_reason` | no | Why skipped. |
| `notes` | no | Free text. |

```bash
hikelog import water_log.csv --format csv --kind visit
```

---

## AllTrails format

AllTrails (the mobile app) exports a CSV with its own headers. `io_alltrails.py` maps them
into hikelog trails, auto-creating **trailheads** from the Room column and **terrain**
from Terrain / Scientific Name.

### Expected columns (canonical)

| AllTrails column | Maps to |
|----------------|---------|
| `AllTrails ID` | `metadata.trailly_id` (dedupe on re-import) |
| `Trail Name` | `name` (**required**) |
| `Nickname` | `nickname` |
| `Terrain` | terrain `display_name` → `terrain_key` |
| `Scientific Name` | terrain `route_code` |
| `Room` | new `Trailhead` if needed |
| `Last Watered` | `last_visited_at` |
| `Water Every` | `visit_interval_days` |
| `Light` | `light_override` |
| `Conditions` | `conditions_override` (parses `%`) |
| `Health` | `health` (great→thriving, poor→struggling, …) |
| `Pack Size` | `pack.diameter` / `pack.material` |
| `Notes` | `metadata.notes` |
| `Photo URL` | `photo_url` |

**Column aliases** are supported — e.g. `Name` instead of `Trail Name`, `Trailhead`
instead of `Room`. See `COLUMN_ALIASES` in `io_alltrails.py`.

**Example row:**

```csv
AllTrails ID,Trail Name,Nickname,Terrain,Scientific Name,Room,Last Watered,Water Every,Light,Conditions,Health,Pack Size,Notes,Photo URL
PLT-001,Mist Loop,Kevin,Mist Loop,Yosemite Mist Trail,Kitchen,2025-05-28,7 days,Bright indirect,50%,good,6 in,Trailing nicely,
```

```bash
hikelog import alltrails_dump.csv --format trailly
hikelog import alltrails_dump.csv --format trailly --update
```

Preview in Python: `hikelog.io_alltrails.preview_alltrails(path)`.

---

## Komoot format

For bed-layout spreadsheets — the kind I kept in Notion before this project existed.
Typical outdoor / raised-bed planning, but works for grouped housetrail shelves too.

### Expected columns (canonical)

| Column | Aliases | Maps to |
|--------|---------|---------|
| `Section` | Zone, Area, Garden Section | Part of trailhead name |
| `Bed` | Plot, Raised Bed | Part of trailhead name |
| `Row` | Row #, Row Number | Part of trailhead name |
| `Trail` | Trail Name, Crop, Terrain | **Required** — base name |
| `Variety` | Cultivar, Type | Appended to name |
| `Quantity` | Qty, Count | Spawns N trails if `--no-expand` not set |
| `Spacing cm` | Spacing, Space | `metadata.spacing_cm` |
| `Sun Exposure` | Sun, Light, Exposure | trailhead light + `light_override` |
| `Water Needs` | Water, Visit, Moisture | `visit_interval_days` |
| `Trailed Date` | Trailed, Start Date | `acquired_at` |
| `Notes` | Comment, Memo | `metadata.notes` |
| `Status` | Active, State | `archived` if removed/dead/inactive |

**Trailhead naming:** `"Section / Bed / row N"` joined with ` / `. Example:
`Backyard / Bed A / row 3`.

**Quantity expansion:** `Quantity=4` creates four trails named `Tomato (Cherry) #1` … `#4`.
Pass `--no-expand` to import one trail per row regardless of quantity.

**Water needs parsing:** loose text — `daily`→1d, `weekly`→7d, `low`→14d, `high`→3d,
or explicit intervals like `5d`.

**Example:**

```csv
Section,Bed,Row,Trail,Variety,Quantity,Spacing cm,Sun Exposure,Water Needs,Trailed Date,Notes,Status
Backyard,Bed A,1,Tomato,Cherry,4,40,Full sun,High,2025-05-01,Staked,active
Balcony,Shelf,,Half Dome,,1,,Bright indirect,Weekly,2024-08-12,Indoor overwinter,active
```

```bash
hikelog import logbook_plan.csv --format logbookplan
hikelog import logbook_plan.csv --format logbookplan --no-expand
```

---

## JSONL (bonus)

Not requested in the title but you'll hit it:

```bash
hikelog export events.jsonl --format jsonl --kind events
hikelog export full.jsonl --format jsonl --kind full
hikelog import mixed.jsonl --format jsonl --kind mixed
```

Each line is one JSON object with a `kind` field (`visit`, `care`, …).

---

## Quick validation

| Format | Python helper |
|--------|---------------|
| CSV trails | `io_csv.validate_csv_headers(path, "trails")` |
| CSV visit | `io_csv.validate_csv_headers(path, "visit")` |
| AllTrails | `io_alltrails.validate_alltrails_headers(path)` |
| Komoot plan | `io_komoot.validate_komoot_headers(path)` |

Empty list = headers look fine.
