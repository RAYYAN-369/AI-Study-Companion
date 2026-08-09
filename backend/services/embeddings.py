"""
Embedding generation service (Member 3).

Takes text chunks (produced by Member 2's chunking.py) and turns them into
vectors for storage in Qdrant. Uses a local sentence-transformers model, so
this doesn't need an API key or network call at inference time.
"""

from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

from backend.config import settings


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """
    Load the embedding model once and cache it. Loading is slow (model
    download + init), so this must not run on every request.
    """
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a batch of text chunks. Expects the output of Member 2's chunking
    step: a list of plain strings (one per chunk).

    Returns a list of vectors, same order and length as `texts`.
    """
    if not texts:
        return []

    model = _get_model()
    vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(text: str) -> List[float]:
    """
    Embed a single query string (e.g. a topic the user typed in) for
    similarity search against Qdrant.
    """
    return embed_texts([text])[0]