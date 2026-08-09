"""
Integration-style tests for the /upload and /study-plan endpoints, using
FastAPI's TestClient. External services (embeddings model, Qdrant, Groq)
are mocked so these run without credentials or network access.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_home():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_upload_rejects_unsupported_extension():
    resp = client.post(
        "/upload",
        files={"file": ("notes.exe", b"binary junk", "application/octet-stream")},
    )
    assert resp.status_code == 415


def test_upload_rejects_oversized_file():
    from backend.config import settings

    big_content = b"a" * (settings.MAX_FILE_SIZE + 1)
    resp = client.post(
        "/upload",
        files={"file": ("notes.txt", big_content, "text/plain")},
    )
    assert resp.status_code == 413


@patch("backend.app.api.upload.store_embeddings", return_value=["id-1"])
@patch("backend.app.api.upload.ensure_collection", return_value=None)
@patch("backend.app.api.upload.embed_texts", return_value=[[0.1, 0.2]])
def test_upload_success(mock_embed, mock_ensure, mock_store):
    resp = client.post(
        "/upload",
        files={"file": ("notes.txt", b"Photosynthesis is how plants make energy.", "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "document_id" in body
    assert body["filename"] == "notes.txt"
    assert body["total_chunks"] >= 1


def test_upload_rejects_empty_document():
    resp = client.post(
        "/upload",
        files={"file": ("empty.txt", b"   ", "text/plain")},
    )
    assert resp.status_code == 422


def test_study_plan_missing_topic_returns_422():
    resp = client.post("/study-plan", json={})
    assert resp.status_code == 422


@patch("backend.api.study_plan.retrieve_relevant_chunks", return_value=[])
def test_study_plan_no_chunks_returns_404(mock_retrieve):
    resp = client.post("/study-plan", json={"topic": "photosynthesis"})
    assert resp.status_code == 404


@patch("backend.api.study_plan.generate_study_plan")
@patch(
    "backend.api.study_plan.retrieve_relevant_chunks",
    return_value=[{"text": "some chunk", "score": 0.9, "filename": "notes.txt", "chunk_index": 0}],
)
def test_study_plan_success_includes_retrieval_metadata(mock_retrieve, mock_generate):
    mock_generate.return_value = {
        "topic": "photosynthesis",
        "summary": "grounded summary",
        "estimated_total_hours": 3,
        "days": [{"day": 1, "focus": "basics", "tasks": ["read"], "estimated_hours": 3}],
    }
    resp = client.post("/study-plan", json={"topic": "photosynthesis", "top_k": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["topic"] == "photosynthesis"
    assert "retrieval" in body
    assert body["retrieval"]["chunks_retrieved"] == 1
    assert "coverage_score" not in body  # no fabricated metrics
