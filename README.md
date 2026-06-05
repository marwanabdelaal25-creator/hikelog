# hikelog

Weekend trail log CLI I wrote after losing a paper summit register in a rainstorm
and realizing my Notes app couldn't tell Half Dome from a grocery list.

One JSON file (`logbook.json`) on disk. Log visits, track elevation, note gear,
and grep for "Yosemite" at 6am without another outdoors app subscription.

## What it does

- Track trails with terrain profile, difficulty, and trailhead placement
- Log visit records (distance, elevation gain, pace, weather notes)
- Trip notes and hazard reports when a route feels wrong
- Gear lists and exposure/conditions history in the logbook
- Weekly hike stats, streaks, seasonal trail calendars
- Import from AllTrails CSV and Komoot exports
- Reminders when a favorite trail is overdue for a revisit

## What it doesn't do

- Live GPS tracking or satellite SOS — use Gaia or a PLB
- Crowd-sourced trail conditions API — I type what I saw
- Multi-user expedition planning at guide-company scale

## Quick start

```bash
pip install .
hikelog init ~/hikes/logbook.json
hikelog add-trail --name "Mist Loop" --terrain alpine --interval 14d
hikelog visit trail001 --km 8.4 --gain 420
hikelog stats --week
```

## Author

Marwan Helmy — marwanabdelaal25@gmail.com

MIT license. Side project, Aug 2024–present.
