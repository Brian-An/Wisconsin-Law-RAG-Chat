"""Text normalization for legal documents.

Strips headers/footers and normalizes whitespace while preserving
all legal section markers (Chapter, Section, §, subsection references).
"""

import re

# ---------------------------------------------------------------------------
# Header / footer patterns — compiled once at module level.
# Each pattern matches an entire line that should be removed.
# Designed to NEVER match legal markers (Chapter X, § X.X, etc.).
# ---------------------------------------------------------------------------

HEADER_FOOTER_PATTERNS: list[re.Pattern] = [
    # "Page 1 of 5", "page 12 of 100"
    re.compile(r"^\s*Page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE | re.MULTILINE),
    # "Page 1" on its own line (but not "Page" as part of longer text)
    re.compile(r"^\s*Page\s+\d+\s*$", re.IGNORECASE | re.MULTILINE),
    # "Wisconsin Statutes 2023" header
    re.compile(r"^\s*Wisconsin\s+Statut(?:e|es)\s+\d{4}\s*$", re.IGNORECASE | re.MULTILINE),
    # "Updated 2023-01-15" or "Updated 2023/01/15" footer
    re.compile(r"^\s*Updated\s+\d{4}[-/]\d{2}[-/]\d{2}\s*$", re.IGNORECASE | re.MULTILINE),
    # Centered page numbers like "- 42 -" or "— 42 —"
    re.compile(r"^\s*[-\u2014\u2013]\s*\d+\s*[-\u2014\u2013]\s*$", re.MULTILINE),
    # Copyright / confidential footer lines
    re.compile(
        r"^\s*(?:Copyright|Confidential|\u00a9).*\d{4}\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
]

# Standalone page-number lines (just digits, 1-4 chars). Applied only at
# page boundaries to avoid stripping legitimate numeric content in statutes.
_LONE_PAGE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")


def strip_headers_footers(text: str) -> str:
    """Remove repetitive headers, footers, and standalone page numbers.

    Applies broad patterns across the entire text, then selectively
    removes lone page-number lines that appear at page boundaries
    (within the first or last 3 lines of each page section).
    """
    # Pass 1: remove full-line header/footer patterns
    for pattern in HEADER_FOOTER_PATTERNS:
        text = pattern.sub("", text)

    # Pass 2: remove lone page numbers at page boundaries.
    # Pages are separated by double newlines (from parser joining).
    page_sections = text.split("\n\n")
    cleaned_sections: list[str] = []

    for section in page_sections:
        lines = section.split("\n")
        if len(lines) <= 6:
            # Short section — check every line
            lines = [ln for ln in lines if not _LONE_PAGE_NUMBER.match(ln)]
        else:
            # Only check first 3 and last 3 lines
            head = [ln for ln in lines[:3] if not _LONE_PAGE_NUMBER.match(ln)]
            tail = [ln for ln in lines[-3:] if not _LONE_PAGE_NUMBER.match(ln)]
            lines = head + lines[3:-3] + tail

        cleaned_sections.append("\n".join(lines))

    return "\n\n".join(cleaned_sections)


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace while preserving paragraph breaks.

    - Tabs → single space
    - 3+ consecutive newlines → 2 newlines (paragraph break)
    - 2+ spaces within a line → 1 space
    - Strip leading/trailing whitespace per line
    """
    # Tabs to spaces
    text = text.replace("\t", " ")

    # Collapse runs of 3+ newlines to exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Process line by line: collapse internal spaces, strip edges
    lines = text.split("\n")
    lines = [re.sub(r" {2,}", " ", line).strip() for line in lines]
    text = "\n".join(lines)

    # Strip overall
    return text.strip()


def normalize_text(text: str) -> str:
    """Full normalization pipeline.

    1. Strip headers and footers
    2. Normalize whitespace

    Legal section markers (Chapter, §, Section, Sub., etc.) are preserved
    because the header/footer patterns are specifically designed to not
    match them.
    """
    text = strip_headers_footers(text)
    text = normalize_whitespace(text)
    return text
