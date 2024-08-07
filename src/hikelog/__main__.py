"""Allow `python -m hikelog` invocation."""

from hikelog.cli import main

__doc__ = """
Entry point for the hikelog CLI.

Examples:
  python -m hikelog init
  python -m hikelog trail-add "Half Dome" --terrain alpine-ridge
  python -m hikelog visit <trail-id> --km 8.4
  python -m hikelog schedule --week
  python -m hikelog export logbook.json

Environment:
  HIKELOG_HOME  Directory for default logbook.json (default: ~/.hikelog/)
"""

if __name__ == "__main__":
    raise SystemExit(main())
