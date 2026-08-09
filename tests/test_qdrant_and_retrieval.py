"""
Unit tests for qdrant_service / retrieval.py logic that doesn't require a
live Qdrant instance -- the actual client calls are mocked.
"""

from unittest.mock import MagicMock, patch

from backend.services.qdrant_service import (
    DOCUMENT_ID_FIELD,
    build_document_filter,
    ensure_collection,
    store_embeddings,
)


def test_build_document_filter_none():
    assert build_document_filter(None) is None


def test_build_document_filter_with_id():
    f = build_document_filter("doc-123")
    assert f is not None
    assert f.must[0].match.value == "doc-123"


def test_store_embeddings_length_mismatch_raises():
    try:
        store_embeddings(["a", "b"], [[0.1, 0.2]])
        assert False, "expected ValueError"
    except ValueError:
        pass


@patch("backend.services.qdrant_service.get_client")
def test_store_embeddings_upserts_with_metadata(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    chunks = ["chunk one", "chunk two"]
    vectors = [[0.1, 0.2], [0.3, 0.4]]
    metadata = [{"document_id": "doc-1"}, {"document_id": "doc-1"}]

    ids = store_embeddings(chunks, vectors, metadata=metadata, collection_name="test_col")

    assert len(ids) == 2
    mock_client.upsert.assert_called_once()
    _, kwargs = mock_client.upsert.call_args
    assert kwargs["collection_name"] == "test_col"
    points = kwargs["points"]
    assert points[0].payload["document_id"] == "doc-1"
    assert points[0].payload["text"] == "chunk one"


# ---------------------------------------------------------------------
# Regression coverage for the missing-payload-index bug:
# "Index required but not found for document_id ..."
# ---------------------------------------------------------------------

@patch("backend.services.qdrant_service.get_client")
def test_ensure_collection_creates_index_on_new_collection(mock_get_client):
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(collections=[])
    mock_client.get_collection.return_value = MagicMock(payload_schema={})
    mock_get_client.return_value = mock_client

    ensure_collection(collection_name="fresh_collection")

    mock_client.create_collection.assert_called_once()
    mock_client.create_payload_index.assert_called_once()
    _, kwargs = mock_client.create_payload_index.call_args
    assert kwargs["collection_name"] == "fresh_collection"
    assert kwargs["field_name"] == DOCUMENT_ID_FIELD


@patch("backend.services.qdrant_service.get_client")
def test_ensure_collection_adds_index_to_existing_collection_without_recreating(mock_get_client):
    # Simulates exactly the reported bug: collection already exists in
    # Qdrant Cloud, but it has no document_id index yet.
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(
        collections=[MagicMock(name="study_companion")]
    )
    mock_client.get_collections.return_value.collections[0].name = "study_companion"
    mock_client.get_collection.return_value = MagicMock(payload_schema={})
    mock_get_client.return_value = mock_client

    ensure_collection(collection_name="study_companion")

    # Must NOT delete/recreate the existing collection.
    mock_client.delete_collection.assert_not_called()
    mock_client.create_collection.assert_not_called()
    # Must add the missing index.
    mock_client.create_payload_index.assert_called_once()


@patch("backend.services.qdrant_service.get_client")
def test_ensure_collection_is_idempotent_when_index_already_present(mock_get_client):
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(
        collections=[MagicMock(name="study_companion")]
    )
    mock_client.get_collections.return_value.collections[0].name = "study_companion"
    mock_client.get_collection.return_value = MagicMock(
        payload_schema={DOCUMENT_ID_FIELD: MagicMock()}
    )
    mock_get_client.return_value = mock_client

    ensure_collection(collection_name="study_companion")
    ensure_collection(collection_name="study_companion")

    # Index already reported present -> never called again, never errors.
    mock_client.create_payload_index.assert_not_called()


@patch("backend.services.retrieval.get_client")
@patch("backend.services.retrieval.embed_query", return_value=[0.1, 0.2])
def test_retrieve_relevant_chunks_scopes_to_document(mock_embed, mock_get_client):
    mock_hit = MagicMock()
    mock_hit.payload = {"text": "some chunk", "document_id": "doc-1"}
    mock_hit.score = 0.9

    mock_client = MagicMock()
    mock_client.query_points.return_value = MagicMock(points=[mock_hit])
    mock_get_client.return_value = mock_client

    from backend.services.retrieval import retrieve_relevant_chunks

    results = retrieve_relevant_chunks("photosynthesis", top_k=3, document_id="doc-1")

    assert len(results) == 1
    assert results[0]["text"] == "some chunk"
    _, kwargs = mock_client.query_points.call_args
    assert kwargs["query_filter"] is not None


@patch("backend.services.retrieval.get_client")
@patch("backend.services.retrieval.embed_query", return_value=[0.1, 0.2])
def test_retrieve_relevant_chunks_isolates_documents(mock_embed, mock_get_client):
    """
    Proves document-level filtering actually works end to end at the
    retrieval.py boundary: querying with document_id="document-A" must
    only ever apply a filter matching "document-A", never leaking into
    "document-B"'s chunks. The real isolation enforcement happens inside
    Qdrant once the payload index exists (covered above); this test
    verifies the client call is built correctly for that enforcement.
    """
    from backend.services.qdrant_service import build_document_filter
    from backend.services.retrieval import retrieve_relevant_chunks

    doc_a_hit = MagicMock()
    doc_a_hit.payload = {"text": "chunk from document A", "document_id": "document-A"}
    doc_a_hit.score = 0.95

    mock_client = MagicMock()
    mock_client.query_points.return_value = MagicMock(points=[doc_a_hit])
    mock_get_client.return_value = mock_client

    results = retrieve_relevant_chunks("some topic", top_k=5, document_id="document-A")

    assert len(results) == 1
    assert all(r["document_id"] == "document-A" for r in results)

    _, kwargs = mock_client.query_points.call_args
    expected_filter = build_document_filter("document-A")
    assert kwargs["query_filter"].must[0].match.value == expected_filter.must[0].match.value
    assert kwargs["query_filter"].must[0].match.value == "document-A"
    assert kwargs["query_filter"].must[0].match.value != "document-B"