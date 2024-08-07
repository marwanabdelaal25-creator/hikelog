"""Tests for hikelog.tag."""

import pytest

from hikelog.errors import ConflictError, NotFoundError
from hikelog.tag import (
    Tag,
    TagRegistry,
    TagGroup,
    TagGroupRegistry,
    filter_trails_by_tag_names,
    rename_tag,
    unused_tags,
    export_tags_csv,
    tag_stats,
    apply_tags_to_trail,
)


class TestTag:
    def test_create(self):
        tag = Tag.create("beginner", color="#4caf50")
        assert tag.name == "beginner"

    def test_slug_auto_generated(self):
        tag = Tag.create("pet safe")
        assert tag.slug == "pet-safe"

    def test_to_dict_from_dict(self):
        tag = Tag.create("fussy", id="tag001", color="#ff9800")
        restored = Tag.from_dict(tag.to_dict())
        assert restored.name == "fussy"

    def test_display_with_color(self):
        tag = Tag.create("beginner", color="#4caf50")
        assert "#4caf50" in tag.display()

    def test_touch_count(self):
        tag = Tag.create("test")
        tag.touch_count(5)
        assert tag.trail_count == 5


class TestTagRegistry:
    def test_add_and_get(self, tag_registry):
        tag = tag_registry.get("tag001")
        assert tag is not None

    def test_duplicate_slug_raises(self):
        reg = TagRegistry()
        reg.add(Tag.create("beginner", id="t1", slug="beginner"))
        with pytest.raises(ConflictError):
            reg.add(Tag.create("Beginner2", id="t2", slug="beginner"))

    def test_get_by_slug(self, tag_registry):
        tag = tag_registry.get_by_slug("beginner")
        assert tag is not None

    def test_get_by_name(self, tag_registry):
        tag = tag_registry.get_by_name("pet-safe")
        assert tag is not None

    def test_require_raises(self):
        reg = TagRegistry()
        with pytest.raises(NotFoundError):
            reg.require("missing")

    def test_find_or_create_existing(self, tag_registry):
        tag = tag_registry.find_or_create("beginner")
        assert tag.id == "tag001"

    def test_find_or_create_new(self, tag_registry):
        tag = tag_registry.find_or_create("conditions-lover")
        assert tag.color is not None

    def test_search(self, tag_registry):
        hits = tag_registry.search("pet")
        assert len(hits) >= 1

    def test_remove(self, tag_registry):
        assert tag_registry.remove("tag001") is True

    def test_recalculate_counts(self, tag_registry):
        tag_registry.recalculate_counts({"p1": ["tag001", "tag002"], "p2": ["tag001"]})
        assert tag_registry.get("tag001").trail_count == 2

    def test_default_tags(self):
        reg = TagRegistry()
        reg.default_tags()
        assert reg.count() >= 4

    def test_merge(self, tag_registry):
        other = TagRegistry()
        other.add(Tag.create("new-tag", id="t99"))
        merged = tag_registry.merge(other)
        assert merged.count() == 3

    def test_ids_for_names(self, tag_registry):
        ids = tag_registry.ids_for_names(["beginner", "pet-safe"])
        assert len(ids) == 2

    def test_tag_cloud(self, tag_registry):
        tag_registry.get("tag001").touch_count(10)
        cloud = tag_registry.tag_cloud()
        assert cloud[0][1] == 10


class TestTagGroup:
    def test_tag_group_registry(self, tag_registry):
        grp_reg = TagGroupRegistry()
        grp = TagGroup(name="Care Level", tag_ids=["tag001"])
        grp_reg.add(grp)
        tags = grp_reg.tags_in_group(grp.id, tag_registry)
        assert len(tags) == 1

    def test_from_dict_list(self):
        reg = TagGroupRegistry.from_dict_list([
            {"name": "Group", "tag_ids": [], "id": "g1"},
        ])
        assert reg.get("g1") is not None


class TestTagHelpers:
    def test_filter_trails_by_tag_names(self, tag_registry, sample_trail):
        sample_trail.attach_tag("tag001")
        found = filter_trails_by_tag_names(tag_registry, [sample_trail], ["beginner"])
        assert sample_trail in found

    def test_filter_match_all(self, tag_registry, sample_trail):
        sample_trail.attach_tag("tag001")
        sample_trail.attach_tag("tag002")
        found = filter_trails_by_tag_names(
            tag_registry, [sample_trail], ["beginner", "pet-safe"], match_all=True
        )
        assert sample_trail in found

    def test_rename_tag(self, tag_registry):
        tag = rename_tag(tag_registry, "tag001", "easy-care")
        assert tag.name == "easy-care"

    def test_unused_tags(self, tag_registry):
        unused = unused_tags(tag_registry, {"p1": ["tag001"]})
        assert any(t.id == "tag002" for t in unused)

    def test_export_tags_csv(self, tag_registry):
        rows = export_tags_csv(tag_registry)
        assert rows[0][0] == "id"

    def test_tag_stats(self, tag_registry):
        stats = tag_stats(tag_registry)
        assert stats["count"] == 2

    def test_tag_stats_empty(self):
        stats = tag_stats(TagRegistry())
        assert stats["count"] == 0

    def test_apply_tags_to_trail(self, tag_registry, sample_trail):
        ids = apply_tags_to_trail(sample_trail, tag_registry, ["beginner"])
        assert len(ids) >= 1
        assert sample_trail.tag_ids
