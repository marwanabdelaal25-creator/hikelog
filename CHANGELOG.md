# Changelog

All notable changes to hikelog are documented here. I don't do semver
religiously but I tag releases when something actually ships.

## [1.2.0] - 2026-05-28

### Added
- Komoot spreadsheet import (`io_komoot`)
- Photo metadata tracking (paths only — bytes live beside the JSON)
- Recurring care tasks for fertilizing on a cadence
- `serve` subcommand: read-only HTTP view of logbook.json

### Changed
- Schema v2 → v3: trip_logs bucket, environmental readings, recurring tasks
- Seasonal multipliers now apply in reminder urgency scoring

## [1.1.0] - 2025-11-14

### Added
- AllTrails app CSV import
- Monthly reports and streak tracking
- Plugin hook registry (experimental)

### Fixed
- `water` command accepted negative ml amounts on Windows paths
- Migration 1→2 dropped empty tag lists instead of preserving `[]`

## [1.0.0] - 2025-06-02

### Added
- Initial public shape: trails, terrain catalog, trailheads, visit log
- CSV and JSONL import/export
- Backup/restore with rotation
- Audit log for destructive operations

## [0.3.0] - 2024-12-08

- Added terrain profiles with built-in defaults for common trail types
- Trailhead zones with light-level hints

## [0.2.0] - 2024-09-21

- JSON storage layer with atomic writes
- Basic CLI: init, add-trail, water, list

## [0.1.0] - 2024-07-30

- Skeleton repo, README, first Trail dataclass
- v0.3.0
- v0.8.0
