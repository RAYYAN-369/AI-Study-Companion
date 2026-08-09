"""
Centralized configuration loaded from environment variables.

Single source of truth for the whole backend. Every service (upload, parser,
chunking, embeddings, qdrant, retrieval, llm) imports `settings` from here
instead of calling os.environ directly or hard-coding values.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- LLM API key (Groq) ---
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # --- Qdrant ---
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "study_companion")

    # --- Embedding model ---
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))

    # --- Backend server ---
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # --- Uploads ---
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "backend/uploads")
    ALLOWED_EXTENSIONS = {"pdf", "txt", "docx"}
    # Single source of truth for the max upload size. The frontend
    # (files/config.js) mirrors this value — keep them in sync.
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024

    # --- Chunking ---
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))

    # --- CORS (dev-friendly defaults; override in production) ---
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000,null",
    ).split(",")


settings = Settings()
