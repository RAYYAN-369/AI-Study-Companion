"""
Upload API.

Full pipeline: validate -> extract text -> chunk -> embed -> ensure Qdrant
collection -> store -> return upload metadata (not raw chunks -- the
frontend only needs to know the upload succeeded and which document_id to
pass to /study-plan).
"""

import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.config import settings
from backend.services.chunking import chunk_text
from backend.services.embeddings import embed_texts
from backend.services.parser import extract_text
from backend.services.qdrant_service import ensure_collection, store_embeddings

router = APIRouter()

os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)


def _validate_upload(filename: str, size: int) -> str:
    """Returns the lowercase extension (no dot) or raises HTTPException."""
    ext = os.path.splitext(filename)[1].lower().lstrip(".")

    if ext not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS)).upper()
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '.{ext}'. Allowed formats: {allowed}.",
        )

    if size > settings.MAX_FILE_SIZE:
        max_mb = settings.MAX_FILE_SIZE // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum size is {max_mb}MB.",
        )

    return ext


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    _validate_upload(file.filename, len(contents))

    document_id = str(uuid.uuid4())
    safe_name = f"{document_id}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_FOLDER, safe_name)

    with open(file_path, "wb") as f:
        f.write(contents)

    # --- extract ---
    try:
        text = extract_text(file_path)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Could not extract text from this file: {exc}"
        )

    if not text or not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No extractable text found in this document (it may be a scanned "
            "image, empty, or password-protected).",
        )

    # --- chunk ---
    try:
        chunks = chunk_text(text, chunk_size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chunking failed: {exc}")

    if not chunks:
        raise HTTPException(status_code=422, detail="Document produced no usable chunks.")

    # --- embed ---
    try:
        vectors = embed_texts(chunks)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {exc}")

    # --- store in Qdrant ---
    try:
        ensure_collection()
        metadata = [
            {"document_id": document_id, "filename": file.filename, "chunk_index": i}
            for i in range(len(chunks))
        ]
        store_embeddings(chunks, vectors, metadata=metadata)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vector storage failed: {exc}")

    return {
        "document_id": document_id,
        "filename": file.filename,
        "characters": len(text),
        "total_chunks": len(chunks),
    }
