"""Response formatting, confidence scoring, and final assembly.

Computes a confidence score with boolean flags, applies safety
guardrails, and appends the mandatory disclaimer.
"""

import logging
import statistics
from pathlib import Path

from backend.generation.safety import build_safety_addendum

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "Disclaimer: This system provides legal information, not formal legal "
    "advice. Always verify with current statutes."
)


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def compute_response_metadata(
    search_results: list[dict],
    final_answer: str,
    enhanced_query: dict,
) -> dict:
    """Compute confidence score (0.0-1.0) and boolean flags.

    Confidence components:
        - topic_relevance: query synonyms found in top-3 result text/metadata (+0.25)
        - top_rrf_score: normalized top boosted_score (up to +0.30)
        - score_variance: spread between top-1 and top-5 scores (0.0 to +0.10)
        - distinct_sources: unique source files in top 5 (+0.10 each, cap +0.30)

    Boolean flags:
        - LOW_CONFIDENCE: confidence < 0.6
        - OUTDATED_POSSIBLE: delegated to safety module
        - JURISDICTION_NOTE: delegated to safety module
        - USE_OF_FORCE_CAUTION: delegated to safety module
    """
    if not search_results:
        return {
            "confidence_score": 0.0,
            "LOW_CONFIDENCE": True,
            "OUTDATED_POSSIBLE": False,
            "JURISDICTION_NOTE": False,
            "USE_OF_FORCE_CAUTION": False,
        }

    score = 0.20  # base score

    # 1. Topic relevance — check if query synonyms appear in top-3 results
    synonyms = enhanced_query.get("synonyms", [])
    exact_keywords = set(enhanced_query.get("exact_keywords", []))

    # First try exact statute/citation match (strongest signal)
    if exact_keywords and search_results:
        top_meta = search_results[0].get("metadata", {})
        top_statutes = set(top_meta.get("statute_numbers", "").split(","))
        top_citations = set(top_meta.get("case_citations", "").split(","))
        if exact_keywords & (top_statutes | top_citations):
            score += 0.25
    elif synonyms:
        # Fall back to synonym matching in top-3 result documents/metadata
        top3_text = " ".join(
            (r.get("document", "") + " " +
             r.get("metadata", {}).get("title", "") + " " +
             r.get("metadata", {}).get("context_header", ""))
            for r in search_results[:3]
        ).lower()
        matched = any(syn.lower() in top3_text for syn in synonyms)
        if matched:
            score += 0.25

    # 2. Top RRF/boosted score (normalized)
    top_score = search_results[0].get("boosted_score", search_results[0].get("rrf_score", 0.0))
    # RRF scores with k=60 max around 0.033 (rank 1 in both lists)
    normalized_top = min(top_score / 0.033, 1.0)
    score += 0.30 * normalized_top

    # 3. Score variance between top-1 and top-5 (clamped to non-negative)
    if len(search_results) >= 5:
        top5_scores = [
            r.get("boosted_score", r.get("rrf_score", 0.0))
            for r in search_results[:5]
        ]
        variance = statistics.variance(top5_scores)
        # High variance means top result is clearly dominant (good)
        variance_factor = min(variance / 0.0001, 1.0)
        score += 0.10 * variance_factor  # 0.0 to +0.10 (never subtracts)

    # 4. Distinct source files in top 5
    top5 = search_results[:5]
    distinct_files = len({
        r.get("metadata", {}).get("source_file", f"unknown_{i}")
        for i, r in enumerate(top5)
    })
    score += min(distinct_files * 0.10, 0.30)

    # Clamp to [0.0, 1.0]
    confidence = max(0.0, min(1.0, score))

    return {
        "confidence_score": round(confidence, 3),
        "LOW_CONFIDENCE": confidence < 0.6,
        "OUTDATED_POSSIBLE": False,  # set later by safety module
        "JURISDICTION_NOTE": False,  # set later by safety module
        "USE_OF_FORCE_CAUTION": False,  # set later by safety module
    }


# ---------------------------------------------------------------------------
# Final response assembly
# ---------------------------------------------------------------------------

def format_response(
    raw_llm_response: str,
    search_results: list[dict],
    enhanced_query: dict,
    query: str,
) -> dict:
    """Format the final response with citations, confidence, safety, and disclaimer.

    Steps:
        1. Use LLM plain-text response directly.
        2. Compute confidence metadata.
        3. Run safety checks.
        4. Merge safety flags into metadata.
        5. Append addendum text and disclaimer.

    Returns:
        dict with:
            - answer: str (main text + addenda + disclaimer)
            - sources: list[dict] (top 3 sources)
            - confidence_score: float
            - flags: dict of boolean flags
            - disclaimer: str
    """
    # 1. Use raw LLM text directly (no JSON parsing needed)
    answer_text = raw_llm_response.strip()

    # 2. Confidence
    metadata = compute_response_metadata(search_results, answer_text, enhanced_query)

    # 3. Safety
    safety_sources = [r.get("metadata", {}) for r in search_results[:5]]
    safety = build_safety_addendum(query, answer_text, safety_sources)

    # 4. Merge safety flags
    metadata["OUTDATED_POSSIBLE"] = safety["outdated_possible"]
    metadata["JURISDICTION_NOTE"] = safety["jurisdiction_note"]
    metadata["USE_OF_FORCE_CAUTION"] = safety["use_of_force_caution"]

    # 5. Final answer (notes and disclaimer are returned as separate fields)
    final_answer = answer_text

    # 6. Build sources from actual search result metadata, capped at 3
    formatted_sources = []
    for r in search_results:
        meta = r.get("metadata", {})
        source_file = meta.get("source_file", "")
        title = meta.get("title", "")
        if not title and source_file:
            title = Path(source_file).stem
        formatted_sources.append({
            "title": title or "Unknown",
            "source_file": source_file,
            "context_header": meta.get("context_header", ""),
            "relevance": "",
            "source_type": meta.get("source_type", ""),
            "document": r.get("document", "")[:500],
            "score": r.get("boosted_score", r.get("rrf_score", 0.0)),
            "chunk_id": r.get("id", ""),
            "statute_numbers": meta.get("statute_numbers", ""),
            "case_citations": meta.get("case_citations", ""),
        })
    formatted_sources = formatted_sources[:3]

    return {
        "answer": final_answer,
        "sources": formatted_sources,
        "confidence_score": metadata["confidence_score"],
        "flags": {
            "LOW_CONFIDENCE": metadata["LOW_CONFIDENCE"],
            "OUTDATED_POSSIBLE": metadata["OUTDATED_POSSIBLE"],
            "JURISDICTION_NOTE": metadata["JURISDICTION_NOTE"],
            "USE_OF_FORCE_CAUTION": metadata["USE_OF_FORCE_CAUTION"],
        },
        "disclaimer": DISCLAIMER,
    }
