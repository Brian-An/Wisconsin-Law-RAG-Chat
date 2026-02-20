"""Tests for the retrieval layer: query expansion, hybrid search, and relevance boosting."""

import pytest
from unittest.mock import patch, MagicMock

from backend.retrieval.query_expand import enhance_query
from backend.retrieval.relevnace_boost import apply_relevance_boost


# ---------------------------------------------------------------------------
# Query expansion tests
# ---------------------------------------------------------------------------

class TestEnhanceQuery:
    def test_expands_owi(self):
        result = enhance_query("What is OWI?")
        assert "Operating While Intoxicated" in result["corrected_text"]
        assert result["original"] == "What is OWI?"

    def test_maps_colloquialisms(self):
        result = enhance_query("What happens when someone is pulled over?")
        assert "traffic stop" in result["semantic_query"].lower() or \
               "Terry stop" in result["semantic_query"]

    def test_extracts_statute_number(self):
        result = enhance_query("What does 940.01 say?")
        assert "940.01" in result["exact_keywords"]

    def test_extracts_case_citation(self):
        result = enhance_query("Tell me about 2023 WI App 45")
        assert any("2023" in kw for kw in result["exact_keywords"])

    def test_chapter_hints_for_traffic(self):
        result = enhance_query("What are the traffic violation rules?")
        assert "346" in result["chapter_hints"]

    def test_multiple_abbreviations(self):
        result = enhance_query("The LEO conducted SFSTs during the OWI stop")
        assert "Law Enforcement Officer" in result["corrected_text"]
        assert "Standardized Field Sobriety Tests" in result["corrected_text"]
        assert "Operating While Intoxicated" in result["corrected_text"]

    def test_no_expansion_needed(self):
        result = enhance_query("What is first degree homicide?")
        assert result["corrected_text"] == "What is first degree homicide?"
        assert result["original"] == "What is first degree homicide?"

    def test_returns_all_keys(self):
        result = enhance_query("test query")
        assert "original" in result
        assert "corrected_text" in result
        assert "exact_keywords" in result
        assert "semantic_query" in result
        assert "chapter_hints" in result


# ---------------------------------------------------------------------------
# Relevance boost tests
# ---------------------------------------------------------------------------

class TestRelevanceBoost:
    def test_drops_superseded(self, sample_search_results):
        sample_search_results[0]["metadata"]["superseded"] = True
        enhanced = {"original": "test", "exact_keywords": [], "chapter_hints": []}
        result = apply_relevance_boost(sample_search_results, enhanced)
        ids = [r["id"] for r in result]
        assert "chunk_1" not in ids

    def test_policy_query_boosts_local_department(self, sample_search_results):
        enhanced = {"original": "What is the department policy on arrests?", "exact_keywords": [], "chapter_hints": []}
        result = apply_relevance_boost(sample_search_results, enhanced)
        # chunk_5 has jurisdiction=local_department and should get 1.5x
        chunk_5 = next(r for r in result if r["id"] == "chunk_5")
        assert chunk_5["boosted_score"] == pytest.approx(0.015 * 1.5, rel=0.01)

    def test_state_jurisdiction_boost(self, sample_search_results):
        enhanced = {"original": "test", "exact_keywords": [], "chapter_hints": []}
        result = apply_relevance_boost(sample_search_results, enhanced)
        # chunk_1 has jurisdiction=state, should get 1.2x
        chunk_1 = next(r for r in result if r["id"] == "chunk_1")
        assert chunk_1["boosted_score"] == pytest.approx(0.030 * 1.2, rel=0.01)

    def test_exact_statute_match_boost(self, sample_search_results):
        enhanced = {"original": "What does 940.01 say?", "exact_keywords": ["940.01"], "chapter_hints": []}
        result = apply_relevance_boost(sample_search_results, enhanced)
        # chunk_1 has statute_numbers="940.01", should get 1.2 (state) * 1.3 (exact)
        chunk_1 = next(r for r in result if r["id"] == "chunk_1")
        assert chunk_1["boosted_score"] == pytest.approx(0.030 * 1.2 * 1.3, rel=0.01)

    def test_sorted_by_boosted_score(self, sample_search_results):
        enhanced = {"original": "test", "exact_keywords": [], "chapter_hints": []}
        result = apply_relevance_boost(sample_search_results, enhanced)
        scores = [r["boosted_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_empty_results(self):
        enhanced = {"original": "test", "exact_keywords": [], "chapter_hints": []}
        result = apply_relevance_boost([], enhanced)
        assert result == []


# ---------------------------------------------------------------------------
# Hybrid search tests (mocked)
# ---------------------------------------------------------------------------

class TestHybridSearch:
    @patch("backend.retrieval.hybrid_search.get_chroma_client")
    @patch("backend.retrieval.hybrid_search.get_or_create_collection")
    @patch("backend.retrieval.hybrid_search.generate_embeddings")
    @patch("backend.retrieval.hybrid_search._get_bm25_index")
    def test_returns_fused_results(
        self, mock_bm25, mock_embed, mock_collection_fn, mock_client
    ):
        from backend.retrieval.hybrid_search import execute_hybrid_search

        # Setup mocks
        mock_collection = MagicMock()
        mock_collection_fn.return_value = mock_collection
        mock_embed.return_value = [[0.1] * 1536]

        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["doc 1", "doc 2"]],
            "metadatas": [[{"statute_numbers": "940.01", "superseded": False}, {"statute_numbers": "", "superseded": False}]],
            "distances": [[0.1, 0.3]],
        }

        # BM25 mock
        mock_bm25_obj = MagicMock()
        mock_bm25_obj.get_scores.return_value = [5.0, 3.0, 1.0]
        mock_bm25.return_value = (
            mock_bm25_obj,
            ["id1", "id2", "id3"],
            ["doc 1", "doc 2", "doc 3"],
            [{"statute_numbers": "940.01"}, {"statute_numbers": ""}, {"statute_numbers": "346.63"}],
        )

        enhanced = {
            "original": "test",
            "corrected_text": "test",
            "semantic_query": "test query",
            "exact_keywords": [],
            "chapter_hints": [],
        }

        results = execute_hybrid_search(enhanced, n_results=5)

        assert len(results) > 0
        assert all("rrf_score" in r for r in results)
        assert all("id" in r and "document" in r and "metadata" in r for r in results)

        # id1 appears in both semantic and BM25, should have highest RRF
        if len(results) >= 2:
            assert results[0]["id"] == "id1"

    @patch("backend.retrieval.hybrid_search.get_chroma_client")
    @patch("backend.retrieval.hybrid_search.get_or_create_collection")
    @patch("backend.retrieval.hybrid_search.generate_embeddings")
    @patch("backend.retrieval.hybrid_search._get_bm25_index")
    def test_rrf_scores_are_positive(
        self, mock_bm25, mock_embed, mock_collection_fn, mock_client
    ):
        from backend.retrieval.hybrid_search import execute_hybrid_search

        mock_collection = MagicMock()
        mock_collection_fn.return_value = mock_collection
        mock_embed.return_value = [[0.1] * 1536]

        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc 1"]],
            "metadatas": [[{"statute_numbers": ""}]],
            "distances": [[0.1]],
        }

        mock_bm25_obj = MagicMock()
        mock_bm25_obj.get_scores.return_value = [2.0]
        mock_bm25.return_value = (mock_bm25_obj, ["id1"], ["doc 1"], [{"statute_numbers": ""}])

        enhanced = {
            "original": "t",
            "corrected_text": "t",
            "semantic_query": "t",
            "exact_keywords": [],
            "chapter_hints": [],
        }

        results = execute_hybrid_search(enhanced, n_results=5)
        for r in results:
            assert r["rrf_score"] > 0
