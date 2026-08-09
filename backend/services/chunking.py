"""
Text chunking service.

Splits extracted document text into overlapping fixed-size chunks. Output is
always `List[str]` so it stays a drop-in compatible input for
embeddings.embed_texts().

Overlap (instead of the original hard cut-off) was added so a sentence that
straddles a chunk boundary still has a fair chance of being retrieved whole
by at least one chunk. This is a small, backward-compatible change: with
overlap=0 it behaves exactly like the original fixed-size splitter.
"""

from typing import List


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping fixed-size chunks.

    Args:
        text: raw extracted document text.
        chunk_size: max characters per chunk.
        overlap: characters repeated between consecutive chunks, so context
            isn't lost at a hard boundary. Must be smaller than chunk_size.

    Returns:
        List of non-empty chunk strings, in order.
    """
    if not text:
        return []

    if overlap >= chunk_size:
        overlap = 0  # avoid an infinite loop from misconfiguration

    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)

    return chunks
