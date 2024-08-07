"""Tests for hikelog.search."""

from hikelog.search import SearchHit, LogbookSearch


class TestSearchHit:
    def test_dataclass(self):
        hit = SearchHit(kind="trail", id="p1", title="Ridge Trail", snippet="...", score=1.0)
        assert hit.score == 1.0


class TestLogbookSearch:
    def test_search_trails_by_name(self, populated_storage, sample_trail):
        search = LogbookSearch(populated_storage)
        hits = search.search_trails("Half Dome")
        assert len(hits) >= 1
        assert hits[0].kind == "trail"

    def test_search_trails_partial(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_trails("Snake")
        assert len(hits) >= 1

    def test_search_trails_empty_query(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_trails("")
        assert hits == []

    def test_search_trails_no_match(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_trails("zzzznonexistent")
        assert hits == []

    def test_search_trails_by_terrain(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_trails("mist-loop")
        assert len(hits) >= 1

    def test_search_notes(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_notes("unfurling")
        assert len(hits) >= 1
        assert hits[0].kind == "note"

    def test_search_notes_no_match(self, populated_storage):
        search = LogbookSearch(populated_storage)
        assert search.search_notes("xyznotfound") == []

    def test_search_trip_logs(self, populated_storage):
        populated_storage.create_trip_log({
            "id": "cl1",
            "trail_id": "trail001",
            "action": "fertilize",
            "details": "Applied fish emulsion",
        })
        search = LogbookSearch(populated_storage)
        hits = search.search_trip_logs("fertilize")
        assert len(hits) >= 1

    def test_search_all_combined(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_all("Half Dome")
        assert len(hits) >= 1

    def test_search_all_with_limit(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_all("trail", limit=1)
        assert len(hits) <= 1

    def test_search_all_sorted_by_score(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_all("Half Dome")
        if len(hits) >= 2:
            assert hits[0].score >= hits[1].score

    def test_to_dicts(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_trails("Half Dome")
        dicts = search.to_dicts(hits)
        assert dicts[0]["kind"] == "trail"
        assert "score" in dicts[0]

    def test_snippet_truncation(self, populated_storage):
        populated_storage.create_note({
            "id": "long_note",
            "trail_id": "trail001",
            "body": "x" * 200,
            "title": "Long",
        })
        search = LogbookSearch(populated_storage)
        hits = search.search_notes("Long")
        if hits:
            assert len(hits[0].snippet) <= 120

    def test_case_insensitive(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_trails("half dome")
        assert len(hits) >= 1

    def test_multiple_tokens(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_trails("Snake Trail")
        assert len(hits) >= 1

    def test_metadata_searchable(self, populated_storage, sample_trail):
        populated_storage.update_trail(sample_trail.id, {
            "metadata": {"notes": "special keyword xyzzy"},
        })
        search = LogbookSearch(populated_storage)
        hits = search.search_trails("xyzzy")
        assert len(hits) >= 1

    def test_trip_log_missing_id(self, populated_storage):
        populated_storage.create_trip_log({
            "trail_id": "trail001",
            "action": "inspect",
            "details": "Checked roots",
        })
        search = LogbookSearch(populated_storage)
        hits = search.search_trip_logs("roots")
        assert len(hits) >= 1

    def test_whitespace_tokens_stripped(self, populated_storage):
        search = LogbookSearch(populated_storage)
        hits = search.search_trails("  Half Dome   ")
        assert len(hits) >= 1
