"""Ingestion pipeline orchestrator.

Coordinates the full pipeline: parse → normalize → chunk → extract metadata
→ embed → upsert into ChromaDB. Can be run as a standalone script.

Usage:
    python -m backend.ingestion.ingest [data_dir]
"""

import logging
import time
from typing import Optional

import chromadb

from backend.config import settings
from backend.generation.llm import get_openai_client
from backend.ingestion.chunking import Chunk, chunk_document
from backend.ingestion.metadata import extract_metadata
from backend.ingestion.normalizer import normalize_text
from backend.ingestion.parser import ParsedDocument, parse_directory

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ChromaDB helpers
# ---------------------------------------------------------------------------

def get_chroma_client() -> chromadb.ClientAPI:
    """Create a persistent ChromaDB client at the configured directory."""
    logger.info(f"Initializing ChromaDB at {settings.CHROMA_DB_DIR}")
    return chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)


def get_or_create_collection(client: chromadb.ClientAPI) -> chromadb.Collection:
    """Get or create the legal corpus collection with cosine distance."""
    collection = client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(
        f"Collection '{settings.CHROMA_COLLECTION_NAME}' ready "
        f"(existing count: {collection.count()})"
    )
    return collection


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings via the OpenAI API using the configured model.

    Uses the existing singleton OpenAI client from llm.py.
    """
    client = get_openai_client()
    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


# ---------------------------------------------------------------------------
# Batch upsert
# ---------------------------------------------------------------------------

def batch_upsert(
    collection: chromadb.Collection,
    chunks: list[Chunk],
    metadata_list: list[dict],
) -> None:
    """Embed and upsert chunks into ChromaDB in batches.

    Each chunk's embedding text is its context header + content,
    so semantic search benefits from the hierarchical context.
    """
    batch_size = settings.EMBEDDING_BATCH_SIZE
    total_batches = (len(chunks) + batch_size - 1) // batch_size

    for batch_num in range(total_batches):
        start = batch_num * batch_size
        end = min(start + batch_size, len(chunks))

        batch_chunks = chunks[start:end]
        batch_meta = metadata_list[start:end]

        # Build embedding text: context header + chunk content
        embedding_texts = [
            f"{c.context_header}\n\n{c.text}" if c.context_header else c.text
            for c in batch_chunks
        ]

        ids = [m["doc_id"] for m in batch_meta]

        try:
            embeddings = generate_embeddings(embedding_texts)

            collection.upsert(
                ids=ids,
                documents=embedding_texts,
                embeddings=embeddings,
                metadatas=batch_meta,
            )

            logger.info(
                f"  Upserted batch {batch_num + 1}/{total_batches} "
                f"({len(batch_chunks)} chunks)"
            )
        except Exception as e:
            logger.error(
                f"  Failed to upsert batch {batch_num + 1}/{total_batches}: {e}"
            )
            raise


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

def run_ingestion(data_dir: Optional[str] = None) -> dict:
    """Run the full ingestion pipeline end-to-end.

    Args:
        data_dir: Path to the data directory. Defaults to settings.RAW_DATA_DIR.

    Returns:
        Summary dict with counts of documents parsed, chunks created, etc.
    """
    data_dir = data_dir or settings.RAW_DATA_DIR
    start_time = time.time()

    # Step 1: Parse all documents
    logger.info(f"Step 1/4: Parsing documents from {data_dir}")
    documents = parse_directory(data_dir)
    if not documents:
        logger.warning("No documents found. Aborting ingestion.")
        return {"documents_parsed": 0, "total_chunks": 0}

    # Step 2: Normalize, chunk, and extract metadata
    logger.info("Step 2/4: Normalizing, chunking, and extracting metadata")
    all_chunks: list[Chunk] = []
    all_metadata: list[dict] = []

    for doc in documents:
        logger.info(f"Processing: {doc.file_name}")

        # Normalize
        normalized = normalize_text(doc.full_text)

        # Chunk
        chunks = chunk_document(doc, normalized)

        # Extract metadata for each chunk
        for chunk in chunks:
            meta = extract_metadata(chunk, doc)
            all_chunks.append(chunk)
            all_metadata.append(meta)

    logger.info(f"Total chunks created: {len(all_chunks)}")

    # Step 3: Initialize ChromaDB
    logger.info("Step 3/4: Initializing ChromaDB")
    chroma_client = get_chroma_client()
    collection = get_or_create_collection(chroma_client)

    # Step 4: Embed and upsert
    logger.info(f"Step 4/4: Embedding and upserting {len(all_chunks)} chunks")
    batch_upsert(collection, all_chunks, all_metadata)

    elapsed = time.time() - start_time
    final_count = collection.count()

    summary = {
        "documents_parsed": len(documents),
        "total_chunks": len(all_chunks),
        "collection_name": settings.CHROMA_COLLECTION_NAME,
        "chroma_db_dir": settings.CHROMA_DB_DIR,
        "collection_total": final_count,
        "elapsed_seconds": round(elapsed, 2),
    }

    logger.info(f"Ingestion complete: {summary}")
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    summary = run_ingestion(data_dir)

    print("\n=== Ingestion Complete ===")
    for key, value in summary.items():
        print(f"  {key}: {value}")
