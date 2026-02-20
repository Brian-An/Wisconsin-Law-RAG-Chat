"""Cross-reference detection and citation chain following.

Detects statute and chapter references in chunk text (e.g. "see also
§ 940.01") and fetches the cited chunks from ChromaDB.
"""

import logging
import re
from typing import Optional

from backend.ingestion.ingest import get_chroma_client, get_or_create_collection

logger = logging.getLogger(__name__)

# Regex patterns for cross-reference language
CROSS_REF_PATTERNS: list[re.Pattern] = [
    # "see also § 940.01", "see section 346.63"
    re.compile(
        r"see\s+(?:also\s+)?(?:\u00a7|section|sec\.)\s*(\d{2,4}\.\d{2,4})",
        re.IGNORECASE,
    ),
    # "under § 940.01", "per section 346.63", "pursuant to § 940.01"
    re.compile(
        r"(?:under|per|pursuant\s+to)\s+(?:\u00a7|section|sec\.)\s*(\d{2,4}\.\d{2,4})",
        re.IGNORECASE,
    ),
    # "§ 940.01 applies", "section 346.63 governs"
    re.compile(
        r"(?:\u00a7|section|sec\.)\s*(\d{2,4}\.\d{2,4})\s+(?:applies|governs|provides|requires|prohibits)",
        re.IGNORECASE,
    ),
    # "Chapter 943"
    re.compile(r"Chapter\s+(\d+[A-Z]?)\b", re.IGNORECASE),
]


def detect_cross_references(text: str) -> list[str]:
    """Extract statute/chapter numbers from cross-reference language in text.

    Returns a deduplicated list of statute numbers (e.g. "940.01") or
    chapter numbers (e.g. "943") found in cross-reference phrases.
    """
    refs: list[str] = []
    for pattern in CROSS_REF_PATTERNS:
        matches = pattern.findall(text)
        refs.extend(matches)
    return list(dict.fromkeys(refs))  # deduplicate, preserve order


def fetch_cross_referenced_chunks(
    references: list[str],
    collection=None,
    max_chunks_per_ref: int = 2,
) -> list[dict]:
    """Look up cross-referenced statutes/chapters in ChromaDB.

    Args:
        references: Statute numbers ("940.01") or chapter numbers ("943").
        collection: ChromaDB collection. If None, uses default.
        max_chunks_per_ref: Maximum chunks to return per reference.

    Returns:
        List of dicts with id, document, metadata.
    """
    if not references:
        return []

    if collection is None:
        client = get_chroma_client()
        collection = get_or_create_collection(client)

    results: list[dict] = []
    seen_ids: set[str] = set()

    for ref in references:
        # Determine if this is a statute number (has ".") or chapter number
        if "." in ref:
            field = "statute_numbers"
        else:
            field = "chapter_numbers"

        try:
            matches = collection.get(
                where={field: {"$contains": ref}},
                include=["documents", "metadatas"],
            )
        except Exception as e:
            logger.warning(f"Failed to fetch cross-ref '{ref}': {e}")
            continue

        if not matches["ids"]:
            continue

        # Take up to max_chunks_per_ref, preferring non-superseded
        added = 0
        for i, doc_id in enumerate(matches["ids"]):
            if doc_id in seen_ids:
                continue
            meta = matches["metadatas"][i]
            if meta.get("superseded") is True:
                continue

            seen_ids.add(doc_id)
            results.append({
                "id": doc_id,
                "document": matches["documents"][i],
                "metadata": meta,
            })
            added += 1
            if added >= max_chunks_per_ref:
                break

    logger.info(
        f"Cross-ref fetch: {len(references)} refs -> {len(results)} chunks"
    )
    return results
