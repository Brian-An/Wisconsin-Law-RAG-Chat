"""Tests for the ingestion pipeline modules."""

import pytest

from backend.ingestion.normalizer import normalize_text, strip_headers_footers
from backend.ingestion.metadata import (
    extract_statute_numbers,
    extract_case_citations,
    extract_chapter_numbers,
    infer_source_type,
    infer_jurisdiction,
    generate_doc_id,
)
from backend.ingestion.chunking import (
    count_tokens,
    detect_hierarchy,
    build_context_header,
    _build_context_path,
    STATUTE_CONFIG,
    chunk_document,
)
from backend.ingestion.parser import ParsedDocument, ParsedPage

# ---------------------------------------------------------------------------
# Normalizer tests
# ---------------------------------------------------------------------------

class TestNormalizer:
    def test_strips_page_headers(self):
        text = "Page 1 of 10\nActual content here."
        result = strip_headers_footers(text)
        assert "Page 1 of 10" not in result
        assert "Actual content here" in result

    def test_preserves_section_markers(self):
        text = "Chapter 943 - Crimes Against Property\n§ 940.01 First Degree Homicide"
        result = normalize_text(text)
        assert "Chapter 943" in result
        assert "§ 940.01" in result

    def test_normalizes_whitespace(self):
        text = "Line one\n\n\n\n\nLine two"
        result = normalize_text(text)
        assert "\n\n\n" not in result
        assert "Line one" in result
        assert "Line two" in result


# ---------------------------------------------------------------------------
# Metadata extraction tests
# ---------------------------------------------------------------------------

class TestMetadataExtraction:
    def test_extract_statute_numbers(self):
        text = "Under § 940.01(2)(a) and section 346.63(1), the law states..."
        nums = extract_statute_numbers(text)
        assert "940.01(2)(a)" in nums
        assert "346.63(1)" in nums

    def test_extract_case_citations(self):
        text = "In 2023 WI App 45, the court decided... Also see 2023AP001234."
        cites = extract_case_citations(text)
        assert any("2023" in c and "App" in c for c in cites) or \
               any("2023" in c for c in cites)

    def test_extract_chapter_numbers(self):
        text = "Chapter 943 covers property crimes. See also Chapter 940."
        chapters = extract_chapter_numbers(text)
        assert "943" in chapters
        assert "940" in chapters

    def test_infer_source_type_statute(self):
        assert infer_source_type("statutes") == "statute"

    def test_infer_source_type_case_law(self):
        assert infer_source_type("case_law") == "case_law"

    def test_infer_source_type_unknown(self):
        assert infer_source_type("random_folder") == "unknown"

    def test_infer_jurisdiction_state(self):
        result = infer_jurisdiction("Wisconsin state statute content", "statute_1.pdf")
        assert result == "state"

    def test_infer_jurisdiction_local(self):
        result = infer_jurisdiction("City of Madison police department policy", "madison_policy.pdf")
        assert result == "local_department"

    def test_generate_doc_id_deterministic(self):
        id1 = generate_doc_id("text", "file.pdf", 0)
        id2 = generate_doc_id("text", "file.pdf", 0)
        assert id1 == id2

    def test_generate_doc_id_unique_for_different_input(self):
        id1 = generate_doc_id("text1", "file.pdf", 0)
        id2 = generate_doc_id("text2", "file.pdf", 0)
        assert id1 != id2


# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------

class TestChunking:
    def test_count_tokens_nonempty(self):
        tokens = count_tokens("This is a simple test sentence.")
        assert tokens > 0

    def test_count_tokens_empty(self):
        tokens = count_tokens("")
        assert tokens == 0

    def test_detect_hierarchy_finds_chapter(self):
        text = "Chapter 940\nSome content here\n§ 940.01 First Degree Homicide\nMore text"
        nodes = detect_hierarchy(text)
        # Should find at least the Chapter node
        assert any(n.title and "940" in n.title for n in nodes)

    def test_detect_hierarchy_empty_text(self):
        nodes = detect_hierarchy("")
        assert nodes == []


# ---------------------------------------------------------------------------
# Chapter 943 statute fixture tests
# ---------------------------------------------------------------------------

STATUTE_TEXT = """\
CHAPTER 943
CRIMES AGAINST PROPERTY

943.01 Damage to property. (1) Whoever intentionally
causes damage to any physical property of another without the
person's consent is guilty of a Class A misdemeanor.
(2) Any person violating sub. (1) under any of the following
circumstances is guilty of a Class I felony:

(a) 1. In this paragraph, "highway" means any public way or
thoroughfare, including bridges thereon, any roadways commonly
used for vehicular traffic, whether public or private, any railroad,
including street and interurban railways, and any navigable water-
way or airport.

2. The property damaged is a vehicle or highway and the
damage is of a kind which is likely to cause injury to a person or
further property damage.

(b) The property damaged belongs to a public utility or com-
mon carrier and the damage is of a kind which is likely to impair
the services of the public utility or common carrier.
"""


def _parsed_doc_943() -> ParsedDocument:
    """Build a minimal ParsedDocument wrapping the Chapter 943 fixture text."""
    return ParsedDocument(
        file_path="data/statute/statute_943.pdf",
        file_name="statute_943.pdf",
        subfolder="statute",
        pages=[ParsedPage(page_number=1, text=STATUTE_TEXT.strip())],
    )


class TestChapter943Statute:
    """Tests that hierarchy is preserved, metadata is extracted, and chunks are built
    correctly for the Chapter 943 / § 943.01 damage-to-property statute text.
    """

    # ------------------------------------------------------------------
    # Hierarchy detection
    # ------------------------------------------------------------------

    def test_detects_section_943_01(self):
        """The bare section number '943.01' must be detected as a level-1 node."""
        nodes = detect_hierarchy(STATUTE_TEXT, config=STATUTE_CONFIG)
        level1_titles = [n.title for n in nodes if n.level == 1]
        assert "943.01" in level1_titles

    def test_detects_subsection_2(self):
        """Numbered subsection '(2)' must be detected as a level-2 node."""
        nodes = detect_hierarchy(STATUTE_TEXT, config=STATUTE_CONFIG)
        level2_titles = [n.title for n in nodes if n.level == 2]
        assert "(2)" in level2_titles

    def test_detects_paragraph_a(self):
        """Lettered paragraph '(a)' must be detected as a level-3 node."""
        nodes = detect_hierarchy(STATUTE_TEXT, config=STATUTE_CONFIG)
        level3_titles = [n.title for n in nodes if n.level == 3]
        assert "(a)" in level3_titles

    def test_detects_paragraph_b(self):
        """Lettered paragraph '(b)' must be detected as a level-3 node."""
        nodes = detect_hierarchy(STATUTE_TEXT, config=STATUTE_CONFIG)
        level3_titles = [n.title for n in nodes if n.level == 3]
        assert "(b)" in level3_titles

    def test_hierarchy_ordering(self):
        """Nodes must be ordered by their position in the text: section → sub → paragraph."""
        nodes = detect_hierarchy(STATUTE_TEXT, config=STATUTE_CONFIG)
        positions = [n.start_pos for n in nodes]
        assert positions == sorted(positions), "Nodes are not in document order"

    def test_section_precedes_subsection_2(self):
        """The § 943.01 section node must appear before the (2) subsection boundary."""
        nodes = detect_hierarchy(STATUTE_TEXT, config=STATUTE_CONFIG)
        section = next(n for n in nodes if n.title == "943.01")
        sub2 = next(n for n in nodes if n.title == "(2)")
        assert section.start_pos < sub2.start_pos

    def test_subsection_2_precedes_paragraph_a(self):
        """(2) must appear before (a) which is nested inside it."""
        nodes = detect_hierarchy(STATUTE_TEXT, config=STATUTE_CONFIG)
        sub2 = next(n for n in nodes if n.title == "(2)")
        para_a = next(n for n in nodes if n.title == "(a)")
        assert sub2.start_pos < para_a.start_pos

    def test_breadcrumb_for_subsection_2(self):
        """Context header at position of (2) should include '943.01' and '(2)'."""
        nodes = detect_hierarchy(STATUTE_TEXT, config=STATUTE_CONFIG)
        sub2 = next(n for n in nodes if n.title == "(2)")
        path = _build_context_path(nodes, sub2.start_pos)
        header = build_context_header(path)
        assert "943.01" in header
        assert "(2)" in header

    def test_breadcrumb_for_paragraph_a(self):
        """Context header at position of (a) should include '943.01', '(2)', and '(a)'."""
        nodes = detect_hierarchy(STATUTE_TEXT, config=STATUTE_CONFIG)
        para_a = next(n for n in nodes if n.title == "(a)")
        path = _build_context_path(nodes, para_a.start_pos)
        header = build_context_header(path)
        assert "943.01" in header
        assert "(a)" in header

    # ------------------------------------------------------------------
    # Metadata extraction
    # ------------------------------------------------------------------

    def test_extracts_statute_number_943_01(self):
        """'943.01' must be extracted from the statute text."""
        nums = extract_statute_numbers(STATUTE_TEXT)
        assert "943.01" in nums

    def test_extracts_chapter_943(self):
        """Chapter '943' must be extracted from the chapter heading."""
        chapters = extract_chapter_numbers(STATUTE_TEXT)
        assert "943" in chapters

    def test_source_type_for_statute_subfolder(self):
        """Subfolder name 'statute' (singular) must map to source_type 'statute'."""
        assert infer_source_type("statute") == "statute"

    def test_jurisdiction_is_state(self):
        """Chapter 943 content has no local jurisdiction keywords — should be 'state'."""
        result = infer_jurisdiction(STATUTE_TEXT, "statute_943.pdf")
        assert result == "state"

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    def test_chunks_are_produced(self):
        """chunk_document must produce at least one chunk from the fixture text."""
        doc = _parsed_doc_943()
        chunks = chunk_document(doc, STATUTE_TEXT, target_tokens=500, overlap_fraction=0.0)
        assert len(chunks) >= 1
        # should generate at least 2 chunks
        assert len(chunks) >= 2

    def test_section_chunk_header_contains_943_01(self):
        """The chunk containing § 943.01's body must have '943.01' in its context_header."""
        doc = _parsed_doc_943()
        chunks = chunk_document(doc, STATUTE_TEXT, target_tokens=500, overlap_fraction=0.0)
        section_chunks = [c for c in chunks if "943.01" in c.context_header]
        assert len(section_chunks) >= 1, (
            "Expected at least one chunk with '943.01' in context_header; "
            f"got headers: {[c.context_header for c in chunks]}"
        )

    def test_chunk_text_contains_damage_to_property(self):
        """At least one chunk must contain the statute's subject matter."""
        doc = _parsed_doc_943()
        chunks = chunk_document(doc, STATUTE_TEXT, target_tokens=500, overlap_fraction=0.0)
        all_text = " ".join(c.text.lower() for c in chunks)
        assert "damage" in all_text
        assert "property" in all_text

    def test_chunk_indices_are_sequential(self):
        """chunk_index values must start at 0 and be strictly sequential."""
        doc = _parsed_doc_943()
        chunks = chunk_document(doc, STATUTE_TEXT, target_tokens=500, overlap_fraction=0.0)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks))), f"Non-sequential chunk indices: {indices}"

    def test_chunk_token_counts_are_positive(self):
        """Every chunk must have a positive token count."""
        doc = _parsed_doc_943()
        chunks = chunk_document(doc, STATUTE_TEXT, target_tokens=500, overlap_fraction=0.0)
        for chunk in chunks:
            assert chunk.token_count > 0, f"Chunk {chunk.chunk_index} has zero tokens"
