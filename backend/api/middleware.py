"""CORS and logging middleware for the FastAPI application."""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings

logger = logging.getLogger(__name__)


def setup_cors(app: FastAPI) -> None:
    """Add CORS middleware using origins from settings."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


async def logging_middleware(request: Request, call_next):
    """Log request method, path, and response time."""
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {elapsed:.3f}s")
    return response


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""
    setup_cors(app)
    app.middleware("http")(logging_middleware)
