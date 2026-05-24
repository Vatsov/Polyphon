"""Tests for text chunker."""

from polyphon.core.chunker import chunk_text


def test_empty_text_returns_empty_list() -> None:
    assert chunk_text("") == []


def test_short_text_is_single_chunk() -> None:
    result = chunk_text("Здравейте.")
    assert result == ["Здравейте."]


def test_respects_max_chars() -> None:
    text = "A" * 100 + ". " + "B" * 100 + "."
    chunks = chunk_text(text, max_chars=120)
    assert all(len(c) <= 120 for c in chunks)


def test_splits_on_sentence_boundary() -> None:
    text = "Първо изречение. Второ изречение."
    chunks = chunk_text(text, max_chars=20)
    assert len(chunks) == 2


def test_no_empty_chunks() -> None:
    text = "Едно.  Две.   Три."
    chunks = chunk_text(text)
    assert all(c.strip() for c in chunks)
