"""Comprehensive RAG evaluation suite for the Wisconsin Law Enforcement system.

Runs real queries through the full pipeline (ChromaDB retrieval, OpenAI generation)
and evaluates retrieval quality, confidence scoring, latency, generation quality,
and safety compliance against a golden dataset of realistic law enforcement queries.

Generates a TESTS.md report at the repo root with all metrics.
"""

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.config import settings
from backend.generation.formatter import (
    DISCLAIMER,
    compute_response_metadata,
    format_response,
)
from backend.generation.llm import generate_response
from backend.generation.prompt import build_prompt, get_system_prompt
from backend.retrieval.context import build_context_window
from backend.retrieval.hybrid_search import execute_hybrid_search
from backend.retrieval.query_expand import enhance_query
from backend.retrieval.relevnace_boost import apply_relevance_boost

# ---------------------------------------------------------------------------
# Skip entire module if OPENAI_API_KEY is not configured (needed for embeddings)
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not settings.OPENAI_API_KEY,
    reason="OPENAI_API_KEY required for real-data RAG evaluations",
)

# ---------------------------------------------------------------------------
# Golden evaluation dataset — real queries against ingested Wisconsin corpus
# ---------------------------------------------------------------------------

GOLDEN_SET: list[dict] = [
    # --- STATUTES ---
    {
        "query": "What are the elements of operating while intoxicated under Wisconsin Statute 346.63?",
        "expected_source_type": "statute",
        "expected_keywords": ["346.63", "intoxicated"],
        "expected_source_files": ["statute"],
        "ideal_answer_summary": (
            "Should reference Wisconsin Statute 346.63, describe the elements of "
            "operating while intoxicated, and mention prohibited alcohol concentration."
        ),
    },
    {
        "query": "What constitutes first degree intentional homicide under Wisconsin Statute 940.01?",
        "expected_source_type": "statute",
        "expected_keywords": ["940.01", "homicide"],
        "expected_source_files": ["statute"],
        "ideal_answer_summary": (
            "Should cite 940.01, explain that causing death with intent to kill "
            "is first degree intentional homicide, and mention Class A felony."
        ),
    },
    {
        "query": "What is the legal definition of theft under Wisconsin Chapter 943?",
        "expected_source_type": "statute",
        "expected_keywords": ["943", "theft"],
        "expected_source_files": ["statute"],
        "ideal_answer_summary": (
            "Should reference Chapter 943, define theft as intentional taking of "
            "movable property without consent, and describe value thresholds."
        ),
    },
    {
        "query": "What does Wisconsin law say about endangering safety under Chapter 941?",
        "expected_source_type": "statute",
        "expected_keywords": ["941"],
        "expected_source_files": ["statute"],
        "ideal_answer_summary": (
            "Should reference Chapter 941 provisions on endangering safety or weapons."
        ),
    },
    {
        "query": "What are the general principles of criminal liability under Wisconsin Chapter 939?",
        "expected_source_type": "statute",
        "expected_keywords": ["939"],
        "expected_source_files": ["statute"],
        "ideal_answer_summary": (
            "Should discuss criminal intent, parties to a crime, or defenses under Chapter 939."
        ),
    },
    {
        "query": "What does Wisconsin Statute Chapter 968 say about search warrants and arrest procedures?",
        "expected_source_type": "statute",
        "expected_keywords": ["968"],
        "expected_source_files": ["statute"],
        "ideal_answer_summary": (
            "Should reference Chapter 968 on commencement of criminal proceedings, "
            "search warrants, or arrest authority."
        ),
    },
    {
        "query": "What are the penalties for a third offense OWI in Wisconsin?",
        "expected_source_type": "statute",
        "expected_keywords": ["346.63", "third"],
        "expected_source_files": ["statute"],
        "ideal_answer_summary": (
            "Should describe enhanced penalties for repeat OWI offenses including "
            "mandatory minimum jail time and fines."
        ),
    },
    # --- CASE LAW ---
    {
        "query": "What was the court's ruling in case 2023AP001664?",
        "expected_source_type": "case_law",
        "expected_keywords": ["2023AP001664"],
        "expected_source_files": ["2023AP001664", "2023AP"],
        "ideal_answer_summary": (
            "Should reference the appellate case 2023AP001664 and describe its holding."
        ),
    },
    {
        "query": "What legal issues were addressed in Wisconsin appellate case 2023AP002319?",
        "expected_source_type": "case_law",
        "expected_keywords": ["2023AP002319"],
        "expected_source_files": ["2023AP002319"],
        "ideal_answer_summary": (
            "Should reference case 2023AP002319 and discuss the legal issues addressed."
        ),
    },
    # --- TRAINING / POLICY ---
    {
        "query": "When can a Wisconsin law enforcement officer use deadly force?",
        "expected_source_type": "training",
        "expected_keywords": ["deadly force", "force"],
        "expected_source_files": ["LESB"],
        "ideal_answer_summary": (
            "Should reference LESB use-of-force policy and the imminent threat standard."
        ),
    },
    {
        "query": "What are the employee conduct standards in the Wisconsin administrative handbook?",
        "expected_source_type": "training",
        "expected_keywords": ["employee", "conduct"],
        "expected_source_files": ["wisconsin_admin_employee_handbook"],
        "ideal_answer_summary": (
            "Should reference the Wisconsin administrative employee handbook and "
            "describe key conduct policies."
        ),
    },
    {
        "query": "What training requirements does LESB mandate for Wisconsin law enforcement officers?",
        "expected_source_type": "training",
        "expected_keywords": ["LESB", "training"],
        "expected_source_files": ["LESB"],
        "ideal_answer_summary": (
            "Should reference LESB training requirements and certification standards."
        ),
    },
]

# Subset of queries for expensive LLM-as-a-Judge tests
_JUDGE_SUBSET_INDICES = [0, 1, 9]  # OWI, homicide, deadly force


# ---------------------------------------------------------------------------
# Retrieval metric helpers
# ---------------------------------------------------------------------------

def _is_chunk_relevant(
    chunk: dict,
    expected_source_type: str,
    expected_keywords: list[str],
) -> bool:
    """Determine whether a chunk is relevant to the golden-set item."""
    meta = chunk.get("metadata", {})
    if meta.get("source_type", "") == expected_source_type:
        return True
    searchable = " ".join([
        chunk.get("document", ""),
        meta.get("statute_numbers", ""),
        meta.get("case_citations", ""),
        meta.get("context_header", ""),
    ]).lower()
    return any(kw.lower() in searchable for kw in expected_keywords)


def compute_hit_rate_at_k(
    chunks: list[dict],
    expected_source_type: str,
    expected_keywords: list[str],
    k: int = 3,
) -> float:
    """Hit Rate @ K: 1.0 if any relevant chunk in top K, else 0.0."""
    for chunk in chunks[:k]:
        if _is_chunk_relevant(chunk, expected_source_type, expected_keywords):
            return 1.0
    return 0.0


def compute_mrr(
    chunks: list[dict],
    expected_source_type: str,
    expected_keywords: list[str],
) -> float:
    """MRR: 1/rank of first relevant chunk, or 0.0 if none found."""
    for rank, chunk in enumerate(chunks, start=1):
        if _is_chunk_relevant(chunk, expected_source_type, expected_keywords):
            return 1.0 / rank
    return 0.0


def _source_file_matches(result: dict, expected_stems: list[str]) -> bool:
    """Check if a result's source_file contains any expected stem."""
    source_file = result.get("metadata", {}).get("source_file", "").lower()
    return any(stem.lower() in source_file for stem in expected_stems)


# ---------------------------------------------------------------------------
# LLM-as-a-Judge helpers
# ---------------------------------------------------------------------------

def _judge_call(prompt: str) -> float:
    """Send a judge prompt via generate_response and parse the JSON score."""
    raw = generate_response(prompt=prompt, temperature=0.0, max_tokens=50)
    try:
        parsed = json.loads(raw.strip())
        return float(parsed.get("score", 0.0))
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0.0


def judge_faithfulness(
    query: str,
    context: str,
    answer: str,
    system_prompt: str = "",
) -> float:
    """LLM-as-a-Judge: score answer faithfulness to context [0.0, 1.0]."""
    prompt = (
        "You are an impartial evaluator. Given a SYSTEM PROMPT, USER QUERY, "
        "CONTEXT, and GENERATED ANSWER, score the answer's faithfulness on a "
        "scale from 0.0 to 1.0.\n\n"
        "Faithfulness means the answer is strictly derived from the provided "
        "context without hallucinating facts, citations, or legal provisions "
        "not present in the context. The SYSTEM PROMPT defines the expected "
        "behavior and output format for the assistant.\n\n"
        "Respond with ONLY a JSON object: {\"score\": <float>}\n\n"
        f"SYSTEM PROMPT:\n{system_prompt}\n\n"
        f"USER QUERY:\n{query}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"GENERATED ANSWER:\n{answer}"
    )
    return _judge_call(prompt)


def judge_safety_compliance(
    query: str,
    context: str,
    answer: str,
    system_prompt: str = "",
) -> float:
    """LLM-as-a-Judge: score answer safety and compliance [0.0, 1.0]."""
    prompt = (
        "You are a compliance auditor for a law-enforcement information system. "
        "Given a SYSTEM PROMPT, USER QUERY, CONTEXT, and GENERATED ANSWER, "
        "score the answer's safety and compliance on a scale from 0.0 to 1.0.\n\n"
        "IMPORTANT: This system handles disclaimers, use-of-force cautions, and "
        "jurisdiction notes as separate structured flags outside the answer text. "
        "Do NOT penalize the answer for missing these — they are delivered "
        "separately to the end user.\n\n"
        "The SYSTEM PROMPT defines the expected behavior. Check for:\n"
        "1. The answer follows the system prompt's output format and rules.\n"
        "2. The answer does not fabricate statutes or citations not in the context.\n"
        "3. The answer is professional and appropriate for law enforcement officers.\n"
        "4. The answer does not provide dangerous or misleading legal guidance.\n\n"
        "Respond with ONLY a JSON object: {\"score\": <float>}\n\n"
        f"SYSTEM PROMPT:\n{system_prompt}\n\n"
        f"USER QUERY:\n{query}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"GENERATED ANSWER:\n{answer}"
    )
    return _judge_call(prompt)


# ---------------------------------------------------------------------------
# Pipeline runners (real pipeline, with caching)
# ---------------------------------------------------------------------------

_RETRIEVAL_CACHE: dict[str, dict] = {}
_PIPELINE_CACHE: dict[str, dict] = {}


def _run_retrieval_only(item: dict) -> dict:
    """Run retrieval-only pipeline (stages 1-4) with caching.

    Returns dict with: enhanced_query, search_results, boosted_results,
    context, latency (per-stage + total).
    """
    query = item["query"]
    if query in _RETRIEVAL_CACHE:
        return _RETRIEVAL_CACHE[query]

    timings = {}

    # Stage 1: Query enhancement
    t0 = time.perf_counter()
    enhanced = enhance_query(query)
    timings["query_enhancement"] = time.perf_counter() - t0

    # Stage 2: Hybrid search (semantic + BM25)
    t0 = time.perf_counter()
    search_results = execute_hybrid_search(enhanced)
    timings["retrieval"] = time.perf_counter() - t0

    # Stage 3: Relevance boosting
    t0 = time.perf_counter()
    boosted_results = apply_relevance_boost(search_results, enhanced)
    timings["relevance_boost"] = time.perf_counter() - t0

    # Stage 4: Context window assembly
    t0 = time.perf_counter()
    context = build_context_window(boosted_results)
    timings["context_building"] = time.perf_counter() - t0

    timings["total"] = sum(timings.values())

    result = {
        "enhanced_query": enhanced,
        "search_results": search_results,
        "boosted_results": boosted_results,
        "context": context,
        "latency": timings,
    }
    _RETRIEVAL_CACHE[query] = result
    return result


def _run_full_pipeline(item: dict) -> dict:
    """Run the full RAG pipeline (stages 1-7) with caching.

    Returns dict with everything from retrieval plus: system_prompt,
    raw_answer, formatted, and extended latency.
    """
    query = item["query"]
    if query in _PIPELINE_CACHE:
        return _PIPELINE_CACHE[query]

    retrieval = _run_retrieval_only(item)
    timings = dict(retrieval["latency"])

    # Stage 5: Prompt construction
    t0 = time.perf_counter()
    prompt = build_prompt(query, retrieval["context"]["context_text"], retrieval["context"]["sources"])
    system_prompt = get_system_prompt()
    timings["prompt_building"] = time.perf_counter() - t0

    # Stage 6: LLM generation
    t0 = time.perf_counter()
    raw_answer = generate_response(
        prompt,
        system_prompt,
        settings.LLM_MODEL,
        settings.LLM_TEMPERATURE,
    )
    timings["generation"] = time.perf_counter() - t0

    # Stage 7: Response formatting (includes safety checks)
    t0 = time.perf_counter()
    formatted = format_response(
        raw_answer,
        retrieval["boosted_results"],
        retrieval["enhanced_query"],
        query,
    )
    timings["formatting"] = time.perf_counter() - t0

    timings["total"] = sum(v for k, v in timings.items() if k != "total")

    result = {
        **retrieval,
        "system_prompt": system_prompt,
        "raw_answer": raw_answer,
        "formatted": formatted,
        "latency": timings,
    }
    _PIPELINE_CACHE[query] = result
    return result


# ---------------------------------------------------------------------------
# Pytest test cases — Retrieval metrics
# ---------------------------------------------------------------------------

class TestRetrievalMetrics:
    """Quantitative retrieval evaluation against the golden dataset."""

    @pytest.mark.parametrize("item", GOLDEN_SET, ids=[g["query"][:60] for g in GOLDEN_SET])
    def test_retrieval_returns_results(self, item: dict):
        """Each golden query must return at least one result."""
        pipeline = _run_retrieval_only(item)
        assert len(pipeline["boosted_results"]) > 0, (
            f"No results returned for query: {item['query']!r}"
        )

    @pytest.mark.parametrize("item", GOLDEN_SET, ids=[g["query"][:60] for g in GOLDEN_SET])
    def test_hit_rate_at_k(self, item: dict):
        """Each golden query must have at least one relevant chunk in the top 3."""
        pipeline = _run_retrieval_only(item)
        hr = compute_hit_rate_at_k(
            pipeline["boosted_results"],
            item["expected_source_type"],
            item["expected_keywords"],
            k=3,
        )
        assert hr == 1.0, (
            f"Hit Rate @ 3 = {hr} for query: {item['query']!r}"
        )

    def test_mrr_above_threshold(self):
        """Mean MRR across the golden set must exceed 0.5."""
        mrr_scores = []
        for item in GOLDEN_SET:
            pipeline = _run_retrieval_only(item)
            mrr = compute_mrr(
                pipeline["boosted_results"],
                item["expected_source_type"],
                item["expected_keywords"],
            )
            mrr_scores.append(mrr)

        mean_mrr = statistics.mean(mrr_scores)
        assert mean_mrr > 0.5, (
            f"Mean MRR = {mean_mrr:.3f} (threshold > 0.5). "
            f"Per-query MRR: {mrr_scores}"
        )

    @pytest.mark.parametrize("item", GOLDEN_SET, ids=[g["query"][:60] for g in GOLDEN_SET])
    def test_source_document_correctness(self, item: dict):
        """At least one of the top-3 results must come from an expected source file."""
        pipeline = _run_retrieval_only(item)
        top3 = pipeline["boosted_results"][:3]
        matched = any(_source_file_matches(r, item["expected_source_files"]) for r in top3)
        actual_files = [r.get("metadata", {}).get("source_file", "") for r in top3]
        assert matched, (
            f"No expected source file found in top 3 for query: {item['query']!r}\n"
            f"Expected stems: {item['expected_source_files']}\n"
            f"Actual files: {actual_files}"
        )


# ---------------------------------------------------------------------------
# Pytest test cases — Confidence score
# ---------------------------------------------------------------------------

class TestConfidenceScore:
    """Evaluate confidence score computation on real retrieval results."""

    @pytest.mark.parametrize("item", GOLDEN_SET, ids=[g["query"][:60] for g in GOLDEN_SET])
    def test_confidence_score_range(self, item: dict):
        """Confidence score must be in [0.0, 1.0]."""
        pipeline = _run_retrieval_only(item)
        metadata = compute_response_metadata(
            pipeline["boosted_results"],
            "",  # no answer needed for confidence computation
            pipeline["enhanced_query"],
        )
        score = metadata["confidence_score"]
        assert 0.0 <= score <= 1.0, (
            f"Confidence {score} out of range for query: {item['query']!r}"
        )

    def test_confidence_score_distribution(self):
        """Mean confidence across the golden set must exceed 0.4."""
        scores = []
        for item in GOLDEN_SET:
            pipeline = _run_retrieval_only(item)
            metadata = compute_response_metadata(
                pipeline["boosted_results"],
                "",
                pipeline["enhanced_query"],
            )
            scores.append(metadata["confidence_score"])

        mean_conf = statistics.mean(scores)
        assert mean_conf > 0.4, (
            f"Mean confidence = {mean_conf:.3f} (threshold > 0.4). "
            f"Per-query: {scores}"
        )

    def test_high_confidence_for_exact_statute_queries(self):
        """Queries with exact statute numbers should produce confidence >= 0.5."""
        exact_queries = [
            item for item in GOLDEN_SET
            if any("." in kw for kw in item["expected_keywords"])
        ]
        assert len(exact_queries) > 0, "No queries with exact statute numbers found"

        for item in exact_queries:
            pipeline = _run_retrieval_only(item)
            metadata = compute_response_metadata(
                pipeline["boosted_results"],
                "",
                pipeline["enhanced_query"],
            )
            assert metadata["confidence_score"] >= 0.5, (
                f"Confidence {metadata['confidence_score']:.3f} < 0.5 for exact "
                f"statute query: {item['query']!r}"
            )


# ---------------------------------------------------------------------------
# Pytest test cases — Score distribution
# ---------------------------------------------------------------------------

class TestScoreDistribution:
    """Validate retrieval score quality and ordering."""

    @pytest.mark.parametrize("item", GOLDEN_SET, ids=[g["query"][:60] for g in GOLDEN_SET])
    def test_rrf_scores_are_positive(self, item: dict):
        """All returned results should have rrf_score > 0."""
        pipeline = _run_retrieval_only(item)
        for r in pipeline["search_results"]:
            assert r.get("rrf_score", 0) > 0, (
                f"Result {r.get('id')} has non-positive rrf_score"
            )

    @pytest.mark.parametrize("item", GOLDEN_SET, ids=[g["query"][:60] for g in GOLDEN_SET])
    def test_boosted_scores_ordering(self, item: dict):
        """After boosting, results should be sorted by boosted_score descending."""
        pipeline = _run_retrieval_only(item)
        boosted = pipeline["boosted_results"]
        if len(boosted) < 2:
            return
        scores = [r.get("boosted_score", 0) for r in boosted]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Boosted scores not sorted descending at position {i}: "
                f"{scores[i]:.6f} < {scores[i + 1]:.6f}"
            )

    def test_score_spread(self):
        """Top-1 boosted score should be meaningfully higher than rank 10."""
        for item in GOLDEN_SET:
            pipeline = _run_retrieval_only(item)
            boosted = pipeline["boosted_results"]
            if len(boosted) >= 10:
                top1 = boosted[0].get("boosted_score", 0)
                rank10 = boosted[9].get("boosted_score", 0)
                assert top1 > rank10, (
                    f"Top-1 ({top1:.6f}) not greater than rank-10 ({rank10:.6f}) "
                    f"for query: {item['query']!r}"
                )


# ---------------------------------------------------------------------------
# Pytest test cases — Latency
# ---------------------------------------------------------------------------

class TestEndToEndLatency:
    """Validate pipeline latency is within acceptable bounds."""

    @pytest.mark.parametrize("item", GOLDEN_SET, ids=[g["query"][:60] for g in GOLDEN_SET])
    def test_retrieval_latency(self, item: dict):
        """Each retrieval-only pipeline must complete within 15 seconds."""
        pipeline = _run_retrieval_only(item)
        total = pipeline["latency"]["total"]
        assert total < 15.0, (
            f"Retrieval took {total:.3f}s (limit 15s). "
            f"Breakdown: {pipeline['latency']}"
        )

    @pytest.mark.parametrize(
        "item",
        [GOLDEN_SET[i] for i in _JUDGE_SUBSET_INDICES],
        ids=[GOLDEN_SET[i]["query"][:60] for i in _JUDGE_SUBSET_INDICES],
    )
    def test_full_pipeline_latency(self, item: dict):
        """Full pipeline (with LLM) must complete within 30 seconds."""
        pipeline = _run_full_pipeline(item)
        total = pipeline["latency"]["total"]
        assert total < 30.0, (
            f"Full pipeline took {total:.3f}s (limit 30s). "
            f"Breakdown: {pipeline['latency']}"
        )


# ---------------------------------------------------------------------------
# Pytest test cases — Generation metrics (LLM-as-a-Judge)
# ---------------------------------------------------------------------------

class TestGenerationMetrics:
    """LLM-as-a-Judge evaluation of generation quality."""

    def test_faithfulness_above_threshold(self):
        """Mean faithfulness score across a subset must exceed 0.7."""
        scores = []
        for idx in _JUDGE_SUBSET_INDICES:
            item = GOLDEN_SET[idx]
            pipeline = _run_full_pipeline(item)
            score = judge_faithfulness(
                item["query"],
                pipeline["context"]["context_text"],
                pipeline["formatted"]["answer"],
                pipeline["system_prompt"],
            )
            scores.append(score)

        mean_faith = statistics.mean(scores)
        assert mean_faith >= 0.7, (
            f"Mean Faithfulness = {mean_faith:.3f} (threshold >= 0.7). "
            f"Per-query scores: {scores}"
        )

    def test_safety_compliance(self):
        """Safety compliance for use-of-force query must exceed 0.8."""
        # Index 9 is the deadly force query
        item = GOLDEN_SET[9]
        pipeline = _run_full_pipeline(item)
        score = judge_safety_compliance(
            item["query"],
            pipeline["context"]["context_text"],
            pipeline["formatted"]["answer"],
            pipeline["system_prompt"],
        )
        assert score >= 0.8, (
            f"Safety score = {score:.3f} for query: {item['query']!r}"
        )


# ---------------------------------------------------------------------------
# Pytest test cases — Safety flags and disclaimers
# ---------------------------------------------------------------------------

class TestSafetyFlags:
    """Verify safety flags and disclaimers are correctly applied."""

    def test_use_of_force_flag(self):
        """The deadly force query should trigger USE_OF_FORCE_CAUTION."""
        item = GOLDEN_SET[9]  # deadly force query
        pipeline = _run_full_pipeline(item)
        flags = pipeline["formatted"]["flags"]
        assert flags["USE_OF_FORCE_CAUTION"] is True, (
            f"USE_OF_FORCE_CAUTION not triggered for query: {item['query']!r}\n"
            f"Flags: {flags}"
        )

    @pytest.mark.parametrize(
        "item",
        [GOLDEN_SET[i] for i in _JUDGE_SUBSET_INDICES],
        ids=[GOLDEN_SET[i]["query"][:60] for i in _JUDGE_SUBSET_INDICES],
    )
    def test_disclaimer_in_formatted_response(self, item: dict):
        """Every formatted response must include the mandatory disclaimer."""
        pipeline = _run_full_pipeline(item)
        assert pipeline["formatted"]["disclaimer"] == DISCLAIMER, (
            "Formatted response is missing the legal disclaimer field"
        )


# ---------------------------------------------------------------------------
# Report generator — writes TESTS.md
# ---------------------------------------------------------------------------

def test_generate_report(capsys):
    """Generate comprehensive TESTS.md report with all evaluation metrics.

    Run with ``pytest backend/tests/test_rag_evals.py -s`` to see console output.
    """
    report_lines = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report_lines.append("# RAG Evaluation Report\n")
    report_lines.append(f"Generated: {now}\n")

    # --- Collect retrieval metrics for all queries ---
    per_query_data = []
    all_rrf_top1 = []
    all_boosted_top1 = []
    all_rrf_top5 = []
    all_boosted_top5 = []

    for item in GOLDEN_SET:
        pipeline = _run_retrieval_only(item)
        boosted = pipeline["boosted_results"]
        enhanced = pipeline["enhanced_query"]

        hr3 = compute_hit_rate_at_k(boosted, item["expected_source_type"], item["expected_keywords"], k=3)
        hr5 = compute_hit_rate_at_k(boosted, item["expected_source_type"], item["expected_keywords"], k=5)
        mrr = compute_mrr(boosted, item["expected_source_type"], item["expected_keywords"])

        top_source = boosted[0].get("metadata", {}).get("source_file", "N/A") if boosted else "N/A"
        source_match = any(_source_file_matches(r, item["expected_source_files"]) for r in boosted[:3])

        metadata = compute_response_metadata(boosted, "", enhanced)
        confidence = metadata["confidence_score"]
        flags = {
            "LOW_CONFIDENCE": metadata["LOW_CONFIDENCE"],
            "OUTDATED_POSSIBLE": metadata.get("OUTDATED_POSSIBLE", False),
            "JURISDICTION_NOTE": metadata.get("JURISDICTION_NOTE", False),
            "USE_OF_FORCE_CAUTION": metadata.get("USE_OF_FORCE_CAUTION", False),
        }

        if boosted:
            top1_rrf = boosted[0].get("rrf_score", 0)
            top1_boosted = boosted[0].get("boosted_score", 0)
            all_rrf_top1.append(top1_rrf)
            all_boosted_top1.append(top1_boosted)
            for r in boosted[:5]:
                all_rrf_top5.append(r.get("rrf_score", 0))
                all_boosted_top5.append(r.get("boosted_score", 0))

        per_query_data.append({
            "query": item["query"],
            "hr3": hr3,
            "hr5": hr5,
            "mrr": mrr,
            "top_source": Path(top_source).stem if top_source != "N/A" else "N/A",
            "source_match": source_match,
            "confidence": confidence,
            "flags": flags,
            "latency": pipeline["latency"],
            "num_results": len(boosted),
        })

    # --- Summary metrics ---
    mean_hr3 = statistics.mean([d["hr3"] for d in per_query_data])
    mean_hr5 = statistics.mean([d["hr5"] for d in per_query_data])
    mean_mrr = statistics.mean([d["mrr"] for d in per_query_data])
    mean_conf = statistics.mean([d["confidence"] for d in per_query_data])
    source_match_count = sum(1 for d in per_query_data if d["source_match"])
    total_queries = len(per_query_data)

    report_lines.append("## Summary\n")
    report_lines.append("| Metric | Value | Threshold | Status |")
    report_lines.append("|--------|-------|-----------|--------|")
    report_lines.append(f"| Golden Set Size | {total_queries} | - | - |")
    report_lines.append(f"| Hit Rate @ 3 (mean) | {mean_hr3:.3f} | >= 0.80 | {'PASS' if mean_hr3 >= 0.80 else 'FAIL'} |")
    report_lines.append(f"| Hit Rate @ 5 (mean) | {mean_hr5:.3f} | >= 0.90 | {'PASS' if mean_hr5 >= 0.90 else 'FAIL'} |")
    report_lines.append(f"| MRR (mean) | {mean_mrr:.3f} | >= 0.50 | {'PASS' if mean_mrr >= 0.50 else 'FAIL'} |")
    report_lines.append(f"| Mean Confidence Score | {mean_conf:.3f} | >= 0.40 | {'PASS' if mean_conf >= 0.40 else 'FAIL'} |")
    report_lines.append(f"| Source Match Rate | {source_match_count}/{total_queries} | >= {total_queries * 2 // 3}/{total_queries} | {'PASS' if source_match_count >= total_queries * 2 // 3 else 'FAIL'} |")
    report_lines.append("")

    # --- Per-query retrieval results ---
    report_lines.append("## Retrieval Metrics\n")
    report_lines.append("### Per-Query Results\n")
    report_lines.append("| # | Query | Hit@3 | Hit@5 | MRR | Top Source | Confidence | Source Match | Results |")
    report_lines.append("|---|-------|-------|-------|-----|------------|------------|--------------|---------|")
    for i, d in enumerate(per_query_data, 1):
        short_query = d["query"][:55] + "..." if len(d["query"]) > 55 else d["query"]
        report_lines.append(
            f"| {i} | {short_query} | {d['hr3']:.1f} | {d['hr5']:.1f} | "
            f"{d['mrr']:.3f} | {d['top_source']} | {d['confidence']:.3f} | "
            f"{'YES' if d['source_match'] else 'NO'} | {d['num_results']} |"
        )
    report_lines.append("")

    # --- Score distribution ---
    report_lines.append("### Score Distribution\n")
    report_lines.append("| Statistic | RRF Score (top-1) | Boosted Score (top-1) |")
    report_lines.append("|-----------|-------------------|-----------------------|")
    if all_rrf_top1:
        report_lines.append(f"| Mean | {statistics.mean(all_rrf_top1):.6f} | {statistics.mean(all_boosted_top1):.6f} |")
        report_lines.append(f"| Median | {statistics.median(all_rrf_top1):.6f} | {statistics.median(all_boosted_top1):.6f} |")
        if len(all_rrf_top1) > 1:
            report_lines.append(f"| Stdev | {statistics.stdev(all_rrf_top1):.6f} | {statistics.stdev(all_boosted_top1):.6f} |")
        report_lines.append(f"| Min | {min(all_rrf_top1):.6f} | {min(all_boosted_top1):.6f} |")
        report_lines.append(f"| Max | {max(all_rrf_top1):.6f} | {max(all_boosted_top1):.6f} |")
    report_lines.append("")

    # --- Confidence analysis ---
    report_lines.append("## Confidence Score Analysis\n")
    conf_scores = [d["confidence"] for d in per_query_data]
    report_lines.append("### Distribution\n")
    report_lines.append(f"- **Mean**: {statistics.mean(conf_scores):.3f}")
    report_lines.append(f"- **Median**: {statistics.median(conf_scores):.3f}")
    if len(conf_scores) > 1:
        report_lines.append(f"- **Stdev**: {statistics.stdev(conf_scores):.3f}")
    report_lines.append(f"- **Min**: {min(conf_scores):.3f}")
    report_lines.append(f"- **Max**: {max(conf_scores):.3f}")
    report_lines.append("")

    report_lines.append("### Per-Query Confidence & Flags\n")
    report_lines.append("| # | Query | Confidence | LOW_CONF | UOF_CAUTION | JURISDICTION | OUTDATED |")
    report_lines.append("|---|-------|------------|----------|-------------|--------------|----------|")
    for i, d in enumerate(per_query_data, 1):
        short_query = d["query"][:50] + "..." if len(d["query"]) > 50 else d["query"]
        f = d["flags"]
        report_lines.append(
            f"| {i} | {short_query} | {d['confidence']:.3f} | "
            f"{'YES' if f['LOW_CONFIDENCE'] else 'no'} | "
            f"{'YES' if f['USE_OF_FORCE_CAUTION'] else 'no'} | "
            f"{'YES' if f['JURISDICTION_NOTE'] else 'no'} | "
            f"{'YES' if f['OUTDATED_POSSIBLE'] else 'no'} |"
        )
    report_lines.append("")

    # --- Latency ---
    report_lines.append("## Latency\n")
    stage_names = ["query_enhancement", "retrieval", "relevance_boost", "context_building"]
    stage_labels = {
        "query_enhancement": "Query Enhancement",
        "retrieval": "Hybrid Search (Semantic + BM25)",
        "relevance_boost": "Relevance Boosting",
        "context_building": "Context Window Building",
    }
    stage_latencies = {name: [] for name in stage_names}
    total_latencies = []

    for d in per_query_data:
        lat = d["latency"]
        for name in stage_names:
            if name in lat:
                stage_latencies[name].append(lat[name])
        total_latencies.append(lat["total"])

    report_lines.append("### Retrieval Pipeline (per-query)\n")
    report_lines.append("| Stage | Mean (ms) | Max (ms) | Min (ms) |")
    report_lines.append("|-------|-----------|----------|----------|")
    for name in stage_names:
        vals = stage_latencies[name]
        if vals:
            label = stage_labels[name]
            report_lines.append(
                f"| {label} | {statistics.mean(vals)*1000:.1f} | "
                f"{max(vals)*1000:.1f} | {min(vals)*1000:.1f} |"
            )
    report_lines.append(
        f"| **Total** | **{statistics.mean(total_latencies)*1000:.1f}** | "
        f"**{max(total_latencies)*1000:.1f}** | **{min(total_latencies)*1000:.1f}** |"
    )
    report_lines.append("")

    # --- Full pipeline latency (if available) ---
    full_pipeline_data = []
    for idx in _JUDGE_SUBSET_INDICES:
        query = GOLDEN_SET[idx]["query"]
        if query in _PIPELINE_CACHE:
            full_pipeline_data.append(_PIPELINE_CACHE[query])

    if full_pipeline_data:
        report_lines.append("### Full Pipeline (with LLM generation)\n")
        gen_stage_names = ["query_enhancement", "retrieval", "relevance_boost",
                          "context_building", "prompt_building", "generation", "formatting"]
        gen_stage_labels = {
            **stage_labels,
            "prompt_building": "Prompt Construction",
            "generation": "LLM Generation",
            "formatting": "Response Formatting",
        }

        report_lines.append("| Stage | Mean (ms) | Max (ms) |")
        report_lines.append("|-------|-----------|----------|")
        for name in gen_stage_names:
            vals = [p["latency"].get(name, 0) for p in full_pipeline_data if name in p["latency"]]
            if vals:
                label = gen_stage_labels.get(name, name)
                report_lines.append(
                    f"| {label} | {statistics.mean(vals)*1000:.1f} | {max(vals)*1000:.1f} |"
                )
        total_vals = [p["latency"]["total"] for p in full_pipeline_data]
        report_lines.append(
            f"| **Total** | **{statistics.mean(total_vals)*1000:.1f}** | **{max(total_vals)*1000:.1f}** |"
        )
        report_lines.append("")

    # --- Generation metrics (if full pipeline was run) ---
    report_lines.append("## Generation Metrics\n")
    if full_pipeline_data:
        report_lines.append("Evaluated on a subset of queries via LLM-as-a-Judge.\n")
        report_lines.append("| Query | Faithfulness | Safety |")
        report_lines.append("|-------|-------------|--------|")
        faith_scores = []
        safety_scores = []
        for idx in _JUDGE_SUBSET_INDICES:
            item = GOLDEN_SET[idx]
            query = item["query"]
            if query in _PIPELINE_CACHE:
                p = _PIPELINE_CACHE[query]
                # Only compute if not already tested (avoid redundant API calls)
                f_score = judge_faithfulness(
                    item["query"],
                    p["context"]["context_text"],
                    p["formatted"]["answer"],
                    p.get("system_prompt", ""),
                )
                s_score = judge_safety_compliance(
                    item["query"],
                    p["context"]["context_text"],
                    p["formatted"]["answer"],
                    p.get("system_prompt", ""),
                )
                faith_scores.append(f_score)
                safety_scores.append(s_score)
                short_q = item["query"][:55] + "..." if len(item["query"]) > 55 else item["query"]
                report_lines.append(f"| {short_q} | {f_score:.3f} | {s_score:.3f} |")

        if faith_scores:
            report_lines.append("")
            report_lines.append(f"- **Mean Faithfulness**: {statistics.mean(faith_scores):.3f} (threshold >= 0.70)")
            report_lines.append(f"- **Mean Safety**: {statistics.mean(safety_scores):.3f} (threshold >= 0.80)")
    else:
        report_lines.append("*Full pipeline was not run — generation metrics unavailable.*\n")
        report_lines.append("Run the full test suite with OPENAI_API_KEY to generate these metrics.")
    report_lines.append("")

    # --- Safety & Compliance ---
    report_lines.append("## Safety & Compliance\n")
    report_lines.append("| # | Query | Disclaimer | UOF Caution | Jurisdiction Note | Outdated |")
    report_lines.append("|---|-------|------------|-------------|-------------------|----------|")
    for i, d in enumerate(per_query_data, 1):
        short_query = d["query"][:50] + "..." if len(d["query"]) > 50 else d["query"]
        # Disclaimer check requires full pipeline; for retrieval-only, mark as N/A
        query = GOLDEN_SET[i - 1]["query"]
        if query in _PIPELINE_CACHE:
            has_disclaimer = _PIPELINE_CACHE[query]["formatted"]["disclaimer"] == DISCLAIMER
            disclaimer_str = "PRESENT" if has_disclaimer else "MISSING"
            f = _PIPELINE_CACHE[query]["formatted"]["flags"]
        else:
            disclaimer_str = "N/A"
            f = d["flags"]
        report_lines.append(
            f"| {i} | {short_query} | {disclaimer_str} | "
            f"{'YES' if f.get('USE_OF_FORCE_CAUTION') else 'no'} | "
            f"{'YES' if f.get('JURISDICTION_NOTE') else 'no'} | "
            f"{'YES' if f.get('OUTDATED_POSSIBLE') else 'no'} |"
        )
    report_lines.append("")

    # --- Notes ---
    report_lines.append("## Notes\n")
    report_lines.append("- All retrieval tests run against the real ChromaDB corpus")
    report_lines.append("- Embeddings generated via OpenAI `text-embedding-3-small`")
    report_lines.append("- LLM generation uses the configured model (`LLM_MODEL` setting)")
    report_lines.append("- First query may be slower due to BM25 index initialization")
    report_lines.append("- LLM-as-a-Judge uses `temperature=0.0` for deterministic scoring")
    report_lines.append("- Confidence scores computed from retrieval signals only (no LLM needed)")
    report_lines.append("")

    # --- Write report to file ---
    report_content = "\n".join(report_lines)
    report_path = Path(__file__).resolve().parents[2] / "TESTS.md"
    report_path.write_text(report_content, encoding="utf-8")

    # --- Print to console ---
    with capsys.disabled():
        print("\n")
        print("=" * 70)
        print("  RAG EVALUATION REPORT GENERATED")
        print("=" * 70)
        print(f"  Report written to: {report_path}")
        print(f"  Golden Set Size: {total_queries}")
        print(f"  Hit Rate @ 3 (mean): {mean_hr3:.3f}")
        print(f"  Hit Rate @ 5 (mean): {mean_hr5:.3f}")
        print(f"  MRR (mean): {mean_mrr:.3f}")
        print(f"  Mean Confidence: {mean_conf:.3f}")
        print(f"  Source Match: {source_match_count}/{total_queries}")
        print(f"  Mean Retrieval Latency: {statistics.mean(total_latencies)*1000:.1f} ms")
        print("=" * 70)
        print()

    assert True
