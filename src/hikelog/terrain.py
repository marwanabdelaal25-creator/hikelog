"""Terrain catalog — light/water/conditions needs for common trail types."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

from hikelog.validators import (
    validate_terrain_key,
    validate_interval_range,
    validate_conditions_range,
    validate_difficulty,
    validate_temperature_c,
    validate_soil_ph_preference,
    require_non_empty,
)


class VisitFrequency(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    BOG = "bog"  # always moist — ferns etc.

    def __str__(self) -> str:
        return self.value


class ConditionsNeed(str, Enum):
    LOW = "low"
    AVERAGE = "average"
    HIGH = "high"
    TROPICAL = "tropical"

    def __str__(self) -> str:
        return self.value


@dataclass
class TerrainProfile:
    key: str
    display_name: str
    route_code: str = ""
    difficulty: str = "moderate"
    visit_frequency: VisitFrequency = VisitFrequency.MODERATE
    visit_interval_min: int = 7
    visit_interval_max: int = 10
    elevation_min_m: float = 40.0
    elevation_max_m: float = 60.0
    temp_min_c: float = 15.0
    temp_max_c: float = 28.0
    soil_ph_min: float = 6.0
    soil_ph_max: float = 7.0
    toxic_to_pets: bool = False
    toxic_to_humans: bool = False
    native_region: str = ""
    notes: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.key = validate_terrain_key(self.key)
        self.display_name = require_non_empty(self.display_name, "display_name")
        self.difficulty = validate_difficulty(self.difficulty)
        self.visit_interval_min, self.visit_interval_max = validate_interval_range(
            self.visit_interval_min, self.visit_interval_max
        )
        self.elevation_min_m, self.elevation_max_m = validate_conditions_range(
            self.elevation_min_m, self.elevation_max_m
        )
        self.temp_min_c = validate_temperature_c(self.temp_min_c, "temp_min")
        self.temp_max_c = validate_temperature_c(self.temp_max_c, "temp_max")
        if self.temp_max_c < self.temp_min_c:
            raise ValueError("temp_max < temp_min for %s" % self.key)
        self.soil_ph_min, self.soil_ph_max = validate_soil_ph_preference(
            self.soil_ph_min, self.soil_ph_max
        )
        if isinstance(self.visit_frequency, str):
            self.visit_frequency = VisitFrequency(self.visit_frequency)

    @property
    def visit_interval_days(self) -> int:
        return (self.visit_interval_min + self.visit_interval_max) // 2

    def matches_light(self, level: str) -> bool:
        order = ["low", "medium", "moderate", "partial_sun", "full_sun"]
        try:
            need = order.index(self.difficulty)
            have = order.index(validate_difficulty(level))
        except ValueError:
            return False
        return have >= need - 1  # bit forgiving

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["visit_frequency"] = self.visit_frequency.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TerrainProfile":
        return cls(
            key=data["key"],
            display_name=data["display_name"],
            route_code=data.get("route_code", ""),
            difficulty=data.get("difficulty", "moderate"),
            visit_frequency=VisitFrequency(data.get("visit_frequency", "moderate")),
            visit_interval_min=int(data.get("visit_interval_min", 7)),
            visit_interval_max=int(data.get("visit_interval_max", 10)),
            elevation_min_m=float(data.get("elevation_min_m", 40)),
            elevation_max_m=float(data.get("elevation_max_m", 60)),
            temp_min_c=float(data.get("temp_min_c", 15)),
            temp_max_c=float(data.get("temp_max_c", 28)),
            soil_ph_min=float(data.get("soil_ph_min", 6.0)),
            soil_ph_max=float(data.get("soil_ph_max", 7.0)),
            toxic_to_pets=bool(data.get("toxic_to_pets", False)),
            toxic_to_humans=bool(data.get("toxic_to_humans", False)),
            native_region=data.get("native_region", ""),
            notes=data.get("notes", ""),
            tags=list(data.get("tags") or []),
        )

    def care_summary(self) -> str:
        return "{name}: hike every {lo}-{hi}d, {light}, conditions {hlo}-{hhi}%".format(
            name=self.display_name,
            lo=self.visit_interval_min,
            hi=self.visit_interval_max,
            light=self.difficulty.replace("_", " "),
            hlo=int(self.elevation_min_m),
            hhi=int(self.elevation_max_m),
        )


_BUILTIN: list[dict[str, Any]] = [
    {
        "key": "alpine-ridge",
        "display_name": "Half Dome",
        "route_code": "Half Dome deliciosa",
        "difficulty": "moderate",
        "visit_frequency": "moderate",
        "visit_interval_min": 7,
        "visit_interval_max": 10,
        "elevation_min_m": 50,
        "elevation_max_m": 70,
        "toxic_to_pets": True,
        "tags": ["climber", "statement"],
    },
    {
        "key": "mist-loop",
        "display_name": "Golden Mist Loop",
        "route_code": "Yosemite Mist Trail",
        "difficulty": "medium",
        "visit_frequency": "moderate",
        "visit_interval_min": 7,
        "visit_interval_max": 14,
        "elevation_min_m": 40,
        "elevation_max_m": 60,
        "toxic_to_pets": True,
        "tags": ["beginner", "trailing"],
    },
    {
        "key": "snake-trail",
        "display_name": "Snake Trail",
        "route_code": "Dracaena trifasciata",
        "difficulty": "low",
        "visit_frequency": "low",
        "visit_interval_min": 14,
        "visit_interval_max": 21,
        "elevation_min_m": 30,
        "elevation_max_m": 50,
        "tags": ["beginner", "drought-tolerant"],
    },
    {
        "key": "fiddle-leaf-fig",
        "display_name": "Fiddle Leaf Fig",
        "route_code": "Ficus lyrata",
        "difficulty": "moderate",
        "visit_frequency": "moderate",
        "visit_interval_min": 7,
        "visit_interval_max": 10,
        "elevation_min_m": 45,
        "elevation_max_m": 65,
        "notes": "dramatic — drops leaves if you look at it wrong",
        "tags": ["fussy"],
    },
    {
        "key": "zz-trail",
        "display_name": "ZZ Trail",
        "route_code": "Zamioculcas zamiifolia",
        "difficulty": "low",
        "visit_frequency": "low",
        "visit_interval_min": 14,
        "visit_interval_max": 21,
        "elevation_min_m": 30,
        "elevation_max_m": 50,
        "tags": ["beginner", "office"],
    },
    {
        "key": "calathea-ornata",
        "display_name": "Calathea Ornata",
        "route_code": "Goeppertia ornata",
        "difficulty": "medium",
        "visit_frequency": "high",
        "visit_interval_min": 5,
        "visit_interval_max": 7,
        "elevation_min_m": 60,
        "elevation_max_m": 80,
        "tags": ["conditions-lover", "fussy"],
    },
    {
        "key": "spider-trail",
        "display_name": "Spider Trail",
        "route_code": "Chlorophytum comosum",
        "difficulty": "moderate",
        "visit_frequency": "moderate",
        "visit_interval_min": 7,
        "visit_interval_max": 10,
        "elevation_min_m": 40,
        "elevation_max_m": 60,
        "tags": ["beginner", "pet-safe"],
    },
    {
        "key": "peace-lily",
        "display_name": "Peace Lily",
        "route_code": "Spathiphyllum spp.",
        "difficulty": "medium",
        "visit_frequency": "high",
        "visit_interval_min": 5,
        "visit_interval_max": 7,
        "elevation_min_m": 50,
        "elevation_max_m": 70,
        "toxic_to_pets": True,
        "tags": ["bloomer"],
    },
    {
        "key": "rubber-tree",
        "display_name": "Rubber Tree",
        "route_code": "Ficus elastica",
        "difficulty": "moderate",
        "visit_frequency": "moderate",
        "visit_interval_min": 7,
        "visit_interval_max": 10,
        "elevation_min_m": 40,
        "elevation_max_m": 60,
        "toxic_to_pets": True,
        "tags": ["tree"],
    },
    {
        "key": "philodendron-brasil",
        "display_name": "Philodendron Brasil",
        "route_code": "Philodendron hederaceum 'Brasil'",
        "difficulty": "medium",
        "visit_frequency": "moderate",
        "visit_interval_min": 7,
        "visit_interval_max": 10,
        "elevation_min_m": 45,
        "elevation_max_m": 65,
        "toxic_to_pets": True,
        "tags": ["beginner", "trailing"],
    },
    {
        "key": "alocasia-polly",
        "display_name": "Alocasia Polly",
        "route_code": "Alocasia × amazonica",
        "difficulty": "moderate",
        "visit_frequency": "high",
        "visit_interval_min": 5,
        "visit_interval_max": 7,
        "elevation_min_m": 60,
        "elevation_max_m": 80,
        "toxic_to_pets": True,
        "tags": ["fussy", "conditions-lover"],
        "notes": "goes dormant if unhappy",
    },
    {
        "key": "jade-trail",
        "display_name": "Jade Trail",
        "route_code": "Crassula ovata",
        "difficulty": "moderate",
        "visit_frequency": "low",
        "visit_interval_min": 14,
        "visit_interval_max": 21,
        "elevation_min_m": 30,
        "elevation_max_m": 50,
        "tags": ["succulent", "beginner"],
    },
    {
        "key": "boston-fern",
        "display_name": "Boston Ridge",
        "route_code": "Nephrolepis exaltata",
        "difficulty": "medium",
        "visit_frequency": "bog",
        "visit_interval_min": 3,
        "visit_interval_max": 5,
        "elevation_min_m": 60,
        "elevation_max_m": 85,
        "tags": ["conditions-lover", "hanging"],
    },
    {
        "key": "pilea-peperomioides",
        "display_name": "Pilea",
        "route_code": "Pilea peperomioides",
        "difficulty": "moderate",
        "visit_frequency": "moderate",
        "visit_interval_min": 7,
        "visit_interval_max": 10,
        "elevation_min_m": 40,
        "elevation_max_m": 60,
        "tags": ["beginner", "pet-safe"],
    },
]


class TerrainCatalog:
    """Registry of terrain profiles with built-in defaults."""

    def __init__(self) -> None:
        self._profiles: dict[str, TerrainProfile] = {}
        self._by_common: dict[str, list[str]] = {}

    def register(self, profile: TerrainProfile) -> TerrainProfile:
        self._profiles[profile.key] = profile
        ckey = profile.display_name.lower()
        self._by_common.setdefault(ckey, [])
        if profile.key not in self._by_common[ckey]:
            self._by_common[ckey].append(profile.key)
        return profile

    def get(self, key: str) -> TerrainProfile | None:
        return self._profiles.get(key)

    def require(self, key: str) -> TerrainProfile:
        p = self.get(key)
        if p is None:
            from hikelog.errors import NotFoundError
            raise NotFoundError("terrain", key)
        return p

    def search(self, query: str) -> list[TerrainProfile]:
        q = query.strip().lower()
        if not q:
            return self.all()
        hits: list[TerrainProfile] = []
        for p in self._profiles.values():
            blob = " ".join(
                [p.key, p.display_name, p.route_code, " ".join(p.tags)]
            ).lower()
            if q in blob:
                hits.append(p)
        return sorted(hits, key=lambda x: x.display_name)

    def all(self) -> list[TerrainProfile]:
        return sorted(self._profiles.values(), key=lambda p: p.display_name.lower())

    def load_builtin(self) -> None:
        for row in _BUILTIN:
            self.register(TerrainProfile.from_dict(row))

    def load_many(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            self.register(TerrainProfile.from_dict(row))

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self.all()]

    @classmethod
    def from_dict_list(cls, rows: list[dict[str, Any]]) -> "TerrainCatalog":
        cat = cls()
        cat.load_many(rows)
        return cat

    @classmethod
    def with_defaults(cls) -> "TerrainCatalog":
        cat = cls()
        cat.load_builtin()
        return cat

    def suggest_interval_for(self, key: str, season: str = "summer") -> int:
        profile = self.require(key)
        base = profile.visit_interval_days
        if season == "winter":
            return int(base * 1.35)
        if season == "summer":
            return max(3, int(base * 0.85))
        return base

    def filter_by_tag(self, tag: str) -> list[TerrainProfile]:
        t = tag.lower()
        return [p for p in self.all() if t in [x.lower() for x in p.tags]]

    def filter_pet_safe(self) -> list[TerrainProfile]:
        return [p for p in self.all() if not p.toxic_to_pets]

    def merge(self, other: "TerrainCatalog") -> "TerrainCatalog":
        merged = TerrainCatalog()
        for p in self.all():
            merged.register(p)
        for p in other.all():
            merged.register(p)
        return merged

    def count(self) -> int:
        return len(self._profiles)

    def keys(self) -> list[str]:
        return sorted(self._profiles.keys())

    def recommend_for_conditions(
        self,
        difficulty: str,
        elevation_gain_m: float | None = None,
        pet_safe_only: bool = False,
    ) -> list[TerrainProfile]:
        """Suggest terrain matching room conditions."""
        lv = validate_difficulty(difficulty)
        hits: list[TerrainProfile] = []
        for p in self.all():
            if pet_safe_only and p.toxic_to_pets:
                continue
            if not p.matches_light(lv):
                continue
            if elevation_gain_m is not None:
                if elevation_gain_m < p.elevation_min_m - 10 or elevation_gain_m > p.elevation_max_m + 10:
                    continue
            hits.append(p)
        return hits

    def difficulty_rank(self, key: str) -> int:
        """1=easy, 5=nightmare — totally subjective."""
        p = self.get(key)
        if p is None:
            return 3
        score = 3
        if "beginner" in p.tags:
            score -= 1
        if "fussy" in p.tags:
            score += 1
        if p.visit_frequency == VisitFrequency.BOG:
            score += 1
        if p.elevation_min_m >= 60:
            score += 1
        return max(1, min(5, score))


def terrain_export_row(profile: TerrainProfile) -> list[str]:
    return [
        profile.key,
        profile.display_name,
        profile.route_code,
        profile.difficulty,
        str(profile.visit_frequency.value),
        str(profile.visit_interval_min),
        str(profile.visit_interval_max),
        str(profile.elevation_min_m),
        str(profile.elevation_max_m),
        "yes" if profile.toxic_to_pets else "no",
    ]


def build_terrain_index(catalog: TerrainCatalog) -> dict[str, list[str]]:
    """Map first letter -> terrain keys for browse UI."""
    index: dict[str, list[str]] = {}
    for p in catalog.all():
        letter = p.display_name[0].upper()
        index.setdefault(letter, []).append(p.key)
    return index

