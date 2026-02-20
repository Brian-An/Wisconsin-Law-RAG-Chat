"""FastAPI application entry point.

Start with:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging

from fastapi import FastAPI

from backend.api.middleware import setup_middleware
from backend.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Wisconsin Law Enforcement RAG",
    description=(
        "Retrieval-Augmented Generation system for Wisconsin law enforcement "
        "statutes, case law, and policies."
    ),
    version="1.0.0",
)

setup_middleware(app)
app.include_router(router, prefix="/api")
