"""Tests for cross-reference detection and context window building."""

import pytest
from unittest.mock import patch, MagicMock

from backend.retrieval.cross_ref import detect_cross_references, fetch_cross_referenced_chunks
from backend.retrieval.context import build_context_window


# ---------------------------------------------------------------------------
# Cross-reference detection tests
# ---------------------------------------------------------------------------

class TestDetectCrossReferences:
    def test_see_also_section(self):
        text = "For penalties, see also § 940.01 for first degree homicide."
        refs = detect_cross_references(text)
        assert "940.01" in refs

    def test_see_section(self):
        text = "See section 346.63 for OWI provisions."
        refs = detect_cross_references(text)
        assert "346.63" in refs

    def test_pursuant_to(self):
        text = "Pursuant to § 968.24, an officer may detain..."
        refs = detect_cross_references(text)
        assert "968.24" in refs

    def test_under_section(self):
        text = "Under section 941.20, carrying firearms is regulated."
        refs = detect_cross_references(text)
        assert "941.20" in refs

    def test_chapter_reference(self):
        text = "Chapter 943 applies to property crimes."
        refs = detect_cross_references(text)
        assert "943" in refs

    def test_no_references(self):
        text = "This is a plain text with no legal references."
        refs = detect_cross_references(text)
        assert refs == []

    def test_multiple_references(self):
        text = "See also § 940.01 and under section 346.63, and Chapter 943 applies."
        refs = detect_cross_references(text)
        assert "940.01" in refs
        assert "346.63" in refs
        assert "943" in refs

    def test_deduplication(self):
        text = "See § 940.01 and see also § 940.01 again."
        refs = detect_cross_references(text)
        assert refs.count("940.01") == 1


# ---------------------------------------------------------------------------
# Fetch cross-referenced chunks tests
# ---------------------------------------------------------------------------

class TestFetchCrossReferencedChunks:
    def test_fetches_statute_reference(self, mock_chroma_collection):
        results = fetch_cross_referenced_chunks(
            ["940.01"], collection=mock_chroma_collection, max_chunks_per_ref=2
        )
        mock_chroma_collection.get.assert_called()
        assert len(results) <= 2

    def test_empty_references(self, mock_chroma_collection):
        results = fetch_cross_referenced_chunks([], collection=mock_chroma_collection)
        assert results == []

    def test_chapter_reference_uses_chapter_field(self, mock_chroma_collection):
        fetch_cross_referenced_chunks(
            ["943"], collection=mock_chroma_collection
        )
        call_args = mock_chroma_collection.get.call_args
        assert "chapter_numbers" in str(call_args)


# ---------------------------------------------------------------------------
# Context window building tests
# ---------------------------------------------------------------------------

class TestBuildContextWindow:
    @patch("backend.retrieval.context.detect_cross_references", return_value=[])
    @patch("backend.retrieval.context.fetch_cross_referenced_chunks", return_value=[])
    def test_respects_token_limit(self, mock_fetch, mock_detect, sample_search_results):
        result = build_context_window(sample_search_results, token_limit=50)
        assert result["total_tokens"] <= 50

    @patch("backend.retrieval.context.detect_cross_references", return_value=[])
    @patch("backend.retrieval.context.fetch_cross_referenced_chunks", return_value=[])
    def test_returns_required_keys(self, mock_fetch, mock_detect, sample_search_results):
        result = build_context_window(sample_search_results, token_limit=10000)
        assert "context_text" in result
        assert "sources" in result
        assert "cross_refs_followed" in result
        assert "total_tokens" in result

    @patch("backend.retrieval.context.detect_cross_references", return_value=["940.01"])
    @patch("backend.retrieval.context.fetch_cross_referenced_chunks")
    def test_follows_cross_references(self, mock_fetch, mock_detect, sample_search_results):
        mock_fetch.return_value = [{
            "id": "xref_1",
            "document": "Cross-referenced statute text about 940.01",
            "metadata": {"source_file": "ref.pdf", "context_header": "", "statute_numbers": "940.01",
                         "source_type": "statute", "start_page": 1, "title": "ref"},
        }]

        result = build_context_window(sample_search_results, token_limit=10000)
        assert "940.01" in result["cross_refs_followed"]
        # The cross-ref chunk should be in sources
        xref_ids = [s["id"] for s in result["sources"]]
        assert "xref_1" in xref_ids

    @patch("backend.retrieval.context.detect_cross_references", return_value=[])
    @patch("backend.retrieval.context.fetch_cross_referenced_chunks", return_value=[])
    def test_deduplicates_chunks(self, mock_fetch, mock_detect):
        chunks = [
            {"id": "same_id", "document": "text", "metadata": {"source_file": "", "context_header": "", "statute_numbers": "", "source_type": "", "start_page": 1, "title": ""}},
            {"id": "same_id", "document": "text", "metadata": {"source_file": "", "context_header": "", "statute_numbers": "", "source_type": "", "start_page": 1, "title": ""}},
        ]
        result = build_context_window(chunks, token_limit=10000)
        assert len(result["sources"]) == 1

    @patch("backend.retrieval.context.detect_cross_references", return_value=[])
    @patch("backend.retrieval.context.fetch_cross_referenced_chunks", return_value=[])
    def test_empty_input(self, mock_fetch, mock_detect):
        result = build_context_window([], token_limit=4000)
        assert result["context_text"] == ""
        assert result["sources"] == []
        assert result["total_tokens"] == 0
