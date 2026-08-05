"""
Retrieval service (Member 3).

Given a user's topic/query, embeds it and searches Qdrant for the most
relevant stored chunks, then hands that context to llm_service.py.
"""

from typing import Dict, List

from backend.config import settings
from backend.services.embeddings import embed_query
from backend.services.qdrant_service import get_client


def retrieve_relevant_chunks(
    query: str,
    top_k: int = 5,
    collection_name: str = None,
) -> List[Dict]:
    """
    Search Qdrant for chunks most relevant to `query`.

    Returns a list of dicts: [{"text": ..., "score": ..., **metadata}, ...]
    ordered by relevance (highest score first).
    """
    collection_name = collection_name or settings.QDRANT_COLLECTION
    client = get_client()
    query_vector = embed_query(query)

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k,
    )

    return [
        {"text": hit.payload.get("text", ""), "score": hit.score, **hit.payload}
        for hit in results.points
    ]


def build_context_string(chunks: List[Dict]) -> str:
    """
    Flatten retrieved chunks into a single context block to feed the LLM
    prompt.
    """
    return "\n\n---\n\n".join(chunk["text"] for chunk in chunks)