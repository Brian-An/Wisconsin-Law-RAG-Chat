"""Metadata extraction for legal document chunks.

Builds a unified metadata dictionary per chunk using file path info,
folder structure, and regex-based extraction of statute numbers,
case citations, and chapter references.
"""

import hashlib
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.ingestion.chunking import Chunk
    from backend.ingestion.parser import ParsedDocument

# ---------------------------------------------------------------------------
# Source type mapping (subfolder name → canonical type)
# ---------------------------------------------------------------------------


SUBFOLDER_TO_SOURCE_TYPE: dict[str, str] = {
    "statute": "statute",
    "statutes": "statute",
    "case_law": "case_law",
    "training": "training",
    "policy": "policy",
}

# ---------------------------------------------------------------------------
# Jurisdiction keywords
# ---------------------------------------------------------------------------

LOCAL_JURISDICTION_KEYWORDS: list[str] = [
    "madison",
    "milwaukee",
    "dane county",
    "milwaukee county",
    "city of madison",
    "city of milwaukee",
]

# ---------------------------------------------------------------------------
# Regex patterns for optional metadata fields
# ---------------------------------------------------------------------------

# Matches: § 940.01, 346.63(1)(a), § 940.01(2)
STATUTE_NUMBER_PATTERN = re.compile(
    r"(?:\u00a7\s*)?(\d{2,4}\.\d{2,4}(?:\(\d+\)(?:\([a-z]\))?)?)"
)

# Matches: 2023 WI App 45, 2023 WI 12, 2023AP001234
CASE_CITATION_PATTERN = re.compile(
    r"(\d{4}\s*(?:WI\s*(?:App\s*)?\d+|AP\s*\d+))"
)

# Matches: Chapter 943, Chapter 346A
CHAPTER_PATTERN = re.compile(r"Chapter\s+(\d+[A-Z]?)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def generate_doc_id(chunk_text: str, source_file: str, chunk_index: int) -> str:
    """Generate a deterministic unique ID for a chunk.

    Uses SHA-256 of (source_file + chunk_index + first 200 chars of text).
    Deterministic so re-running ingestion with the same parameters produces
    the same IDs, making ChromaDB upserts idempotent.
    """
    content = f"{source_file}::{chunk_index}::{chunk_text[:200]}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


def infer_source_type(subfolder: str) -> str:
    """Map a subfolder name to a canonical source type."""
    return SUBFOLDER_TO_SOURCE_TYPE.get(subfolder.lower(), "unknown")


def infer_jurisdiction(text: str, file_name: str) -> str:
    """Determine jurisdiction based on text content and filename.

    Returns "local_department" if Madison/Milwaukee keywords are found,
    otherwise "state".
    """
    search_text = f"{file_name} {text[:2000]}".lower()
    for keyword in LOCAL_JURISDICTION_KEYWORDS:
        if keyword in search_text:
            return "local_department"
    return "state"


def extract_statute_numbers(text: str) -> list[str]:
    """Extract all statute number references from text."""
    matches = STATUTE_NUMBER_PATTERN.findall(text)
    return list(dict.fromkeys(matches))  # deduplicate, preserve order


def extract_case_citations(text: str) -> list[str]:
    """Extract all case citation references from text."""
    matches = CASE_CITATION_PATTERN.findall(text)
    return list(dict.fromkeys(matches))


def extract_chapter_numbers(text: str) -> list[str]:
    """Extract all chapter number references from text."""
    matches = CHAPTER_PATTERN.findall(text)
    return list(dict.fromkeys(matches))


def extract_metadata(chunk: "Chunk", parsed_doc: "ParsedDocument") -> dict:
    """Build the complete metadata dictionary for a chunk.

    All values are str, int, float, or bool to satisfy ChromaDB constraints.
    Lists are stored as comma-separated strings.

    Returns:
        dict with keys: doc_id, source_type, jurisdiction, superseded,
        title, source_file, chunk_index, start_page, end_page,
        context_header, statute_numbers, case_citations, chapter_numbers,
        token_count.
    """
    combined_text = f"{chunk.context_header}\n{chunk.text}"
    title = Path(parsed_doc.file_name).stem

    statute_nums = extract_statute_numbers(combined_text)
    case_cites = extract_case_citations(combined_text)
    chapter_nums = extract_chapter_numbers(combined_text)

    return {
        "doc_id": generate_doc_id(chunk.text, parsed_doc.file_path, chunk.chunk_index),
        "source_type": infer_source_type(parsed_doc.subfolder),
        "jurisdiction": infer_jurisdiction(chunk.text, parsed_doc.file_name),
        "superseded": False,
        "title": title,
        "source_file": parsed_doc.file_path,
        "chunk_index": chunk.chunk_index,
        "start_page": chunk.start_page,
        "end_page": chunk.end_page,
        "context_header": chunk.context_header,
        "statute_numbers": ",".join(statute_nums),
        "case_citations": ",".join(case_cites),
        "chapter_numbers": ",".join(chapter_nums),
        "token_count": chunk.token_count,
    }
