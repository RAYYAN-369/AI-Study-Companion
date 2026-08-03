"""
Qdrant integration service (Member 3).

Owns: connecting to Qdrant, creating the collection, and storing embeddings
with their source text + metadata as payload.
"""

import uuid
from functools import lru_cache
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from backend.config import settings


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    """Single shared Qdrant client for the app's lifetime."""
    return QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)


def ensure_collection(collection_name: str = None) -> None:
    """
    Create the Qdrant collection if it doesn't already exist. Safe to call
    on every app startup — it's a no-op if the collection is already there.
    """
    collection_name = collection_name or settings.QDRANT_COLLECTION
    client = get_client()

    existing = [c.name for c in client.get_collections().collections]
    if collection_name in existing:
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=settings.EMBEDDING_DIM,
            distance=Distance.COSINE,
        ),
    )


def store_embeddings(
    chunks: List[str],
    vectors: List[List[float]],
    metadata: Optional[List[Dict]] = None,
    collection_name: str = None,
) -> List[str]:
    """
    Upsert chunk vectors into Qdrant, storing the original chunk text (and
    any per-chunk metadata) as the payload so retrieval.py can return
    readable context, not just vectors.

    Returns the list of point IDs that were written.
    """
    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors must be the same length")

    collection_name = collection_name or settings.QDRANT_COLLECTION
    metadata = metadata or [{} for _ in chunks]
    client = get_client()

    point_ids = [str(uuid.uuid4()) for _ in chunks]
    points = [
        PointStruct(
            id=point_ids[i],
            vector=vectors[i],
            payload={"text": chunks[i], **metadata[i]},
        )
        for i in range(len(chunks))
    ]

    client.upsert(collection_name=collection_name, points=points)
    return point_ids