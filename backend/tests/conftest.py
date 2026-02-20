"""Shared pytest fixtures for backend tests."""

from pathlib import Path
import pytest
from dotenv import load_dotenv
from unittest.mock import MagicMock, patch

# Load .env from the repo root so OPENAI_API_KEY is available in all tests
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _make_chunk_metadata(
    doc_id: str = "abc123",
    source_type: str = "statute",
    jurisdiction: str = "state",
    superseded: bool = False,
    title: str = "statute_1",
    source_file: str = "data/statues/statue_1.pdf",
    statute_numbers: str = "940.01",
    case_citations: str = "",
    chapter_numbers: str = "940",
    context_header: str = "Chapter 940 > § 940.01",
    start_page: int = 1,
    **overrides,
) -> dict:
    """Build a sample metadata dict matching ChromaDB schema."""
    meta = {
        "doc_id": doc_id,
        "source_type": source_type,
        "jurisdiction": jurisdiction,
        "superseded": superseded,
        "title": title,
        "source_file": source_file,
        "chunk_index": 0,
        "start_page": start_page,
        "end_page": start_page,
        "context_header": context_header,
        "statute_numbers": statute_numbers,
        "case_citations": case_citations,
        "chapter_numbers": chapter_numbers,
        "token_count": 100,
    }
    meta.update(overrides)
    return meta


@pytest.fixture
def sample_metadata():
    """Return a factory for building sample metadata dicts."""
    return _make_chunk_metadata


@pytest.fixture
def sample_search_results():
    """Return a list of sample search results (as returned by hybrid_search)."""
    return [
        {
            "id": "chunk_1",
            "document": "Under Wisconsin Statute 940.01, first degree intentional homicide is defined as...",
            "metadata": _make_chunk_metadata(
                doc_id="chunk_1", statute_numbers="940.01", chapter_numbers="940",
                title="statute_1", source_file="data/statues/statue_1.pdf",
            ),
            "rrf_score": 0.030,
            "boosted_score": 0.036,
        },
        {
            "id": "chunk_2",
            "document": "Section 346.63 addresses operating while intoxicated on public highways...",
            "metadata": _make_chunk_metadata(
                doc_id="chunk_2", statute_numbers="346.63", chapter_numbers="346",
                title="statute_2", source_file="data/statues/statue_2.pdf",
            ),
            "rrf_score": 0.025,
            "boosted_score": 0.030,
        },
        {
            "id": "chunk_3",
            "document": "The LESB training manual outlines use of force policies for all Wisconsin officers...",
            "metadata": _make_chunk_metadata(
                doc_id="chunk_3", source_type="training",
                statute_numbers="", chapter_numbers="",
                title="LESB", source_file="data/training/LESB.pdf",
            ),
            "rrf_score": 0.020,
            "boosted_score": 0.024,
        },
        {
            "id": "chunk_4",
            "document": "In the case 2023 WI App 45, the court held that...",
            "metadata": _make_chunk_metadata(
                doc_id="chunk_4", source_type="case_law",
                statute_numbers="940.01", case_citations="2023 WI App 45",
                title="2023AP001664", source_file="data/case_law/2023AP001664.pdf",
            ),
            "rrf_score": 0.018,
            "boosted_score": 0.022,
        },
        {
            "id": "chunk_5",
            "document": "Administrative policies for employee conduct require...",
            "metadata": _make_chunk_metadata(
                doc_id="chunk_5", source_type="training",
                jurisdiction="local_department",
                statute_numbers="", chapter_numbers="",
                title="handbook", source_file="data/training/wisconsin_admin_employee_handbook.pdf",
            ),
            "rrf_score": 0.015,
            "boosted_score": 0.018,
        },
    ]


@pytest.fixture
def mock_chroma_collection():
    """Return a MagicMock ChromaDB collection."""
    collection = MagicMock()
    collection.count.return_value = 100
    collection.query.return_value = {
        "ids": [["id1", "id2"]],
        "documents": [["doc text 1", "doc text 2"]],
        "metadatas": [[
            _make_chunk_metadata(doc_id="id1"),
            _make_chunk_metadata(doc_id="id2", statute_numbers="346.63"),
        ]],
        "distances": [[0.1, 0.2]],
    }
    collection.get.return_value = {
        "ids": ["id1", "id2", "id3"],
        "documents": ["doc 1 text", "doc 2 text", "doc 3 text"],
        "metadatas": [
            _make_chunk_metadata(doc_id="id1"),
            _make_chunk_metadata(doc_id="id2"),
            _make_chunk_metadata(doc_id="id3"),
        ],
    }
    return collection
