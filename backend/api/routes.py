"""Chat and search API endpoints.

The /chat route orchestrates the full RAG pipeline:
  enhance_query -> hybrid_search -> relevance_boost -> build_context
  -> build_prompt -> generate_response -> format_response
"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from backend.api.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ResponseFlags,
    SearchRequest,
    SearchResponse,
    SourceInfo,
)
from backend.config import settings
from backend.generation.formatter import format_response
from backend.generation.llm import generate_response
from backend.generation.prompt import build_prompt, get_system_prompt
from backend.ingestion.ingest import get_chroma_client, get_or_create_collection
from backend.retrieval.context import build_context_window
from backend.retrieval.hybrid_search import execute_hybrid_search
from backend.retrieval.query_expand import enhance_query
from backend.retrieval.relevnace_boost import apply_relevance_boost

router = APIRouter()
logger = logging.getLogger(__name__)


async def _run_sync(func, *args):
    """Run a synchronous function in the default thread-pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a user query through the full RAG pipeline."""
    try:
        # 1. Query enhancement
        enhanced = await _run_sync(enhance_query, request.query)

        # 2. Hybrid search (semantic + BM25)
        search_results = await _run_sync(execute_hybrid_search, enhanced)

        # 3. Relevance boosting
        boosted_results = await _run_sync(apply_relevance_boost, search_results, enhanced)

        if not boosted_results:
            from backend.generation.formatter import DISCLAIMER

            return ChatResponse(
                answer="I could not find relevant information in the available legal documents "
                       "to answer your question. Please try rephrasing or ask about a specific "
                       f"Wisconsin statute or policy.\n\n{DISCLAIMER}",
                sources=[],
                confidence_score=0.0,
                flags=ResponseFlags(LOW_CONFIDENCE=True),
                disclaimer=DISCLAIMER,
            )

        # 4. Build context window with cross-reference following
        context = await _run_sync(build_context_window, boosted_results)

        # 5. Build prompt
        prompt = build_prompt(request.query, context["context_text"], context["sources"])
        system_prompt = get_system_prompt()

        # 6. Generate LLM response
        raw_response = await _run_sync(
            generate_response,
            prompt,
            system_prompt,
            settings.LLM_MODEL,
            settings.LLM_TEMPERATURE,
        )

        # 7. Format response (parse JSON, score confidence, apply safety, add disclaimer)
        formatted = format_response(raw_response, boosted_results, enhanced, request.query)

        return ChatResponse(
            answer=formatted["answer"],
            sources=[SourceInfo(**s) for s in formatted["sources"]],
            confidence_score=formatted["confidence_score"],
            flags=ResponseFlags(**formatted["flags"]),
            disclaimer=formatted["disclaimer"],
        )

    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Run retrieval only (no LLM generation). Useful for debugging."""
    try:
        enhanced = await _run_sync(enhance_query, request.query)
        results = await _run_sync(execute_hybrid_search, enhanced, request.n_results)
        boosted = await _run_sync(apply_relevance_boost, results, enhanced)

        return SearchResponse(
            results=[
                {
                    "id": r["id"],
                    "document": r["document"][:500],
                    "metadata": r["metadata"],
                    "score": r.get("boosted_score", r.get("rrf_score", 0.0)),
                }
                for r in boosted
            ],
            enhanced_query=enhanced,
        )
    except Exception as e:
        logger.error(f"Error processing search request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    try:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        return HealthResponse(status="ok", collection_count=collection.count())
    except Exception:
        return HealthResponse(status="degraded", collection_count=0)
