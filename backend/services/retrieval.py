"""
Retrieval service.

Given a user's topic/query, embeds it and searches Qdrant for the most
relevant stored chunks, then hands that context to llm_service.py.
"""

from typing import Dict, List, Optional

from backend.config import settings
from backend.services.embeddings import embed_query
from backend.services.qdrant_service import build_document_filter, get_client


def retrieve_relevant_chunks(
    query: str,
    top_k: int = 5,
    collection_name: str = None,
    document_id: Optional[str] = None,
) -> List[Dict]:
    """
    Search Qdrant for chunks most relevant to `query`.

    If `document_id` is given, results are restricted to chunks belonging to
    that document -- this is what prevents a query about one uploaded file
    from pulling in unrelated chunks from a different upload stored in the
    same collection.

    Returns a list of dicts: [{"text": ..., "score": ..., **metadata}, ...]
    ordered by relevance (highest score first).
    """
    collection_name = collection_name or settings.QDRANT_COLLECTION
    client = get_client()
    query_vector = embed_query(query)
    query_filter = build_document_filter(document_id)

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
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
