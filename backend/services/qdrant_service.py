"""
Qdrant integration service (Member 3).

Owns: connecting to Qdrant, creating the collection, ensuring the
`document_id` payload index exists, and storing embeddings with their
source text + metadata as payload.
"""

import logging
import uuid
from functools import lru_cache
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from backend.config import settings

logger = logging.getLogger(__name__)

# The field we filter retrieval on (backend/services/retrieval.py ->
# build_document_filter). Qdrant requires an explicit payload index before
# a field can be used in a query filter -- without it, query_points raises
# a 400 "Index required but not found" UnexpectedResponse.
DOCUMENT_ID_FIELD = "document_id"


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    """Single shared Qdrant client for the app's lifetime."""
    return QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)


def ensure_collection(collection_name: str = None) -> None:
    """
    Create the Qdrant collection if it doesn't already exist, and make sure
    the document_id payload index exists either way. Safe to call on every
    app startup / every upload -- it's a no-op if the collection and index
    are already there.

    This does NOT delete or recreate an existing collection. It only adds
    what's missing.
    """
    collection_name = collection_name or settings.QDRANT_COLLECTION
    client = get_client()

    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )

    # Whether the collection was just created or already existed (e.g. an
    # older collection created before this fix), make sure the index that
    # document-scoped retrieval depends on is present.
    _ensure_document_id_index(client, collection_name)


def _ensure_document_id_index(client: QdrantClient, collection_name: str) -> None:
    """
    Idempotently ensure a KEYWORD payload index exists on `document_id` for
    the given collection. document_id is generated as a UUID4 string
    (see backend/app/api/upload.py: str(uuid.uuid4())) and stored/queried
    as a plain string throughout, so KEYWORD is the correct, consistent
    schema end-to-end.

    Qdrant's create_payload_index is safe to call repeatedly -- calling it
    again for a field/schema that's already indexed does not error or
    duplicate the index. We still guard with try/except so a transient
    "already exists"-style response (older server versions) never crashes
    startup or an upload.
    """
    try:
        info = client.get_collection(collection_name)
        payload_schema = getattr(info, "payload_schema", None) or {}
        if DOCUMENT_ID_FIELD in payload_schema:
            return
    except Exception as exc:  # pragma: no cover - purely a best-effort skip check
        logger.debug("Could not inspect existing payload schema, will attempt index creation: %s", exc)

    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name=DOCUMENT_ID_FIELD,
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("Ensured payload index on '%s' for collection '%s'.", DOCUMENT_ID_FIELD, collection_name)
    except UnexpectedResponse as exc:
        if "already exists" in str(exc).lower():
            logger.debug("Payload index on '%s' already exists for '%s'.", DOCUMENT_ID_FIELD, collection_name)
        else:
            raise


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


def build_document_filter(document_id: Optional[str]) -> Optional[Filter]:
    """
    Build a Qdrant filter that restricts a search to points belonging to a
    single uploaded document (identified by the `document_id` stored in each
    point's payload). Returns None if no document_id is given, meaning
    "search everything" — used for local dev/testing only.

    This is what keeps a query for one uploaded document from accidentally
    retrieving chunks from a different document in the same collection: the
    app is single-collection, multi-document, and NOT strongly
    session-isolated (no auth) — see README for the honest caveat.

    Requires a payload index on document_id (see _ensure_document_id_index),
    which ensure_collection() guarantees before this filter is ever used.
    """
    if not document_id:
        return None
    return Filter(
        must=[FieldCondition(key=DOCUMENT_ID_FIELD, match=MatchValue(value=document_id))]
    )