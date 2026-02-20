from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # API Keys
    OPENAI_API_KEY: str = ""

    # LLM Settings
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_TEMPERATURE: float = 0.3
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Data Source
    RAW_DATA_DIR: str = "./data"

    # ChromaDB
    CHROMA_DB_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "wisconsin_legal_corpus"

    # Ingestion
    EMBEDDING_BATCH_SIZE: int = 100
    CHUNK_TARGET_TOKENS: int = 1000
    CHUNK_OVERLAP_FRACTION: float = 0.15

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
