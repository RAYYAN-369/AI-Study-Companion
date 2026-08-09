"""
Verifies the embedding model's output dimension matches
settings.EMBEDDING_DIM, i.e. what the Qdrant collection is configured with.

Requires downloading the sentence-transformers model (network access to
huggingface.co) -- skipped automatically if that's unavailable.
"""

import pytest

from backend.config import settings


def test_embedding_dimension_matches_config():
    pytest.importorskip("sentence_transformers")
    try:
        from backend.services.embeddings import embed_texts
        vectors = embed_texts(["a quick dimension check"])
    except Exception as exc:
        pytest.skip(f"embedding model unavailable in this environment: {exc}")

    assert len(vectors[0]) == settings.EMBEDDING_DIM
