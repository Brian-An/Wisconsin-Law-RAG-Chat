"""Query enhancement for the retrieval pipeline.

Takes a raw user query, expands abbreviations, maps colloquialisms to
legal terms, extracts exact-match keywords (statute numbers, case
citations), and builds an expanded semantic query for vector search.
"""

import logging

from backend.ingestion.metadata import STATUTE_NUMBER_PATTERN, CASE_CITATION_PATTERN
from backend.utils.abbreviations import expand_abbreviations
from backend.utils.legal_terms import get_legal_synonyms, get_chapter_hints

logger = logging.getLogger(__name__)


def enhance_query(raw_query: str) -> dict:
    """Enhance a raw user query for hybrid search.

    Returns:
        dict with keys:
            - original: the original query unchanged
            - corrected_text: query with abbreviations expanded inline
            - exact_keywords: statute numbers and case citations extracted
            - semantic_query: expanded string for vector search
            - chapter_hints: relevant statute chapter numbers
    """
    # 1. Expand abbreviations
    corrected = expand_abbreviations(raw_query)

    # 2. Extract exact-match keywords (statute numbers, case citations)
    statute_matches = STATUTE_NUMBER_PATTERN.findall(corrected)
    case_matches = CASE_CITATION_PATTERN.findall(corrected)
    exact_keywords = list(dict.fromkeys(statute_matches + case_matches))

    # 3. Get legal synonyms for colloquialisms
    synonyms = get_legal_synonyms(raw_query)

    # 4. Build expanded semantic query
    parts = [corrected]
    if synonyms:
        parts.append(" ".join(synonyms))
    semantic_query = " ".join(parts)

    # 5. Get chapter hints from topic mapping
    chapter_hints = get_chapter_hints(raw_query)

    result = {
        "original": raw_query,
        "corrected_text": corrected,
        "exact_keywords": exact_keywords,
        "semantic_query": semantic_query,
        "chapter_hints": chapter_hints,
        "synonyms": synonyms,
    }

    logger.info(
        f"Enhanced query: keywords={exact_keywords}, "
        f"synonyms={len(synonyms)}, chapters={chapter_hints}"
    )
    return result
