"""Tests for the API layer (routes, middleware, response format)."""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from backend.main import app
from backend.generation.formatter import DISCLAIMER


client = TestClient(app)

# Shared mock return values
_MOCK_ENHANCED = {
    "original": "What is OWI?",
    "corrected_text": "What is OWI (Operating While Intoxicated)?",
    "exact_keywords": [],
    "semantic_query": "What is OWI (Operating While Intoxicated)?",
    "chapter_hints": [],
}

_MOCK_SEARCH_RESULTS = [
    {
        "id": "c1",
        "document": "OWI is defined under section 346.63...",
        "metadata": {
            "doc_id": "c1",
            "source_type": "statute",
            "jurisdiction": "state",
            "superseded": False,
            "title": "statue_2",
            "source_file": "data/statues/statue_2.pdf",
            "statute_numbers": "346.63",
            "case_citations": "",
            "chapter_numbers": "346",
            "context_header": "Chapter 346 > § 346.63",
            "start_page": 1,
            "token_count": 50,
        },
        "rrf_score": 0.030,
        "boosted_score": 0.036,
    },
]

_MOCK_CONTEXT = {
    "context_text": "OWI is defined under section 346.63...",
    "sources": [{
        "id": "c1",
        "source_file": "data/statues/statue_2.pdf",
        "context_header": "Chapter 346 > § 346.63",
        "statute_numbers": "346.63",
        "source_type": "statute",
        "start_page": 1,
        "title": "statue_2",
    }],
    "cross_refs_followed": [],
    "total_tokens": 50,
}

_MOCK_LLM_RESPONSE = '{"answer_text": "OWI stands for Operating While Intoxicated under Wisconsin Statute 346.63.", "source_list": [{"title": "statue_2", "source_file": "data/statues/statue_2.pdf", "context_header": "Chapter 346 > § 346.63", "relevance": "Defines OWI"}]}'

_MOCK_FORMATTED = {
    "answer": f"OWI stands for Operating While Intoxicated under Wisconsin Statute 346.63.\n\n{DISCLAIMER}",
    "sources": [{"title": "statue_2", "source_file": "data/statues/statue_2.pdf", "context_header": "Chapter 346 > § 346.63", "relevance": "Defines OWI"}],
    "confidence_score": 0.75,
    "flags": {"LOW_CONFIDENCE": False, "OUTDATED_POSSIBLE": False, "JURISDICTION_NOTE": False, "USE_OF_FORCE_CAUTION": False},
    "disclaimer": DISCLAIMER,
}


def _patch_pipeline():
    """Return a stack of patches for the full RAG pipeline."""
    return [
        patch("backend.api.routes.enhance_query", return_value=_MOCK_ENHANCED),
        patch("backend.api.routes.execute_hybrid_search", return_value=_MOCK_SEARCH_RESULTS),
        patch("backend.api.routes.apply_relevance_boost", return_value=_MOCK_SEARCH_RESULTS),
        patch("backend.api.routes.build_context_window", return_value=_MOCK_CONTEXT),
        patch("backend.api.routes.generate_response", return_value=_MOCK_LLM_RESPONSE),
        patch("backend.api.routes.format_response", return_value=_MOCK_FORMATTED),
    ]


class TestHealthEndpoint:
    @patch("backend.api.routes.get_chroma_client")
    @patch("backend.api.routes.get_or_create_collection")
    def test_health_returns_ok(self, mock_collection_fn, mock_client):
        mock_col = MagicMock()
        mock_col.count.return_value = 42
        mock_collection_fn.return_value = mock_col

        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["collection_count"] == 42

    @patch("backend.api.routes.get_chroma_client", side_effect=Exception("db down"))
    def test_health_degraded_on_error(self, mock_client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"


class TestChatEndpoint:
    def test_chat_success(self):
        patches = _patch_pipeline()
        for p in patches:
            p.start()
        try:
            resp = client.post("/api/chat", json={"query": "What is OWI?"})
            assert resp.status_code == 200
            data = resp.json()
            assert "answer" in data
            assert "sources" in data
            assert "confidence_score" in data
            assert "flags" in data
            assert "disclaimer" in data
        finally:
            for p in patches:
                p.stop()

    def test_chat_empty_query_returns_422(self):
        resp = client.post("/api/chat", json={"query": ""})
        assert resp.status_code == 422

    def test_chat_disclaimer_present(self):
        patches = _patch_pipeline()
        for p in patches:
            p.start()
        try:
            resp = client.post("/api/chat", json={"query": "What is OWI?"})
            data = resp.json()
            assert DISCLAIMER in data["disclaimer"]
        finally:
            for p in patches:
                p.stop()

    def test_chat_response_structure(self):
        patches = _patch_pipeline()
        for p in patches:
            p.start()
        try:
            resp = client.post("/api/chat", json={"query": "test query"})
            data = resp.json()
            # Verify flags structure
            flags = data["flags"]
            for key in ["LOW_CONFIDENCE", "OUTDATED_POSSIBLE", "JURISDICTION_NOTE", "USE_OF_FORCE_CAUTION"]:
                assert key in flags
            # Verify confidence score range
            assert 0.0 <= data["confidence_score"] <= 1.0
        finally:
            for p in patches:
                p.stop()


class TestSearchEndpoint:
    @patch("backend.api.routes.enhance_query", return_value=_MOCK_ENHANCED)
    @patch("backend.api.routes.execute_hybrid_search", return_value=_MOCK_SEARCH_RESULTS)
    @patch("backend.api.routes.apply_relevance_boost", return_value=_MOCK_SEARCH_RESULTS)
    def test_search_success(self, mock_boost, mock_search, mock_enhance):
        resp = client.post("/api/search", json={"query": "OWI"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "enhanced_query" in data
        assert len(data["results"]) > 0

    @patch("backend.api.routes.enhance_query", return_value=_MOCK_ENHANCED)
    @patch("backend.api.routes.execute_hybrid_search", return_value=_MOCK_SEARCH_RESULTS)
    @patch("backend.api.routes.apply_relevance_boost", return_value=_MOCK_SEARCH_RESULTS)
    def test_search_result_structure(self, mock_boost, mock_search, mock_enhance):
        resp = client.post("/api/search", json={"query": "OWI"})
        data = resp.json()
        result = data["results"][0]
        assert "id" in result
        assert "document" in result
        assert "metadata" in result
        assert "score" in result

    def test_search_empty_query_returns_422(self):
        resp = client.post("/api/search", json={"query": ""})
        assert resp.status_code == 422
