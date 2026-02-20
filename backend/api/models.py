"""Pydantic request/response models for the API layer."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""

    query: str = Field(..., min_length=1, max_length=2000, description="The user's question")
    session_id: Optional[str] = Field(None, description="Optional session identifier")


class SourceInfo(BaseModel):
    """A single source citation."""

    title: str
    source_file: str
    context_header: str = ""
    relevance: str = ""
    source_type: str = ""
    document: str = ""
    score: float = 0.0
    chunk_id: str = ""
    statute_numbers: str = ""
    case_citations: str = ""

    @field_validator(
        "context_header", "relevance", "source_file", "source_type",
        "document", "chunk_id", "statute_numbers", "case_citations",
        mode="before",
    )
    @classmethod
    def coerce_none_to_empty(cls, v: object) -> str:
        """Accept None gracefully and convert to empty string."""
        return v if v is not None else ""


class ResponseFlags(BaseModel):
    """Boolean flags about response quality and safety."""

    LOW_CONFIDENCE: bool = False
    OUTDATED_POSSIBLE: bool = False
    JURISDICTION_NOTE: bool = False
    USE_OF_FORCE_CAUTION: bool = False


class ChatResponse(BaseModel):
    """Response body for the /chat endpoint."""

    answer: str
    sources: list[SourceInfo] = []
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    flags: ResponseFlags = ResponseFlags()
    disclaimer: str


class SearchRequest(BaseModel):
    """Request body for the /search endpoint (retrieval only, no LLM)."""

    query: str = Field(..., min_length=1, max_length=2000)
    n_results: int = Field(10, ge=1, le=50)


class SearchResult(BaseModel):
    """A single search result."""

    id: str
    document: str
    metadata: dict
    score: float


class SearchResponse(BaseModel):
    """Response body for the /search endpoint."""

    results: list[SearchResult]
    enhanced_query: dict


class HealthResponse(BaseModel):
    """Response body for the /health endpoint."""

    status: str = "ok"
    collection_count: int = 0
