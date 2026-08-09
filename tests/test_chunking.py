from backend.services.chunking import chunk_text


def test_chunk_text_basic():
    text = "a" * 2000
    chunks = chunk_text(text, chunk_size=800, overlap=100)
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)
    assert len(chunks) > 1


def test_chunk_text_empty():
    assert chunk_text("") == []


def test_chunk_text_overlap_prevents_infinite_loop():
    # overlap >= chunk_size should be sanitized, not hang
    chunks = chunk_text("a" * 100, chunk_size=10, overlap=10)
    assert len(chunks) > 0


def test_chunk_text_short_text_single_chunk():
    chunks = chunk_text("short text", chunk_size=800, overlap=100)
    assert chunks == ["short text"]
