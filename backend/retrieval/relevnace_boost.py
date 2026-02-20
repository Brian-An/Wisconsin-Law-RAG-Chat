"""Domain-specific relevance boosting for search results.

Applies metadata-driven score multipliers after RRF fusion to promote
relevant results and drop superseded documents.
"""

import logging

logger = logging.getLogger(__name__)


def apply_relevance_boost(
    ranked_results: list[dict],
    enhanced_query: dict,
) -> list[dict]:
    """Apply domain-specific relevance multipliers to fused search results.

    Multipliers (applied multiplicatively):
        - superseded == True  -> score * 0.0  (dropped entirely)
        - query contains "policy" AND jurisdiction == "local_department" -> 1.5x
        - jurisdiction == "state" -> 1.2x
        - exact statute number match in exact_keywords -> 1.3x

    Args:
        ranked_results: Output of execute_hybrid_search(), each dict has
            id, document, metadata, rrf_score.
        enhanced_query: Output of enhance_query().

    Returns:
        List re-sorted by boosted_score descending, with superseded
        results removed. Each dict gains a ``boosted_score`` key.
    """
    query_lower = enhanced_query["original"].lower()
    exact_keywords = set(enhanced_query.get("exact_keywords", []))
    chapter_hints = set(enhanced_query.get("chapter_hints", []))
    is_policy_query = "policy" in query_lower

    boosted: list[dict] = []

    for result in ranked_results:
        meta = result.get("metadata", {})
        score = result.get("rrf_score", 0.0)

        # Drop superseded documents
        superseded = meta.get("superseded", False)
        if superseded is True or superseded == "True":
            logger.debug(f"Dropping superseded document: {result['id']}")
            continue

        multiplier = 1.0

        # Policy query + local department source
        if is_policy_query and meta.get("jurisdiction") == "local_department":
            multiplier *= 1.5

        # State jurisdiction boost
        if meta.get("jurisdiction") == "state":
            multiplier *= 1.2

        # Exact statute number match
        statute_numbers = meta.get("statute_numbers", "")
        if statute_numbers and exact_keywords:
            chunk_statutes = set(statute_numbers.split(","))
            if chunk_statutes & exact_keywords:
                multiplier *= 1.3

        # Chapter hint match
        chapter_numbers = meta.get("chapter_numbers", "")
        if chapter_numbers and chapter_hints:
            chunk_chapters = set(chapter_numbers.split(","))
            if chunk_chapters & chapter_hints:
                multiplier *= 1.15

        entry = result.copy()
        entry["boosted_score"] = score * multiplier
        boosted.append(entry)

    # Sort by boosted score descending
    boosted.sort(key=lambda r: r["boosted_score"], reverse=True)

    logger.info(
        f"Relevance boost: {len(ranked_results)} in -> {len(boosted)} out "
        f"(policy_query={is_policy_query})"
    )
    return boosted
