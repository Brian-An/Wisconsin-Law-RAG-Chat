"""Document-type-aware hierarchical chunking for legal documents.

Supports three document types with tailored hierarchy detection:
  - Statutes:       Chapter > Section (§) > Subsection > Paragraph
  - Case law:       Opinion type > Roman-numeral section > Lettered sub > ¶ paragraph
  - Training/policy: ALL-CAPS header > Section/decimal subsection > numbered/lettered items

Splits text into ~1000-token chunks respecting structural boundaries and prepends
hierarchical context breadcrumbs to each chunk.
"""

import bisect
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from backend.config import settings
from backend.ingestion.parser import ParsedDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-loaded tiktoken encoder (cl100k_base matches text-embedding-3-small)
# ---------------------------------------------------------------------------

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        import tiktoken
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def count_tokens(text: str) -> int:
    """Return the token count using the cl100k_base encoding."""
    return len(_get_encoder().encode(text))


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class HierarchyNode:
    """A detected structural element in a legal document."""
    level: int          # 0=chapter, 1=section, 2=subsection, 3=paragraph
    title: str          # e.g., "Chapter 943", "§ 940.01"
    start_pos: int      # character offset in full text (inclusive)
    end_pos: int = -1   # character offset (exclusive), set after detection


@dataclass
class Chunk:
    """A single chunk of text ready for embedding."""
    text: str
    context_header: str       # breadcrumb, e.g., "Chapter 943 > § 940.01"
    chunk_index: int          # sequential index within the document
    start_page: int = 1
    end_page: int = 1
    token_count: int = 0
    source_file: str = ""
    overlap_with_previous: bool = False


@dataclass
class DocTypeConfig:
    """Per-document-type configuration for hierarchy detection and chunking."""
    name: str
    hierarchy_patterns: list[tuple[int, re.Pattern]]
    primary_section_levels: set[int]
    split_boundary: re.Pattern


# ---------------------------------------------------------------------------
# Document-type hierarchy patterns
# ---------------------------------------------------------------------------

# --- Statute patterns (Wisconsin statutes) ---
_STATUTE_PATTERNS: list[tuple[int, re.Pattern]] = [
    # Level 0 — Chapter: "Chapter 943", "CHAPTER 346"
    (0, re.compile(r"^(Chapter\s+\d+[A-Z]?)\b", re.MULTILINE)),
    # Level 0 — Subchapter: "SUBCHAPTER I", "SUBCHAPTER IV"
    (0, re.compile(r"^(SUBCHAPTER\s+[IVXLC]+)\b", re.MULTILINE)),
    # Level 1 — Section symbol: "§ 940.01"
    (1, re.compile(r"^(\u00a7\s*\d+\.\d+(?:\(\d+\))?)\b", re.MULTILINE)),
    # Level 1 — Bare section number with title: "346.01 Words and phrases"
    (1, re.compile(r"^(\d{2,4}\.\d{2,4})\s+[A-Z]", re.MULTILINE)),
    # Level 1 — "Section X." or "SECTION X."
    (1, re.compile(r"^(Section\s+\d+[A-Za-z]?\.?)\s", re.MULTILINE | re.IGNORECASE)),
    # Level 2 — Numbered subsections: "(1)", "(2)"
    (2, re.compile(r"^\((\d+)\)\s", re.MULTILINE)),
    # Level 2 — "Sub. (1)"
    (2, re.compile(r"^(Sub\.\s*\(\d+\))\s", re.MULTILINE)),
    # Level 3 — Letter paragraphs: "(a)", "(b)"
    (3, re.compile(r"^\(([a-z])\)\s", re.MULTILINE)),
]
_STATUTE_PRIMARY_LEVELS = {0, 1}
_STATUTE_SPLIT_BOUNDARY = re.compile(
    r"\n(?=Chapter\s+\d|\u00a7\s*\d|\d{2,4}\.\d{2,4}\s)"
)

# --- Case law patterns (court opinions) ---
_CASE_LAW_PATTERNS: list[tuple[int, re.Pattern]] = [
    # Level 0 — Opinion type header (appears on every page of each opinion)
    (0, re.compile(
        r"^((?:Opinion of the Court"
        r"|(?:JUSTICE|Justice|CHIEF JUSTICE)\s+[A-Z][A-Za-z]+(?:,?\s+"
        r"(?:concurring|dissenting|concurring in part and dissenting in part))"
        r"[^.\n]*))",
        re.MULTILINE,
    )),
    # Level 1 — Roman numeral sections: "I. FACTUAL AND PROCEDURAL BACKGROUND"
    (1, re.compile(r"^([IVXLC]+\.\s+[A-Z][A-Z\s:]+)", re.MULTILINE)),
    # Level 2 — Lettered subsections: "A. PRIVATE PARTY SEARCH"
    (2, re.compile(r"^([A-Z]\.\s+[A-Z][A-Z\s:]+)", re.MULTILINE)),
    # Level 3 — Pilcrow paragraph markers: "¶1", "¶133"
    (3, re.compile(r"^(\u00b6\s*\d+)\b", re.MULTILINE)),
]
_CASE_LAW_PRIMARY_LEVELS = {0, 1}
_CASE_LAW_SPLIT_BOUNDARY = re.compile(r"\n(?=\u00b6\s*\d+)")

# --- Training / policy patterns (LESB manual, employee handbook) ---
_TRAINING_PATTERNS: list[tuple[int, re.Pattern]] = [
    # Level 0 — ALL-CAPS major section headers (LESB style, 9+ chars)
    (0, re.compile(r"^([A-Z][A-Z\s&/\-]{8,})\s*$", re.MULTILINE)),
    # Level 0 — "POLICY & PROCEDURE" marker
    (0, re.compile(r"^(POLICY\s*&\s*PROCEDURE)\s*$", re.MULTILINE | re.IGNORECASE)),
    # Level 1 — "Section X:" numbered sections (handbook style)
    (1, re.compile(r"^(Section\s+\d+[A-Za-z]?[:.])(?:\s|$)", re.MULTILINE | re.IGNORECASE)),
    # Level 1 — Decimal subsection headers: "1.1 Welcome" at line start
    (1, re.compile(r"^(\d+\.\d+)\s+[A-Z]", re.MULTILINE)),
    # Level 2 — Numbered items: "1." at line start (but not decimal like "1.1")
    (2, re.compile(r"^(\d+)\.\s+(?!\d)", re.MULTILINE)),
    # Level 2 — Lettered items: "a.", "b." at line start
    (2, re.compile(r"^([a-z])\.\s", re.MULTILINE)),
]
_TRAINING_PRIMARY_LEVELS = {0, 1}
_TRAINING_SPLIT_BOUNDARY = re.compile(
    r"\n(?=Section\s+\d|[A-Z][A-Z\s]{8,}$|\d+\.\d+\s)"
)

# --- Backward-compatible aliases (used by tests and external code) ---
HIERARCHY_PATTERNS = _STATUTE_PATTERNS
PRIMARY_SECTION_LEVELS = _STATUTE_PRIMARY_LEVELS

# --- Config instances ---
STATUTE_CONFIG = DocTypeConfig(
    name="statute",
    hierarchy_patterns=_STATUTE_PATTERNS,
    primary_section_levels=_STATUTE_PRIMARY_LEVELS,
    split_boundary=_STATUTE_SPLIT_BOUNDARY,
)
CASE_LAW_CONFIG = DocTypeConfig(
    name="case_law",
    hierarchy_patterns=_CASE_LAW_PATTERNS,
    primary_section_levels=_CASE_LAW_PRIMARY_LEVELS,
    split_boundary=_CASE_LAW_SPLIT_BOUNDARY,
)
TRAINING_CONFIG = DocTypeConfig(
    name="training",
    hierarchy_patterns=_TRAINING_PATTERNS,
    primary_section_levels=_TRAINING_PRIMARY_LEVELS,
    split_boundary=_TRAINING_SPLIT_BOUNDARY,
)

# Subfolder -> config mapping (handles naming variants)
_SUBFOLDER_TO_CONFIG: dict[str, DocTypeConfig] = {
    "statute": STATUTE_CONFIG,
    "statutes": STATUTE_CONFIG,
    "case_law": CASE_LAW_CONFIG,
    "training": TRAINING_CONFIG,
    "policy": TRAINING_CONFIG,
}


def _detect_doc_type_from_content(text: str) -> DocTypeConfig:
    """Heuristic fallback: detect document type from content when subfolder is unknown."""
    sample = text[:3000]

    # Case law signals
    if (
        sample.count("\u00b6") >= 3
        or bool(re.search(r"No\.\s*\d{4}AP\d+", sample))
        or "Opinion of the Court" in sample
        or bool(re.search(r"Plaintiff|Defendant|Appellant|Respondent", sample, re.IGNORECASE))
    ):
        return CASE_LAW_CONFIG

    # Training/policy signals
    if (
        bool(re.search(r"^[A-Z][A-Z\s&/\-]{10,}$", sample, re.MULTILINE))
        or bool(re.search(r"Section\s+\d+:", sample))
        or "POLICY & PROCEDURE" in sample.upper()
        or "handbook" in sample.lower()
    ):
        return TRAINING_CONFIG

    return STATUTE_CONFIG


def _get_doc_type_config(subfolder: str, text: str) -> DocTypeConfig:
    """Resolve document type config from subfolder, with content-based fallback."""
    config = _SUBFOLDER_TO_CONFIG.get(subfolder.lower())
    if config is not None:
        return config
    logger.info(f"Unknown subfolder '{subfolder}'; detecting doc type from content")
    return _detect_doc_type_from_content(text)


def detect_hierarchy(
    text: str,
    config: Optional[DocTypeConfig] = None,
) -> list[HierarchyNode]:
    """Scan text for legal hierarchy markers and return a sorted list of nodes.

    Args:
        text: The document text to scan.
        config: Optional DocTypeConfig. If None, uses the default statute
                patterns for backward compatibility.

    Returns nodes sorted by position with ``end_pos`` set to the start of
    the next same-or-higher-level node (or end of text for the last node).
    """
    patterns = config.hierarchy_patterns if config else HIERARCHY_PATTERNS
    raw_matches: list[HierarchyNode] = []

    for level, pattern in patterns:
        for match in pattern.finditer(text):
            title = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)

            # For bare digit/letter captures, wrap in parens for readability
            if level == 2 and title.isdigit():
                title = f"({title})"
            elif level == 3 and len(title) == 1 and title.isalpha():
                title = f"({title})"

            raw_matches.append(HierarchyNode(
                level=level,
                title=title.strip(),
                start_pos=match.start(),
            ))

    raw_matches.sort(key=lambda n: n.start_pos)

    # Deduplicate overlapping matches at the same position
    deduped: list[HierarchyNode] = []
    for node in raw_matches:
        if deduped and abs(node.start_pos - deduped[-1].start_pos) < 3:
            if node.level < deduped[-1].level:
                deduped[-1] = node
            continue
        deduped.append(node)

    # Set end_pos: each node ends where the next same-or-higher-level node begins
    for i, node in enumerate(deduped):
        node.end_pos = len(text)
        for j in range(i + 1, len(deduped)):
            if deduped[j].level <= node.level:
                node.end_pos = deduped[j].start_pos
                break

    return deduped


def _build_context_path(all_nodes: list[HierarchyNode], target_pos: int) -> list[HierarchyNode]:
    """Find the hierarchy path (root -> leaf) enclosing a given text position."""
    path: list[HierarchyNode] = []
    for node in all_nodes:
        if node.start_pos <= target_pos < node.end_pos:
            if not path or node.level > path[-1].level:
                path.append(node)
    return path


def build_context_header(node_path: list[HierarchyNode]) -> str:
    """Build a breadcrumb string from a hierarchy path.

    Example: "Chapter 943 > § 940.01 > (2) > (a)"
    """
    if not node_path:
        return ""
    return " > ".join(n.title for n in node_path)


# ---------------------------------------------------------------------------
# Text splitting helpers
# ---------------------------------------------------------------------------

_LEGAL_BOUNDARY = re.compile(r"\n(?=Chapter\s+\d|§\s*\d)")
_PARAGRAPH_BOUNDARY = re.compile(r"\n\n+")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z\(\u00a7])")


def _find_split_point(
    text: str,
    max_chars: int,
    legal_boundary: Optional[re.Pattern] = None,
) -> int:
    """Find the best split point at or before *max_chars*.

    Priority: legal boundary > paragraph break > sentence end > last space.

    Args:
        text: Text to search for a split point.
        max_chars: Maximum character position for the split.
        legal_boundary: Override for the structural boundary pattern.
                        Defaults to the statute-focused ``_LEGAL_BOUNDARY``.
    """
    if len(text) <= max_chars:
        return len(text)

    search_region = text[:max_chars]
    min_pos = int(max_chars * 0.3)
    boundary = legal_boundary or _LEGAL_BOUNDARY

    # 1. Legal / structural boundary
    best = -1
    for m in boundary.finditer(search_region):
        best = m.start()
    if best > min_pos:
        return best

    # 2. Paragraph boundary
    best = -1
    for m in _PARAGRAPH_BOUNDARY.finditer(search_region):
        best = m.start()
    if best > min_pos:
        return best

    # 3. Sentence boundary
    best = -1
    for m in _SENTENCE_BOUNDARY.finditer(search_region):
        best = m.end()
    if best > min_pos:
        return best

    # 4. Last space
    last_space = search_region.rfind(" ")
    if last_space > 0:
        return last_space

    return max_chars


def _estimate_chars_per_token(text: str, sample_size: int = 500) -> float:
    """Estimate average characters per token for the given text."""
    sample = text[:sample_size] if len(text) > sample_size else text
    tokens = count_tokens(sample)
    if tokens == 0:
        return 4.0
    return len(sample) / tokens


# ---------------------------------------------------------------------------
# Page estimation
# ---------------------------------------------------------------------------

def _build_page_offsets(pages) -> list[int]:
    """Build cumulative character offsets matching the parser's \\n\\n join."""
    offsets: list[int] = []
    cumulative = 0
    for page in pages:
        cumulative += len(page.text)
        offsets.append(cumulative)
        cumulative += 2  # "\n\n" separator
    return offsets


def _estimate_page(char_offset: int, page_offsets: list[int]) -> int:
    """Map a character offset to a 1-indexed page number."""
    if not page_offsets:
        return 1
    idx = bisect.bisect_right(page_offsets, char_offset)
    return min(idx + 1, len(page_offsets))


# ---------------------------------------------------------------------------
# Core splitting
# ---------------------------------------------------------------------------

def _split_text_into_chunks(
    text: str,
    context_header: str,
    target_tokens: int,
    overlap_fraction: float,
    source_file: str,
    start_chunk_index: int,
    page_offsets: list[int],
    text_start_offset: int,
    legal_boundary: Optional[re.Pattern] = None,
) -> list[Chunk]:
    """Split a section of text into token-bounded chunks with overlap."""
    if not text.strip():
        return []

    chars_per_token = _estimate_chars_per_token(text)
    target_chars = int(target_tokens * chars_per_token)
    overlap_chars = int(target_chars * overlap_fraction)
    # Minimum advance must be at least half the target to prevent micro-chunks
    min_advance = max(target_chars // 2, 100)

    chunks: list[Chunk] = []
    chunk_idx = start_chunk_index
    remaining = text
    offset_in_section = 0
    is_first = True

    while remaining.strip():
        split_at = _find_split_point(remaining, target_chars, legal_boundary)
        chunk_text = remaining[:split_at].strip()

        if not chunk_text:
            break

        token_count = count_tokens(chunk_text)
        abs_start = text_start_offset + offset_in_section
        abs_end = abs_start + split_at

        chunks.append(Chunk(
            text=chunk_text,
            context_header=context_header,
            chunk_index=chunk_idx,
            start_page=_estimate_page(abs_start, page_offsets),
            end_page=_estimate_page(abs_end, page_offsets),
            token_count=token_count,
            source_file=source_file,
            overlap_with_previous=not is_first,
        ))

        chunk_idx += 1
        is_first = False

        # Advance: split_at minus overlap, but never less than min_advance
        advance = max(split_at - overlap_chars, min_advance)
        # Don't advance past what we actually have
        advance = min(advance, len(remaining))
        offset_in_section += advance
        remaining = remaining[advance:]

    return chunks


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def chunk_document(
    parsed_doc: ParsedDocument,
    normalized_text: str,
    target_tokens: Optional[int] = None,
    overlap_fraction: Optional[float] = None,
) -> list[Chunk]:
    """Chunk a normalized document into embedding-ready pieces.

    Automatically selects document-type-specific hierarchy patterns based on
    the document's subfolder (statute, case_law, training), with a content-based
    fallback for unknown subfolders.

    Args:
        parsed_doc: The original parsed document (for page info).
        normalized_text: The cleaned text to chunk.
        target_tokens: Target tokens per chunk (default from settings).
        overlap_fraction: Fraction of overlap between chunks (default from settings).

    Returns:
        List of Chunk objects ready for metadata extraction and embedding.
    """
    target_tokens = target_tokens or settings.CHUNK_TARGET_TOKENS
    if overlap_fraction is None:
        overlap_fraction = settings.CHUNK_OVERLAP_FRACTION

    # Resolve document-type config for hierarchy patterns and split boundaries
    config = _get_doc_type_config(parsed_doc.subfolder, normalized_text)
    logger.debug(f"Using doc type config '{config.name}' for {parsed_doc.file_name}")

    page_offsets = _build_page_offsets(parsed_doc.pages)
    all_nodes = detect_hierarchy(normalized_text, config=config)

    # Filter to primary section nodes for section splitting
    primary_nodes = [n for n in all_nodes if n.level in config.primary_section_levels]

    doc_title = parsed_doc.file_name.rsplit(".", 1)[0]

    if not primary_nodes:
        # No structural markers found — chunk as flat text.
        chunks = _split_text_into_chunks(
            text=normalized_text,
            context_header=doc_title,
            target_tokens=target_tokens,
            overlap_fraction=overlap_fraction,
            source_file=parsed_doc.file_path,
            start_chunk_index=0,
            page_offsets=page_offsets,
            text_start_offset=0,
            legal_boundary=config.split_boundary,
        )
        logger.info(
            f"  {parsed_doc.file_name}: {len(chunks)} chunks "
            f"(flat/{config.name}, no primary hierarchy)"
        )
        return chunks

    # Build section ranges from primary nodes.
    # Each section runs from one primary node's start to the next primary node's start.
    sections: list[tuple[int, int]] = []  # (start_pos, end_pos)

    # Text before first primary node
    if primary_nodes[0].start_pos > 0:
        sections.append((0, primary_nodes[0].start_pos))

    for i, node in enumerate(primary_nodes):
        end = primary_nodes[i + 1].start_pos if i + 1 < len(primary_nodes) else len(normalized_text)
        sections.append((node.start_pos, end))

    all_chunks: list[Chunk] = []
    chunk_idx = 0

    for start_pos, end_pos in sections:
        section_text = normalized_text[start_pos:end_pos]
        if not section_text.strip():
            continue

        # Build context header from all hierarchy levels at this position
        path = _build_context_path(all_nodes, start_pos)
        header = build_context_header(path) or doc_title

        chunks = _split_text_into_chunks(
            text=section_text,
            context_header=header,
            target_tokens=target_tokens,
            overlap_fraction=overlap_fraction,
            source_file=parsed_doc.file_path,
            start_chunk_index=chunk_idx,
            page_offsets=page_offsets,
            text_start_offset=start_pos,
            legal_boundary=config.split_boundary,
        )

        # For chunks beyond the first in a section, update their context header
        # to reflect the sub-hierarchy at their actual position
        for chunk in chunks:
            mid_pos = start_pos + (chunk.chunk_index - chunk_idx) * (
                (end_pos - start_pos) // max(len(chunks), 1)
            )
            mid_pos = min(mid_pos, end_pos - 1)
            sub_path = _build_context_path(all_nodes, mid_pos)
            if sub_path:
                chunk.context_header = build_context_header(sub_path)

        all_chunks.extend(chunks)
        chunk_idx += len(chunks)

    logger.info(
        f"  {parsed_doc.file_name}: {len(all_chunks)} chunks "
        f"({len(primary_nodes)} primary sections, {len(all_nodes)} total nodes, "
        f"type={config.name})"
    )

    return all_chunks
