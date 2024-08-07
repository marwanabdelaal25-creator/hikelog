"""Tests for hikelog.terrain."""

import pytest

from hikelog.errors import NotFoundError
from hikelog.terrain import (
    VisitFrequency,
    ConditionsNeed,
    TerrainProfile,
    TerrainCatalog,
    terrain_export_row,
    build_terrain_index,
)


class TestTerrainProfile:
    def test_create(self, sample_terrain):
        assert sample_terrain.key == "mist-loop"
        assert sample_terrain.display_name == "Golden Mist Loop"

    def test_visit_interval_days(self, sample_terrain):
        assert sample_terrain.visit_interval_days == 10

    def test_matches_light(self, sample_terrain):
        assert sample_terrain.matches_light("medium") is True

    def test_to_dict_from_dict(self, sample_terrain):
        restored = TerrainProfile.from_dict(sample_terrain.to_dict())
        assert restored.key == sample_terrain.key

    def test_care_summary(self, sample_terrain):
        summary = sample_terrain.care_summary()
        assert "Golden Mist Loop" in summary

    def test_temp_max_less_than_min_raises(self):
        with pytest.raises(ValueError):
            TerrainProfile(
                key="bad-terrain",
                display_name="Bad",
                temp_min_c=30.0,
                temp_max_c=10.0,
            )


class TestVisitFrequency:
    def test_str(self):
        assert str(VisitFrequency.LOW) == "low"


class TestTerrainCatalog:
    def test_register_and_get(self, terrain_catalog, sample_terrain):
        assert terrain_catalog.get(sample_terrain.key) is not None

    def test_require_raises(self):
        cat = TerrainCatalog()
        with pytest.raises(NotFoundError):
            cat.require("missing")

    def test_search(self, terrain_catalog):
        hits = terrain_catalog.search("mist-loop")
        assert len(hits) >= 1

    def test_search_empty_returns_all(self, terrain_catalog):
        assert len(terrain_catalog.search("")) >= 1

    def test_load_builtin(self):
        cat = TerrainCatalog()
        cat.load_builtin()
        assert cat.count() >= 10

    def test_with_defaults(self):
        cat = TerrainCatalog.with_defaults()
        assert cat.get("alpine-ridge") is not None

    def test_suggest_interval_winter(self, terrain_catalog):
        interval = terrain_catalog.suggest_interval_for("snake-trail", season="winter")
        assert interval > terrain_catalog.require("snake-trail").visit_interval_days

    def test_suggest_interval_summer(self, terrain_catalog):
        interval = terrain_catalog.suggest_interval_for("snake-trail", season="summer")
        assert interval <= terrain_catalog.require("snake-trail").visit_interval_days

    def test_filter_by_tag(self, terrain_catalog):
        beginner = terrain_catalog.filter_by_tag("beginner")
        assert len(beginner) >= 1

    def test_filter_pet_safe(self, terrain_catalog):
        safe = terrain_catalog.filter_pet_safe()
        assert all(not p.toxic_to_pets for p in safe)

    def test_merge(self, terrain_catalog, sample_terrain):
        other = TerrainCatalog()
        other.register(TerrainProfile(
            key="custom-fern",
            display_name="Custom Ridge",
        ))
        merged = terrain_catalog.merge(other)
        assert merged.get("custom-fern") is not None

    def test_keys(self, terrain_catalog):
        keys = terrain_catalog.keys()
        assert "mist-loop" in keys

    def test_recommend_for_conditions(self, terrain_catalog):
        hits = terrain_catalog.recommend_for_conditions("medium", elevation_gain_m=50)
        assert len(hits) >= 1

    def test_recommend_pet_safe_only(self, terrain_catalog):
        hits = terrain_catalog.recommend_for_conditions("moderate", pet_safe_only=True)
        assert all(not p.toxic_to_pets for p in hits)

    def test_difficulty_rank_beginner(self, terrain_catalog):
        rank = terrain_catalog.difficulty_rank("snake-trail")
        assert rank <= 3

    def test_difficulty_rank_fussy(self, terrain_catalog):
        rank = terrain_catalog.difficulty_rank("fiddle-leaf-fig")
        assert rank >= 3

    def test_difficulty_rank_unknown(self, terrain_catalog):
        assert terrain_catalog.difficulty_rank("nonexistent") == 3

    def test_from_dict_list(self, sample_terrain):
        cat = TerrainCatalog.from_dict_list([sample_terrain.to_dict()])
        assert cat.get(sample_terrain.key) is not None

    def test_to_dict_list(self, terrain_catalog):
        rows = terrain_catalog.to_dict_list()
        assert len(rows) >= 1


class TestTerrainHelpers:
    def test_terrain_export_row(self, sample_terrain):
        row = terrain_export_row(sample_terrain)
        assert row[0] == sample_terrain.key

    def test_build_terrain_index(self, terrain_catalog):
        index = build_terrain_index(terrain_catalog)
        assert "G" in index or "P" in index
