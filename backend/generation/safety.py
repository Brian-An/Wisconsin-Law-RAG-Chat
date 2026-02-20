"""Post-processing guardrails for RAG responses.

Detects sensitive topics (use of force, outdated sources, jurisdiction
mismatches) and produces safety flags and addendum text.
"""

import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Terms that trigger use-of-force caution
USE_OF_FORCE_TERMS: list[str] = [
    "use of force",
    "deadly force",
    "firearm",
    "discharge",
    "taser",
    "electronic control device",
    "oc spray",
    "pepper spray",
    "baton",
    "chokehold",
    "neck restraint",
    "vehicle pursuit",
    "pursuit policy",
    "fleeing",
    "shooting",
    "force",
    "pursuit",
]

# Regex to extract a 4-digit year from a filename
_YEAR_PATTERN = re.compile(r"((?:19|20)\d{2})")

_CURRENT_YEAR = datetime.now().year


def check_use_of_force(query: str, answer_text: str) -> bool:
    """Return True if the query or answer involves use-of-force topics."""
    combined = f"{query} {answer_text}".lower()
    return any(term in combined for term in USE_OF_FORCE_TERMS)


def check_outdated_possible(sources: list[dict]) -> bool:
    """Return True if the primary cited source may be outdated (>10 years old).

    Checks source filenames for year patterns. A source is considered
    potentially outdated if its year is more than 10 years ago.
    """
    if not sources:
        return False

    # Check the primary (first) source
    primary = sources[0]
    source_file = primary.get("source_file", "")
    match = _YEAR_PATTERN.search(source_file)
    if match:
        year = int(match.group(1))
        if _CURRENT_YEAR - year > 10:
            return True
    return False


def check_jurisdiction_note(query: str, sources: list[dict]) -> bool:
    """Return True if the query is general but top sources are local-department-specific.

    A general query (no explicit jurisdiction mention) returning
    local_department results should get a jurisdiction note.
    """
    if not sources:
        return False

    # Check if query mentions a specific jurisdiction
    jurisdiction_keywords = [
        "department", "agency", "local", "city", "county",
        "madison", "milwaukee", "dane",
    ]
    query_lower = query.lower()
    query_is_specific = any(kw in query_lower for kw in jurisdiction_keywords)

    if query_is_specific:
        return False

    # Check if top source is local department
    top_source = sources[0]
    return top_source.get("source_type") == "training" or \
        "local_department" in str(top_source.get("jurisdiction", ""))


def build_safety_addendum(
    query: str,
    answer_text: str,
    sources: list[dict],
) -> dict:
    """Build safety flags and any addendum text.

    Returns:
        dict with:
            - use_of_force_caution: bool
            - outdated_possible: bool
            - jurisdiction_note: bool
            - addendum_text: str (additional text to append to the answer)
    """
    uof = check_use_of_force(query, answer_text)
    outdated = check_outdated_possible(sources)
    jurisdiction = check_jurisdiction_note(query, sources)

    addendum_parts: list[str] = []

    if uof:
        addendum_parts.append(
            "Note: This response involves use of force topics. "
            "Department-specific policies may impose additional requirements "
            "beyond state law. Consult your agency's use-of-force policy."
        )

    if outdated:
        addendum_parts.append(
            "Note: The primary source cited may be outdated. "
            "Please verify against current statutes and regulations."
        )

    if jurisdiction:
        addendum_parts.append(
            "Note: The top retrieved source is a local department policy. "
            "State-level statutes or other jurisdictions may differ."
        )

    return {
        "use_of_force_caution": uof,
        "outdated_possible": outdated,
        "jurisdiction_note": jurisdiction,
        "addendum_text": " ".join(addendum_parts),
    }
