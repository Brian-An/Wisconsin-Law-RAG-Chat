# Wisconsin Law Enforcement RAG System

A Retrieval-Augmented Generation (RAG) application that enables Wisconsin law enforcement officers to query state statutes, case law, and department policies through a conversational chat interface.

Video Demo: [Here](https://youtu.be/1F9aKxEJcyU)

---

## Table of Contents

- [How It Works](#how-it-works)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Configure Environment Variables](#2-configure-environment-variables)
  - [3. Install Backend Dependencies](#3-install-backend-dependencies)
  - [4. Install Frontend Dependencies](#4-install-frontend-dependencies)
  - [5. Ingest Legal Documents](#5-ingest-legal-documents)
  - [6. Start the Backend Server](#6-start-the-backend-server)
  - [7. Start the Frontend Dev Server](#7-start-the-frontend-dev-server)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Running Tests](#running-tests)
- [Configuration Reference](#configuration-reference)
- [Key Metrics](#key-metrics)
- [Security](#security)
- [Documentation](#documentation)

---

## How It Works

1. **You ask a question** — Type a legal question or select a quick action (Miranda Rights, OWI Laws, Terry Stop, Use of Force).
2. **Query expansion** — The system expands law enforcement abbreviations (e.g., "OWI" → "Operating While Intoxicated") and maps informal terms to their legal equivalents.
3. **Hybrid retrieval** — Two search strategies run in parallel: keyword matching (BM25) finds exact statute references, while semantic search finds conceptually related passages. Results are fused via Reciprocal Rank Fusion.
4. **Context assembly** — Top-ranked chunks are assembled within a token budget, automatically following cross-references ("see also § 940.01") to pull in cited statutes.
5. **Answer generation** — An LLM generates a prose answer grounded in the retrieved context, with confidence scoring, safety flags, citation cards, and a mandatory legal disclaimer.

For the full technical architecture, pipeline diagrams, and design rationale, see [ARCHITECTURE.md](ARCHITECTURE.MD).

---

## Features

- **Hybrid Search** — Combines BM25 keyword search with semantic vector search via Reciprocal Rank Fusion for accurate statute number matching and conceptual query understanding.
- **Document-Type-Aware Chunking** — Separate hierarchy detection for statutes (Chapter → Section → Subsection), case law (Opinion → Section → ¶), and training documents (Header → Section → Item).
- **Cross-Reference Following** — Automatically follows citation chains ("see also §", "pursuant to §") within a token-budgeted context window.
- **Safety Guardrails** — Flags use-of-force queries with department-policy caveats, detects outdated sources, and notes jurisdiction mismatches. Mandatory legal disclaimer on every response.
- **Confidence Scoring** — Algorithmic 0.0–1.0 confidence score based on retrieval quality signals (topic relevance, RRF score strength, score variance, source diversity) — no extra LLM call required.
- **Query Expansion** — Expands 35 law enforcement abbreviations (OWI, OMVWI, DV, etc.) and maps 34 colloquial terms to their legal equivalents.
- **Responsive Chat UI** — Three-column layout with conversation sidebar, message stream with citation cards and confidence badges, and a source detail panel. Dark theme by default.

---

## Tech Stack

| Layer                | Technology                                         | Purpose                                        |
| -------------------- | -------------------------------------------------- | ---------------------------------------------- |
| **Backend**          | FastAPI, Python 3.11+                              | Async API server                               |
| **Vector Store**     | ChromaDB (persistent, cosine distance)             | Document embedding storage and semantic search |
| **LLM / Embeddings** | OpenAI (`gpt-3.5-turbo`, `text-embedding-3-small`) | Response generation and document embedding     |
| **Keyword Search**   | rank-bm25                                          | BM25Okapi keyword ranking                      |
| **PDF Parsing**      | pdfplumber, python-docx, BeautifulSoup             | Multi-format document ingestion                |
| **Token Counting**   | tiktoken (`cl100k_base`)                           | Chunk sizing and context budget management     |
| **Frontend**         | Next.js 16, React 19, TypeScript 5                 | Chat interface                                 |
| **Styling**          | Tailwind CSS v4                                    | Responsive dark/light theming                  |
| **State Management** | Zustand                                            | Client-side conversation and UI state          |
| **Testing**          | pytest                                             | Unit, integration, and RAG evaluation tests    |

---

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Settings via pydantic_settings (.env)
│   ├── api/
│   │   ├── routes.py            # /api/chat, /api/search, /api/health
│   │   ├── models.py            # Pydantic request/response models
│   │   └── middleware.py        # CORS, request logging
│   ├── ingestion/
│   │   ├── ingest.py            # Ingestion orchestrator + CLI
│   │   ├── parser.py            # PDF/DOCX/HTML parsing
│   │   ├── chunking.py          # Document-type-aware hierarchical chunking
│   │   ├── metadata.py          # Legal metadata extraction (statutes, citations)
│   │   └── normalizer.py        # Header/footer stripping, whitespace normalization
│   ├── retrieval/
│   │   ├── hybrid_search.py     # BM25 + semantic search with RRF fusion
│   │   ├── query_expand.py      # Abbreviation expansion, synonym mapping
│   │   ├── relevnace_boost.py   # Score multipliers (jurisdiction, source type)
│   │   ├── cross_ref.py         # Citation chain detection
│   │   └── context.py           # Token-budgeted context window assembly
│   ├── generation/
│   │   ├── llm.py               # OpenAI client (singleton)
│   │   ├── prompt.py            # System + user prompt construction
│   │   ├── formatter.py         # Confidence scoring, response assembly
│   │   └── safety.py            # Use-of-force, outdated, jurisdiction checks
│   ├── utils/
│   │   ├── abbreviations.py     # 35 law enforcement abbreviation mappings
│   │   └── legal_terms.py       # 34 colloquial-to-legal term mappings
│   └── tests/                   # 174 test cases (see TESTS.md)
├── data/
│   ├── statute/                 # Wisconsin statute PDFs
│   ├── case_law/                # Case law PDFs
│   └── training/                # Training/policy documents (LESB, handbook)
├── chroma_db/                   # ChromaDB persistent storage (auto-generated)
├── frontend/
│   └── src/
│       ├── app/                 # Next.js App Router (layout, page, globals.css)
│       ├── components/          # Chat, input, layout, common UI components
│       ├── hooks/               # useChat, useHealth, useMediaQuery, useScrollToBottom
│       ├── lib/                 # API client, types, utilities, constants
│       └── store/               # Zustand stores (chatStore, uiStore)
├── ARCHITECTURE.MD              # System architecture documentation
├── TESTS.MD                     # Testing methodology and metrics
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment variable template
```

---

## Prerequisites

- **Python 3.11+** — Backend runtime
- **Node.js 18+** and **npm** — Frontend toolchain
- **OpenAI API Key** — Required for embeddings and LLM generation

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Brian-An/Wisconsin-Law-RAG-Chat.git
cd code-four-takehome
```

### 2. Configure Environment Variables

Copy the example file and add your OpenAI API key:

```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder:

```dotenv
# Required
OPENAI_API_KEY=sk-your-actual-api-key-here

# Optional — defaults shown
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.3
EMBEDDING_MODEL=text-embedding-3-small
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000"]
```

### 3. Install Backend Dependencies

Create a virtual environment (recommended) and install packages:

```bash
python -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Ingest Legal Documents

Place your legal documents in the appropriate `data/` subdirectories:

| Directory        | Document Type             | Examples                                            |
| ---------------- | ------------------------- | --------------------------------------------------- |
| `data/statute/`  | Wisconsin statute PDFs    | `statue_1.pdf` through `statue_5.pdf`               |
| `data/case_law/` | Case law PDFs             | `2023AP001664.pdf`, etc.                            |
| `data/training/` | Training/policy documents | `LESB.pdf`, `wisconsin_admin_employee_handbook.pdf` |

Run the ingestion pipeline to parse, chunk, embed, and store documents in ChromaDB:

```bash
python -m backend.ingestion.ingest
```

This will:

1. Parse all PDF/DOCX/HTML files from `data/`
2. Normalize text (strip headers/footers, collapse whitespace)
3. Chunk by document type with hierarchical context headers
4. Extract metadata (statute numbers, case citations, jurisdiction)
5. Generate embeddings via OpenAI and upsert to ChromaDB

The vector store persists to `chroma_db/` — you only need to run this once unless documents change.

### 6. Start the Backend Server

From the **repository root** (not inside `backend/`):

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. You can verify with:

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{
  "status": "ok",
  "document_count": <number_of_indexed_chunks>
}
```

### 7. Start the Frontend Dev Server

In a separate terminal:

```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## Usage

### Chat Interface

1. Open the app at `http://localhost:3000`
2. Type a legal question in the chat input or select a **quick action** (Miranda Rights, OWI Laws, Terry Stop, Use of Force)
3. The system will retrieve relevant legal sources, generate a response with citations, and display:
   - The answer with a **confidence badge** (High / Medium / Low)
   - **Citation cards** showing source documents with relevance scores
   - **Safety flag banners** when applicable (use-of-force caution, outdated sources, jurisdiction notes)
   - A mandatory **legal disclaimer**
4. Click any citation card to expand the **source panel** with full document details
5. Use the **sidebar** to manage conversation history (grouped by date, persisted to localStorage)

## API Endpoints

| Method | Endpoint      | Description                                                                |
| ------ | ------------- | -------------------------------------------------------------------------- |
| `POST` | `/api/chat`   | Full RAG pipeline — returns answer, sources, confidence, flags, disclaimer |
| `POST` | `/api/search` | Retrieval only (no LLM) — returns ranked chunks for debugging              |
| `GET`  | `/api/health` | ChromaDB connectivity check and document count                             |

### POST `/api/chat`

**Request:**

```json
{
  "query": "What constitutes first degree homicide in Wisconsin?",
  "session_id": "optional-uuid"
}
```

**Response:**

```json
{
  "answer": "Under Wisconsin Statute § 940.01, first degree intentional homicide...",
  "sources": [
    {
      "title": "statue_1",
      "source_file": "data/statues/statue_1.pdf",
      "source_type": "statute",
      "context_header": "Chapter 940 > § 940.01",
      "statute_numbers": "940.01",
      "confidence_score": 0.038
    }
  ],
  "confidence_score": 0.87,
  "flags": {
    "LOW_CONFIDENCE": false,
    "OUTDATED_POSSIBLE": false,
    "JURISDICTION_NOTE": false,
    "USE_OF_FORCE_CAUTION": false
  },
  "disclaimer": "This system provides legal information, not formal legal advice. Always verify with current statutes."
}
```

### POST `/api/search`

**Request:**

```json
{
  "query": "§ 346.63 OWI",
  "top_k": 5
}
```

**Response:**

```json
{
  "results": [
    {
      "id": "abc123...",
      "document": "Chunk text...",
      "metadata": { "source_type": "statute", "statute_numbers": "346.63", ... },
      "rrf_score": 0.032,
      "boosted_score": 0.038
    }
  ]
}
```

---

## Running Tests

```bash
# All tests (174 test cases)
pytest backend/tests/ -v

# Quick run — unit tests only (no API key needed)
pytest backend/tests/ -v -k "not test_rag_evals"

# Individual test files
pytest backend/tests/test_api.py -v          # 9 API tests
pytest backend/tests/test_ingestion.py -v    # 35 ingestion tests
pytest backend/tests/test_retrieval.py -v    # 16 retrieval tests
pytest backend/tests/test_cross_ref.py -v    # 16 cross-reference tests
pytest backend/tests/test_rag_evals.py -v    # 98 RAG evaluation tests
```

See [TESTS.md](TESTS.md) for detailed documentation on metrics, thresholds, and the golden query set.

---

## Configuration Reference

All settings are managed via environment variables loaded from `.env` through `pydantic_settings.BaseSettings`.

| Variable                 | Default                     | Description                                                |
| ------------------------ | --------------------------- | ---------------------------------------------------------- |
| `OPENAI_API_KEY`         | _(required)_                | OpenAI API key for embeddings and generation               |
| `LLM_MODEL`              | `gpt-3.5-turbo`             | Chat completion model                                      |
| `LLM_TEMPERATURE`        | `0.3`                       | LLM response temperature (0 = deterministic, 1 = creative) |
| `EMBEDDING_MODEL`        | `text-embedding-3-small`    | Embedding model for document and query vectors             |
| `API_HOST`               | `0.0.0.0`                   | Backend server bind address                                |
| `API_PORT`               | `8000`                      | Backend server port                                        |
| `CORS_ORIGINS`           | `["http://localhost:3000"]` | Allowed CORS origins (JSON array)                          |
| `RAW_DATA_DIR`           | `./data`                    | Root directory for legal documents                         |
| `CHROMA_DB_DIR`          | `./chroma_db`               | ChromaDB persistent storage directory                      |
| `CHROMA_COLLECTION_NAME` | `wisconsin_legal_corpus`    | ChromaDB collection name                                   |
| `EMBEDDING_BATCH_SIZE`   | `100`                       | Documents per embedding API batch                          |
| `CHUNK_TARGET_TOKENS`    | `1000`                      | Target tokens per chunk                                    |
| `CHUNK_OVERLAP_FRACTION` | `0.15`                      | Overlap between adjacent chunks (0.0–1.0)                  |

---

## Key Metrics

Evaluated against a golden query set of 12 representative queries spanning statutes, case law, and training documents. Full methodology and per-query breakdowns in [TESTS.md](TESTS.MD).

| Metric                           | Value    | Threshold   |
| -------------------------------- | -------- | ----------- |
| Hit Rate @ 3                     | 1.000    | >= 0.80     |
| Hit Rate @ 5                     | 1.000    | >= 0.90     |
| Mean Reciprocal Rank             | 1.000    | >= 0.50     |
| Mean Confidence Score            | 0.791    | >= 0.40     |
| Source Match Rate                | 12/12    | >= 8/12     |
| Mean Retrieval Latency           | 521 ms   | < 15 000 ms |
| Mean End-to-End Latency          | 2 559 ms | < 30 000 ms |
| Faithfulness (LLM-as-Judge)      | 1.000    | >= 0.70     |
| Safety Compliance (LLM-as-Judge) | 1.000    | >= 0.80     |

---

## Security

The system is designed for deployment on internal law enforcement networks. Key measures:

- **Input validation** — Query length enforced at 1–2 000 characters via Pydantic. All request/response models use strict typing.
- **CORS restrictions** — Only configured frontend origins can call the API (default: `http://localhost:3000`).
- **No PII logging** — Request logging captures method, path, status, and timing only. Query content and response bodies are never written to logs.
- **LLM guardrails** — System prompt prohibits fabrication of statutes or citations. Use-of-force queries trigger safety flags. Outdated sources and jurisdiction mismatches are flagged automatically.
- **Mandatory disclaimer** — Every response includes: _"This system provides legal information, not formal legal advice. Always verify with current statutes."_
- **Local data storage** — All documents and vector embeddings stay on the local filesystem. Only query text and context chunks are sent to the OpenAI API.
- **API key protection** — `OPENAI_API_KEY` loaded from `.env` (git-ignored), never hardcoded or logged.

For full security architecture, see [ARCHITECTURE.md](ARCHITECTURE.MD#security-and-privacy-measures).

---

## Documentation

| Document                           | Description                                                                                                                                       |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| [ARCHITECTURE.md](ARCHITECTURE.MD) | System architecture with RAG pipeline diagrams, design decisions, scalability considerations, and security measures                               |
| [TESTS.md](TESTS.MD)               | Testing methodology, retrieval accuracy metrics (HR@K, MRR), response time benchmarks, relevance scoring evaluation, and golden query set results |
