"""Hikelog — personal housetrail manager by Marwan Helmy."""

from __future__ import annotations

__version__ = "1.2.0"
__author__ = "Marwan Helmy"
__email__ = "marwanabdelaal25@gmail.com"

from hikelog.errors import (
    HikelogError,
    StorageError,
    ValidationError,
    NotFoundError,
    ImportPipelineError,
    ExportError,
    MigrationError,
    PluginError,
    ConflictError,
    format_error,
    is_not_found,
    is_validation,
)
from hikelog.trail import Trail, PackInfo, TrailStatus, TrailCatalog
from hikelog.terrain import TerrainProfile, TerrainCatalog, VisitFrequency, ConditionsNeed
from hikelog.trailhead import Trailhead, TrailheadRegistry, AspectDirection
from hikelog.visit import VisitEvent, VisitLog, VisitPace
from hikelog.trip_log import TripEvent, TripLog, TripEventType, GearSchedule
from hikelog.schedule import ScheduleEngine, ScheduleEntry, ScheduleOptions, Season, compute_next_visit
from hikelog.tag import Tag, TagRegistry
from hikelog.notes import Note, NotesCollection, NoteKind
from hikelog.parser import (
    parse_date,
    parse_interval,
    parse_distance_km,
    parse_difficulty,
    parse_conditions,
    format_interval_days,
    format_distance_km,
)
from hikelog.validators import (
    validate_trail_name,
    validate_interval_days,
    validate_elevation_gain_m,
    validate_difficulty,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    # errors
    "HikelogError",
    "StorageError",
    "ValidationError",
    "NotFoundError",
    "ImportPipelineError",
    "ExportError",
    "MigrationError",
    "PluginError",
    "ConflictError",
    "format_error",
    "is_not_found",
    "is_validation",
    # trail
    "Trail",
    "PackInfo",
    "TrailStatus",
    "TrailCatalog",
    # terrain
    "TerrainProfile",
    "TerrainCatalog",
    "VisitFrequency",
    "ConditionsNeed",
    # trailhead
    "Trailhead",
    "TrailheadRegistry",
    "AspectDirection",
    # visit
    "VisitEvent",
    "VisitLog",
    "VisitPace",
    # care
    "TripEvent",
    "TripLog",
    "TripEventType",
    "GearSchedule",
    # schedule
    "ScheduleEngine",
    "ScheduleEntry",
    "ScheduleOptions",
    "Season",
    "compute_next_visit",
    # tags & notes
    "Tag",
    "TagRegistry",
    "Note",
    "NotesCollection",
    "NoteKind",
    # parser helpers
    "parse_date",
    "parse_interval",
    "parse_distance_km",
    "parse_difficulty",
    "parse_conditions",
    "format_interval_days",
    "format_distance_km",
    # validators
    "validate_trail_name",
    "validate_interval_days",
    "validate_elevation_gain_m",
    "validate_difficulty",
]
