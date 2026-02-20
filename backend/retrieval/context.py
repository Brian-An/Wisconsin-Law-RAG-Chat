"""Context window assembly for the generation pipeline.

Builds a token-budgeted context string from ranked chunks, following
cross-references to pull in cited statutes when space allows.
"""

import logging

from backend.ingestion.chunking import count_tokens
from backend.retrieval.cross_ref import detect_cross_references, fetch_cross_referenced_chunks

logger = logging.getLogger(__name__)


def build_context_window(
    ranked_chunks: list[dict],
    token_limit: int = 4000,
) -> dict:
    """Assemble a context string from ranked chunks, following cross-references.

    For each chunk (in rank order):
      1. If adding it would exceed token_limit, stop.
      2. Append the chunk text to the context.
      3. Detect cross-references in the text.
      4. For each unseen cross-reference, fetch the cited chunk and append
         if still under the token limit.

    Args:
        ranked_chunks: Output of apply_relevance_boost(), sorted by
            boosted_score descending.
        token_limit: Maximum tokens in the assembled context.

    Returns:
        dict with keys:
            - context_text: the assembled context string
            - sources: metadata for each chunk included
            - cross_refs_followed: statute/chapter numbers looked up
            - total_tokens: final token count
    """
    context_parts: list[str] = []
    sources: list[dict] = []
    seen_ids: set[str] = set()
    cross_refs_followed: list[str] = []
    total_tokens = 0

    for chunk in ranked_chunks:
        doc_id = chunk["id"]
        if doc_id in seen_ids:
            continue

        text = chunk["document"]
        chunk_tokens = count_tokens(text)

        if total_tokens + chunk_tokens > token_limit:
            break

        # Add chunk to context
        context_parts.append(text)
        total_tokens += chunk_tokens
        seen_ids.add(doc_id)

        meta = chunk.get("metadata", {})
        sources.append({
            "id": doc_id,
            "source_file": meta.get("source_file", ""),
            "context_header": meta.get("context_header", ""),
            "statute_numbers": meta.get("statute_numbers", ""),
            "source_type": meta.get("source_type", ""),
            "start_page": meta.get("start_page", 0),
            "title": meta.get("title", ""),
        })

        # Detect and follow cross-references
        refs = detect_cross_references(text)
        new_refs = [r for r in refs if r not in cross_refs_followed]

        if new_refs:
            cross_ref_chunks = fetch_cross_referenced_chunks(new_refs)
            cross_refs_followed.extend(new_refs)

            for xref_chunk in cross_ref_chunks:
                xref_id = xref_chunk["id"]
                if xref_id in seen_ids:
                    continue

                xref_text = xref_chunk["document"]
                xref_tokens = count_tokens(xref_text)

                if total_tokens + xref_tokens > token_limit:
                    continue  # skip this cross-ref but try others

                context_parts.append(xref_text)
                total_tokens += xref_tokens
                seen_ids.add(xref_id)

                xref_meta = xref_chunk.get("metadata", {})
                sources.append({
                    "id": xref_id,
                    "source_file": xref_meta.get("source_file", ""),
                    "context_header": xref_meta.get("context_header", ""),
                    "statute_numbers": xref_meta.get("statute_numbers", ""),
                    "source_type": xref_meta.get("source_type", ""),
                    "start_page": xref_meta.get("start_page", 0),
                    "title": xref_meta.get("title", ""),
                })

    context_text = "\n\n---\n\n".join(context_parts)

    logger.info(
        f"Context window: {len(sources)} chunks, {total_tokens} tokens, "
        f"{len(cross_refs_followed)} cross-refs followed"
    )

    return {
        "context_text": context_text,
        "sources": sources,
        "cross_refs_followed": cross_refs_followed,
        "total_tokens": total_tokens,
    }
