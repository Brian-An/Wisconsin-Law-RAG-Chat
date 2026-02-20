"""Hybrid search combining semantic (ChromaDB vector) and BM25 keyword search.

Results are merged using Reciprocal Rank Fusion (RRF) with k=60.
"""

import logging
from typing import Optional

from rank_bm25 import BM25Okapi

from backend.config import settings
from backend.ingestion.ingest import (
    get_chroma_client,
    get_or_create_collection,
    generate_embeddings,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# BM25 index cache (built lazily on first query)
# ---------------------------------------------------------------------------

_bm25_index: Optional[BM25Okapi] = None
_bm25_doc_ids: list[str] = []
_bm25_metadatas: list[dict] = []
_bm25_documents: list[str] = []


def _get_bm25_index(collection) -> tuple[Optional[BM25Okapi], list[str], list[str], list[dict]]:
    """Build or return the cached BM25 index from ChromaDB documents."""
    global _bm25_index, _bm25_doc_ids, _bm25_documents, _bm25_metadatas

    if _bm25_index is not None:
        return _bm25_index, _bm25_doc_ids, _bm25_documents, _bm25_metadatas

    logger.info("Building BM25 index from ChromaDB collection...")
    all_data = collection.get(include=["documents", "metadatas"])

    _bm25_doc_ids = all_data["ids"]
    _bm25_documents = all_data["documents"]
    _bm25_metadatas = all_data["metadatas"]

    # Guard: empty collection — BM25Okapi divides by corpus_size internally
    if not _bm25_documents:
        logger.warning("BM25 index: empty corpus, no documents in collection")
        return None, [], [], []

    # Tokenize: lowercase + whitespace split
    corpus = [doc.lower().split() for doc in _bm25_documents]
    _bm25_index = BM25Okapi(corpus)

    logger.info(f"BM25 index built with {len(_bm25_doc_ids)} documents")
    return _bm25_index, _bm25_doc_ids, _bm25_documents, _bm25_metadatas


def invalidate_bm25_cache() -> None:
    """Clear the BM25 cache. Call after re-ingestion."""
    global _bm25_index, _bm25_doc_ids, _bm25_documents, _bm25_metadatas
    _bm25_index = None
    _bm25_doc_ids = []
    _bm25_documents = []
    _bm25_metadatas = []
    logger.info("BM25 cache invalidated")


def _reciprocal_rank_fusion(
    semantic_ranking: list[str],
    bm25_ranking: list[str],
    k: int = 60,
) -> dict[str, float]:
    """Merge two ranked lists using RRF.

    For each document, score = sum of 1/(k + rank) across all lists
    where the document appears. Rank is 1-indexed.
    """
    scores: dict[str, float] = {}

    for rank, doc_id in enumerate(semantic_ranking, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

    for rank, doc_id in enumerate(bm25_ranking, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

    return scores


def execute_hybrid_search(
    enhanced_query: dict,
    n_results: int = 20,
) -> list[dict]:
    """Run semantic + BM25 search and merge with Reciprocal Rank Fusion.

    Args:
        enhanced_query: Output of enhance_query() with keys
            semantic_query, corrected_text, exact_keywords, chapter_hints.
        n_results: Number of results to return.

    Returns:
        List of dicts with keys: id, document, metadata, rrf_score.
        Sorted by rrf_score descending.
    """
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    # --- Semantic search ---
    query_embedding = generate_embeddings([enhanced_query["semantic_query"]])[0]
    semantic_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    semantic_ids = semantic_results["ids"][0]
    semantic_docs = semantic_results["documents"][0]
    semantic_metas = semantic_results["metadatas"][0]

    # Build lookup for document data
    doc_lookup: dict[str, dict] = {}
    for i, doc_id in enumerate(semantic_ids):
        doc_lookup[doc_id] = {
            "id": doc_id,
            "document": semantic_docs[i],
            "metadata": semantic_metas[i],
        }

    # --- BM25 search ---
    bm25_index, bm25_ids, bm25_docs, bm25_metas = _get_bm25_index(collection)

    bm25_ranking_ids: list[str] = []
    if bm25_index is not None:
        tokenized_query = enhanced_query["corrected_text"].lower().split()
        bm25_scores = bm25_index.get_scores(tokenized_query)

        # Get top n_results by BM25 score
        scored_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True,
        )[:n_results]

        for idx in scored_indices:
            if bm25_scores[idx] > 0:
                doc_id = bm25_ids[idx]
                bm25_ranking_ids.append(doc_id)
                if doc_id not in doc_lookup:
                    doc_lookup[doc_id] = {
                        "id": doc_id,
                        "document": bm25_docs[idx],
                        "metadata": bm25_metas[idx],
                    }

    # --- RRF merge ---
    rrf_scores = _reciprocal_rank_fusion(semantic_ids, bm25_ranking_ids, k=60)

    # Build final results sorted by RRF score
    results = []
    for doc_id, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        if doc_id in doc_lookup:
            entry = doc_lookup[doc_id].copy()
            entry["rrf_score"] = score
            results.append(entry)

    results = results[:n_results]

    logger.info(
        f"Hybrid search: {len(semantic_ids)} semantic + "
        f"{len(bm25_ranking_ids)} BM25 -> {len(results)} fused results"
    )
    return results
