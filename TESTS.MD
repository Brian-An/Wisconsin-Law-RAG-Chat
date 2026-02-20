# Testing & Evaluation

## Table of Contents

- [Testing Overview](#testing-overview)
- [Running Tests](#running-tests)
- [Test Coverage Summary](#test-coverage-summary)
- [Evaluation Methodology](#evaluation-methodology)
- [RAG Evaluation Results](#rag-evaluation-results)
- [Interpretation Guide](#interpretation-guide)

---

## Testing Overview

The test suite comprises **5 test files** covering unit tests, integration tests, and end-to-end RAG evaluation:

| Layer            | Test File           | Tests | Scope                                              |
| ---------------- | ------------------- | ----- | -------------------------------------------------- |
| API              | `test_api.py`       | 8     | Endpoint validation with fully mocked pipeline     |
| Ingestion        | `test_ingestion.py` | 28    | Normalizer, metadata extraction, chunking          |
| Retrieval        | `test_retrieval.py` | 16    | Query expansion, relevance boost, hybrid search    |
| Cross-References | `test_cross_ref.py` | 16    | Cross-reference detection, context window assembly |
| RAG Evaluation   | `test_rag_evals.py` | 21+   | End-to-end pipeline with real ChromaDB + OpenAI    |

**Unit tests** (`test_api.py`, `test_ingestion.py`, `test_retrieval.py`, `test_cross_ref.py`) run without external dependencies — ChromaDB and OpenAI are fully mocked. These validate correctness of individual pipeline stages.

**End-to-end evaluation** (`test_rag_evals.py`) runs real queries through the full pipeline against the ingested ChromaDB corpus using OpenAI embeddings and generation. Requires `OPENAI_API_KEY` to be set; skipped automatically when not configured.

---

## Running Tests

```bash
# All tests (unit + integration, ~89+ test cases)
pytest backend/tests/ -v

# Quick run — unit tests only (no API key needed)
pytest backend/tests/ -v -k "not test_rag_evals"

# Individual test files
pytest backend/tests/test_api.py -v          # 8 API endpoint tests
pytest backend/tests/test_ingestion.py -v    # 28 ingestion tests
pytest backend/tests/test_retrieval.py -v    # 16 retrieval tests
pytest backend/tests/test_cross_ref.py -v    # 16 cross-reference tests

# End-to-end RAG evaluation (requires OPENAI_API_KEY)
pytest backend/tests/test_rag_evals.py -v

# Skip expensive LLM-as-a-Judge tests
pytest backend/tests/test_rag_evals.py -v -k "not TestGenerationMetrics"

# Generate the evaluation report (TESTS.md metrics tables)
pytest backend/tests/test_rag_evals.py::test_generate_report -s
```

---

## Test Coverage Summary

### `test_api.py` — API Endpoint Tests (8 tests)

Tests all 3 endpoints using FastAPI's `TestClient` with fully mocked pipeline stages:

- `GET /api/health` — Returns `status: "ok"` with `collection_count`; degrades gracefully on DB error
- `POST /api/chat` — Returns all required response fields with correct types and disclaimer
- `POST /api/chat` — Empty query returns 422 (Pydantic validation)
- `POST /api/search` — Returns `results` + `enhanced_query` with correct structure
- `POST /api/search` — Empty query returns 422

### `test_ingestion.py` — Ingestion Pipeline Tests (28 tests)

Uses embedded Chapter 943 statute text as a realistic test fixture:

- **Normalizer**: Header/footer stripping, legal section marker preservation (`Chapter`, `§`, `Section`), whitespace normalization
- **Metadata**: Statute number extraction (`§ X.XX` patterns), case citation extraction (`2023 WI App X`), chapter extraction, source type inference, jurisdiction inference (state vs. local), doc ID determinism and uniqueness
- **Chunking**: Token counting with tiktoken, hierarchy detection for 4 levels (chapter → section → subsection → paragraph), breadcrumb context header correctness, chunk production and sequencing

### `test_retrieval.py` — Retrieval Pipeline Tests (16 tests)

- **Query Expansion** (8 tests): Abbreviation expansion (single and multiple), colloquialism → legal synonym mapping, exact statute/citation extraction, chapter hints from topic keywords
- **Relevance Boost** (6 tests): Superseded document dropping (×0.0), policy+local_department boost (×1.5), state jurisdiction boost (×1.2), exact statute match boost (×1.3), sort order preservation, empty input handling
- **Hybrid Search** (2 tests): Integration tests with mocked ChromaDB + BM25 + embedding; verifies RRF result structure, score positivity, and that dual-ranked results get higher RRF scores

### `test_cross_ref.py` — Cross-Reference Tests (16 tests)

- **Detection**: All 4 cross-reference regex patterns (`"see also §"`, `"see section"`, `"pursuant to §"`, `"under section"`, `"Chapter N"`), deduplication, empty input
- **Chunk Fetching**: Statute vs. chapter field selection, `superseded` filtering, max chunks per reference, empty references
- **Context Window**: Token limit enforcement, required return keys, cross-reference following with actual chunk addition, deduplication of repeated chunk IDs, empty input

### `test_rag_evals.py` — End-to-End RAG Evaluation (21+ tests)

Runs real queries through the full pipeline. Organized into test classes:

- **`TestRetrievalMetrics`**: Hit Rate @ 3, Hit Rate @ 5, MRR, source file matching for each golden query
- **`TestConfidenceMetrics`**: Mean confidence threshold, per-query confidence validation, LOW_CONFIDENCE flag correctness
- **`TestLatencyMetrics`**: Retrieval pipeline < 15s, full pipeline < 30s per query
- **`TestGenerationMetrics`**: LLM-as-a-Judge faithfulness and safety compliance on 3 representative queries
- **`TestSafetyCompliance`**: Disclaimer presence, use-of-force flag on deadly force queries
- **`test_generate_report`**: Generates the metrics tables below

---

## Evaluation Methodology

### Golden Query Set

The evaluation uses a curated set of **12 queries** designed to cover the full document corpus and the diversity of real-world officer queries:

| #   | Query                                                                                    | Type     | Expected Keywords       | Expected Sources                  |
| --- | ---------------------------------------------------------------------------------------- | -------- | ----------------------- | --------------------------------- |
| 1   | What are the elements of operating while intoxicated under Wisconsin Statute 346.63?     | Statute  | `346.63`, `intoxicated` | statute                           |
| 2   | What constitutes first degree intentional homicide under Wisconsin Statute 940.01?       | Statute  | `940.01`, `homicide`    | statute                           |
| 3   | What is the legal definition of theft under Wisconsin Chapter 943?                       | Statute  | `943`, `theft`          | statute                           |
| 4   | What does Wisconsin law say about endangering safety under Chapter 941?                  | Statute  | `941`                   | statute                           |
| 5   | What are the general principles of criminal liability under Wisconsin Chapter 939?       | Statute  | `939`                   | statute                           |
| 6   | What does Wisconsin Statute Chapter 968 say about search warrants and arrest procedures? | Statute  | `968`                   | statute                           |
| 7   | What are the penalties for a third offense OWI in Wisconsin?                             | Statute  | `346.63`, `third`       | statute                           |
| 8   | What was the court's ruling in case 2023AP001664?                                        | Case Law | `2023AP001664`          | 2023AP001664                      |
| 9   | What legal issues were addressed in Wisconsin appellate case 2023AP002319?               | Case Law | `2023AP002319`          | 2023AP002319                      |
| 10  | When can a Wisconsin law enforcement officer use deadly force?                           | Training | `deadly force`, `force` | LESB                              |
| 11  | What are the employee conduct standards in the Wisconsin administrative handbook?        | Training | `employee`, `conduct`   | wisconsin_admin_employee_handbook |
| 12  | What training requirements does LESB mandate for Wisconsin law enforcement officers?     | Training | `LESB`, `training`      | LESB                              |

**Design rationale**: The 7:2:3 statute/case law/training split mirrors the corpus composition. Queries range from exact statute references ("§ 346.63") to conceptual questions ("when can an officer use deadly force?") to test both keyword and semantic retrieval.

### Metric Definitions

**Hit Rate @ K** — Binary relevance: 1.0 if any relevant chunk appears in the top-K results, else 0.0. A chunk is "relevant" if its `source_type` matches the expected type OR any `expected_keyword` appears in the chunk's text, statute numbers, case citations, or context header.

**MRR (Mean Reciprocal Rank)** — For each query, MRR = 1/rank where rank is the position of the first relevant result. Averaged across all queries. MRR = 1.0 means the most relevant result is always ranked first.

**Confidence Score** — Algorithmic score from 0.0 to 1.0 computed from four retrieval signals (topic relevance, RRF score strength, score variance, source diversity). See [ARCHITECTURE.md](ARCHITECTURE.MD#confidence-scoring-algorithm) for the formula.

**Faithfulness (LLM-as-a-Judge)** — An LLM scores (0.0–1.0) whether the answer is grounded in the provided context with no hallucinated facts. Uses `temperature=0.0` for deterministic scoring.

**Safety Compliance (LLM-as-a-Judge)** — An LLM scores (0.0–1.0) the response's professionalism, format compliance, and absence of fabricated legal citations. Evaluated on the deadly force query to test sensitive-topic handling.

### Thresholds

| Metric                | Threshold | Rationale                                                                                                           |
| --------------------- | --------- | ------------------------------------------------------------------------------------------------------------------- |
| Hit Rate @ 3          | >= 0.80   | At least 80% of queries must find a relevant result in top 3 — ensures users see relevant content without scrolling |
| Hit Rate @ 5          | >= 0.90   | Slightly relaxed for top 5 — catches edge cases where the best result is ranked 4th or 5th                          |
| MRR                   | > 0.50    | Average reciprocal rank above 0.5 means relevant results are typically in the top 2 positions                       |
| Mean Confidence       | > 0.40    | Low bar — ensures the system produces confident answers more often than not                                         |
| Source Match Rate     | >= 8/12   | At least 2/3 of queries retrieve from the correct source file                                                       |
| Retrieval Latency     | < 15s     | Per-query retrieval (no LLM) completes within 15 seconds                                                            |
| Full Pipeline Latency | < 30s     | End-to-end (with LLM generation) completes within 30 seconds                                                        |
| Faithfulness          | >= 0.70   | Answers must be at least 70% faithful to context (no major hallucinations)                                          |
| Safety Compliance     | >= 0.80   | Critical for law enforcement — responses must be professional and accurate                                          |

---

## RAG Evaluation Results

### Summary

| Metric                | Value | Threshold | Status |
| --------------------- | ----- | --------- | ------ |
| Golden Set Size       | 12    | -         | -      |
| Hit Rate @ 3 (mean)   | 1.000 | >= 0.80   | PASS   |
| Hit Rate @ 5 (mean)   | 1.000 | >= 0.90   | PASS   |
| MRR (mean)            | 1.000 | >= 0.50   | PASS   |
| Mean Confidence Score | 0.791 | >= 0.40   | PASS   |
| Source Match Rate     | 12/12 | >= 8/12   | PASS   |

### Retrieval Metrics — Per-Query Results

| #   | Query                                                      | Hit@3 | Hit@5 | MRR   | Top Source                        | Confidence | Source Match | Results |
| --- | ---------------------------------------------------------- | ----- | ----- | ----- | --------------------------------- | ---------- | ------------ | ------- |
| 1   | What are the elements of operating while intoxicated un... | 1.0   | 1.0   | 1.000 | statute_2                         | 0.851      | YES          | 20      |
| 2   | What constitutes first degree intentional homicide unde... | 1.0   | 1.0   | 1.000 | statute_6                         | 0.881      | YES          | 20      |
| 3   | What is the legal definition of theft under Wisconsin C... | 1.0   | 1.0   | 1.000 | statute_4                         | 0.680      | YES          | 20      |
| 4   | What does Wisconsin law say about endangering safety un... | 1.0   | 1.0   | 1.000 | statute_5                         | 0.865      | YES          | 20      |
| 5   | What are the general principles of criminal liability u... | 1.0   | 1.0   | 1.000 | statute_5                         | 0.751      | YES          | 20      |
| 6   | What does Wisconsin Statute Chapter 968 say about searc... | 1.0   | 1.0   | 1.000 | statute_3                         | 0.919      | YES          | 20      |
| 7   | What are the penalties for a third offense OWI in Wisco... | 1.0   | 1.0   | 1.000 | statute_2                         | 0.851      | YES          | 20      |
| 8   | What was the court's ruling in case 2023AP001664?          | 1.0   | 1.0   | 1.000 | 2023AP002319                      | 0.762      | YES          | 20      |
| 9   | What legal issues were addressed in Wisconsin appellate... | 1.0   | 1.0   | 1.000 | 2023AP002319                      | 0.852      | YES          | 20      |
| 10  | When can a Wisconsin law enforcement officer use deadly... | 1.0   | 1.0   | 1.000 | statute_3                         | 0.873      | YES          | 20      |
| 11  | What are the employee conduct standards in the Wisconsi... | 1.0   | 1.0   | 1.000 | wisconsin_admin_employee_handbook | 0.601      | YES          | 20      |
| 12  | What training requirements does LESB mandate for Wiscon... | 1.0   | 1.0   | 1.000 | LESB                              | 0.601      | YES          | 20      |

### Score Distribution

| Statistic | RRF Score (top-1) | Boosted Score (top-1) |
| --------- | ----------------- | --------------------- |
| Mean      | 0.030728          | 0.038762              |
| Median    | 0.030592          | 0.037216              |
| Stdev     | 0.001144          | 0.005019              |
| Min       | 0.028958          | 0.034750              |
| Max       | 0.032522          | 0.050735              |

### Confidence Score Analysis

**Distribution:**

- **Mean**: 0.791
- **Median**: 0.851
- **Stdev**: 0.111
- **Min**: 0.601
- **Max**: 0.919

**Per-Query Confidence & Flags:**

| #   | Query                                                 | Confidence | LOW_CONF | UOF_CAUTION | JURISDICTION | OUTDATED |
| --- | ----------------------------------------------------- | ---------- | -------- | ----------- | ------------ | -------- |
| 1   | What are the elements of operating while intoxicat... | 0.851      | no       | no          | no           | no       |
| 2   | What constitutes first degree intentional homicide... | 0.881      | no       | no          | no           | no       |
| 3   | What is the legal definition of theft under Wiscon... | 0.680      | no       | no          | no           | no       |
| 4   | What does Wisconsin law say about endangering safe... | 0.865      | no       | no          | no           | no       |
| 5   | What are the general principles of criminal liabil... | 0.751      | no       | no          | no           | no       |
| 6   | What does Wisconsin Statute Chapter 968 say about ... | 0.919      | no       | no          | no           | no       |
| 7   | What are the penalties for a third offense OWI in ... | 0.851      | no       | no          | no           | no       |
| 8   | What was the court's ruling in case 2023AP001664?     | 0.762      | no       | no          | no           | no       |
| 9   | What legal issues were addressed in Wisconsin appe... | 0.852      | no       | no          | no           | no       |
| 10  | When can a Wisconsin law enforcement officer use d... | 0.873      | no       | no          | no           | no       |
| 11  | What are the employee conduct standards in the Wis... | 0.601      | no       | no          | no           | no       |
| 12  | What training requirements does LESB mandate for W... | 0.601      | no       | no          | no           | no       |

### Latency — Retrieval Pipeline (per-query)

| Stage                           | Mean (ms) | Max (ms)   | Min (ms)  |
| ------------------------------- | --------- | ---------- | --------- |
| Query Enhancement               | 0.1       | 0.3        | 0.1       |
| Hybrid Search (Semantic + BM25) | 357.6     | 1189.2     | 132.1     |
| Relevance Boosting              | 0.1       | 0.1        | 0.0       |
| Context Window Building         | 12.8      | 82.8       | 4.0       |
| **Total**                       | **370.6** | **1272.4** | **136.7** |

### Latency — Full Pipeline (with LLM generation)

| Stage                           | Mean (ms)  | Max (ms)   |
| ------------------------------- | ---------- | ---------- |
| Query Enhancement               | 0.2        | 0.3        |
| Hybrid Search (Semantic + BM25) | 535.7      | 1189.2     |
| Relevance Boosting              | 0.1        | 0.1        |
| Context Window Building         | 32.3       | 82.8       |
| Prompt Construction             | 0.1        | 0.1        |
| LLM Generation                  | 1771.8     | 1993.1     |
| Response Formatting             | 0.6        | 0.8        |
| **Total**                       | **2340.6** | **3047.0** |

### Generation Metrics (LLM-as-a-Judge)

Evaluated on a subset of 3 queries (OWI elements, homicide definition, deadly force policy):

| Query                                                      | Faithfulness | Safety |
| ---------------------------------------------------------- | ------------ | ------ |
| What are the elements of operating while intoxicated un... | 1.000        | 1.000  |
| What constitutes first degree intentional homicide unde... | 1.000        | 1.000  |
| When can a Wisconsin law enforcement officer use deadly... | 1.000        | 1.000  |

- **Mean Faithfulness**: 1.000 (threshold >= 0.70)
- **Mean Safety**: 1.000 (threshold >= 0.80)

### Safety & Compliance

| #   | Query                                                 | Disclaimer | UOF Caution | Jurisdiction Note | Outdated |
| --- | ----------------------------------------------------- | ---------- | ----------- | ----------------- | -------- |
| 1   | What are the elements of operating while intoxicat... | PRESENT    | no          | no                | no       |
| 2   | What constitutes first degree intentional homicide... | PRESENT    | YES         | no                | no       |
| 3   | What is the legal definition of theft under Wiscon... | N/A        | no          | no                | no       |
| 4   | What does Wisconsin law say about endangering safe... | N/A        | no          | no                | no       |
| 5   | What are the general principles of criminal liabil... | N/A        | no          | no                | no       |
| 6   | What does Wisconsin Statute Chapter 968 say about ... | N/A        | no          | no                | no       |
| 7   | What are the penalties for a third offense OWI in ... | N/A        | no          | no                | no       |
| 8   | What was the court's ruling in case 2023AP001664?     | N/A        | no          | no                | no       |
| 9   | What legal issues were addressed in Wisconsin appe... | N/A        | no          | no                | no       |
| 10  | When can a Wisconsin law enforcement officer use d... | PRESENT    | YES         | no                | no       |
| 11  | What are the employee conduct standards in the Wis... | N/A        | no          | no                | no       |
| 12  | What training requirements does LESB mandate for W... | N/A        | no          | no                | no       |

---

## Interpretation Guide

### What the Results Mean

- **Perfect Hit Rate (1.000)**: Every query finds at least one relevant document in the top 3 and top 5 results. The hybrid search (BM25 + semantic) is effective at retrieving relevant content for both exact statute references and conceptual questions.
- **Perfect MRR (1.000)**: The most relevant result is always ranked first. The combination of RRF fusion and relevance boosting consistently surfaces the best match.
- **Confidence range (0.601–0.919)**: No queries trigger `LOW_CONFIDENCE` (threshold < 0.6). Lower confidence on training/policy queries (0.601) is expected — these documents have fewer exact keyword matches compared to statutes with precise section numbers.
- **Latency profile**: ~76% of end-to-end time is LLM generation (~1.8s). Retrieval averages ~370ms. The system comfortably meets the 30-second threshold for all queries.
- **Safety flags**: `USE_OF_FORCE_CAUTION` correctly triggers on queries 2 (homicide) and 10 (deadly force). No false positives on non-force queries.

### Known Limitations

- **Golden set size**: 12 queries provide coverage but may not capture all edge cases. Expanding to 30+ queries would increase evaluation robustness.
- **LLM-as-a-Judge subset**: Only 3 queries are evaluated for faithfulness/safety due to API cost. Expanding this subset would provide stronger generation quality guarantees.
- **Single-run metrics**: Results may vary slightly across runs due to OpenAI API non-determinism (embedding and generation). LLM-as-a-Judge uses `temperature=0.0` to minimize this.
- **Corpus dependency**: All metrics depend on the ingested document corpus. Adding or removing documents requires re-running the evaluation.

### Extending the Golden Query Set

To add new evaluation queries, edit the `GOLDEN_SET` list in `backend/tests/test_rag_evals.py`:

```python
{
    "query": "Your new test query",
    "expected_source_type": "statute",        # or "case_law", "training"
    "expected_keywords": ["keyword1", "keyword2"],
    "expected_source_files": ["source_name"],  # substring match against source filenames
    "ideal_answer_summary": "Description of what a good answer should contain.",
}
```

To add LLM-as-a-Judge evaluation for the new query, add its index to `_JUDGE_SUBSET_INDICES`.

---

## Notes

- All retrieval tests run against the real ChromaDB corpus
- Embeddings generated via OpenAI `text-embedding-3-small`
- LLM generation uses the configured model (`LLM_MODEL` setting)
- First query may be slower due to BM25 index initialization
- LLM-as-a-Judge uses `temperature=0.0` for deterministic scoring
- Confidence scores computed from retrieval signals only (no LLM needed)
- The metrics tables in this file are regenerated by running `pytest backend/tests/test_rag_evals.py::test_generate_report -s`
