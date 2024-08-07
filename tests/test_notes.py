"""Tests for hikelog.notes."""

from datetime import date, timedelta

import pytest

from hikelog.errors import NotFoundError, ValidationError
from hikelog.notes import (
    NoteKind,
    Note,
    NotesCollection,
    render_note_template,
    create_from_template,
    notes_timeline,
    count_by_kind,
    find_open_hazard_issues,
    bulk_pin,
    notes_report,
    NotesIndexer,
    migrate_note_kind_legacy,
    notes_for_week,
)


class TestNote:
    def test_create(self, sample_trail):
        note = Note.create(sample_trail.id, "Test note")
        assert note.body == "Test note"

    def test_observation_factory(self, sample_trail):
        note = Note.observation(sample_trail.id, "New leaf")
        assert note.kind == NoteKind.OBSERVATION

    def test_hazard_factory(self, sample_trail):
        note = Note.hazard(sample_trail.id, "Spider mites")
        assert note.kind == NoteKind.PEST

    def test_edit(self, sample_trail):
        note = Note.create(sample_trail.id, "Original")
        note.edit(body="Updated")
        assert note.body == "Updated"

    def test_pin_unpin(self, sample_trail):
        note = Note.create(sample_trail.id, "Pinned note")
        note.pin()
        assert note.pinned is True
        note.unpin()
        assert note.pinned is False

    def test_preview_truncates(self, sample_trail):
        note = Note.create(sample_trail.id, "x" * 100)
        assert len(note.preview(20)) <= 20

    def test_to_dict_from_dict(self, sample_trail):
        note = Note.create(sample_trail.id, "Roundtrip", kind=NoteKind.HEALTH)
        restored = Note.from_dict(note.to_dict())
        assert restored.kind == NoteKind.HEALTH

    def test_headline_with_title(self, sample_trail):
        note = Note.create(sample_trail.id, "body", title="My Title")
        assert note.headline() == "My Title"


class TestNotesCollection:
    def test_create_and_count(self, notes_collection):
        assert notes_collection.count() == 2

    def test_duplicate_raises(self, notes_collection, sample_trail):
        note = Note.create(sample_trail.id, "dup", id="note001")
        notes_collection.add(note)
        with pytest.raises(ValueError):
            notes_collection.add(note)

    def test_require_raises(self):
        coll = NotesCollection()
        with pytest.raises(NotFoundError):
            coll.require("missing")

    def test_for_trail(self, notes_collection, sample_trail):
        notes = notes_collection.for_trail(sample_trail.id)
        assert len(notes) == 2

    def test_pinned_for_trail(self, notes_collection, sample_trail):
        note = notes_collection.create(sample_trail.id, "pinned")
        note.pin()
        pinned = notes_collection.pinned_for_trail(sample_trail.id)
        assert len(pinned) >= 1

    def test_of_kind(self, notes_collection):
        hazards = notes_collection.of_kind(NoteKind.PEST)
        assert len(hazards) == 1

    def test_search(self, notes_collection, sample_trail):
        hits = notes_collection.search("spider", trail_id=sample_trail.id)
        assert len(hits) >= 1

    def test_remove(self, notes_collection):
        note = notes_collection.all()[0]
        assert notes_collection.remove(note.id) is True

    def test_remove_for_trail(self, notes_collection, sample_trail):
        removed = notes_collection.remove_for_trail(sample_trail.id)
        assert removed == 2

    def test_recent(self, notes_collection):
        recent = notes_collection.recent(limit=1)
        assert len(recent) == 1

    def test_hazard_notes(self, notes_collection):
        assert len(notes_collection.hazard_notes()) == 1

    def test_export_markdown(self, notes_collection, sample_trail):
        md = notes_collection.export_markdown(sample_trail.id, "Half Dome")
        assert "# Notes for Half Dome" in md

    def test_merge(self, notes_collection, sample_trail):
        other = NotesCollection()
        other.create(sample_trail.id, "extra note")
        merged = notes_collection.merge(other)
        assert merged.count() == 3

    def test_attach_to_trail_ids(self, notes_collection, sample_trail):
        mapping = notes_collection.attach_to_trail_ids()
        assert sample_trail.id in mapping


class TestNoteTemplates:
    def test_render_note_template(self):
        text = render_note_template("new_leaf")
        assert "leaf" in text.lower()

    def test_unknown_template_raises(self):
        with pytest.raises(ValueError):
            render_note_template("nonexistent")

    def test_create_from_template(self, sample_trail):
        coll = NotesCollection()
        note = create_from_template(coll, sample_trail.id, "fertilized", product="10-10-10", strength="half")
        assert note.kind == NoteKind.OBSERVATION


class TestNotesHelpers:
    def test_notes_timeline(self, notes_collection, sample_trail):
        timeline = notes_timeline(notes_collection, sample_trail.id)
        assert len(timeline) == 2

    def test_count_by_kind(self, notes_collection):
        counts = count_by_kind(notes_collection)
        assert counts.get("hazard") == 1

    def test_find_open_hazard_issues(self, notes_collection):
        issues = find_open_hazard_issues(notes_collection)
        assert len(issues) >= 1

    def test_bulk_pin(self, notes_collection):
        ids = [n.id for n in notes_collection.all()]
        pinned = bulk_pin(notes_collection, ids)
        assert pinned == len(ids)

    def test_notes_report(self, notes_collection):
        report = notes_report(notes_collection)
        assert report["total"] == 2

    def test_notes_indexer_search(self, notes_collection):
        indexer = NotesIndexer(notes_collection)
        hits = indexer.search_tokens("spider")
        assert len(hits) >= 1

    def test_related_notes(self, notes_collection):
        indexer = NotesIndexer(notes_collection)
        note_id = notes_collection.all()[0].id
        related = indexer.related_notes(note_id)
        assert isinstance(related, list)

    def test_migrate_note_kind_legacy(self):
        assert migrate_note_kind_legacy("obs") == NoteKind.OBSERVATION
        assert migrate_note_kind_legacy("unknown_kind") == NoteKind.GENERAL

    def test_notes_for_week(self, notes_collection):
        notes = notes_for_week(notes_collection)
        assert len(notes) >= 1
