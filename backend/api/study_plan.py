"""
Study Plan API.

Ties retrieval.py + llm_service.py together: user sends a topic (and the
document_id returned by /upload), we search Qdrant for relevant chunks
scoped to that document, then ask the LLM to turn that into a plan.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.llm_service import generate_study_plan
from backend.services.retrieval import build_context_string, retrieve_relevant_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/study-plan", tags=["study-plan"])


class StudyPlanRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic the user wants to study")
    top_k: int = Field(5, ge=1, le=20, description="How many chunks to retrieve")
    document_id: Optional[str] = Field(
        None,
        description="document_id returned by /upload. Scopes retrieval to that "
        "document so a query doesn't pull in chunks from a different upload.",
    )


@router.post("")
def create_study_plan(request: StudyPlanRequest):
    # Retrieval hits an external service (Qdrant) -- any failure there
    # (network issue, missing index, bad collection state, etc.) must be
    # turned into a clean HTTPException here rather than propagating as an
    # unhandled exception. An unhandled exception is caught by Starlette's
    # ServerErrorMiddleware *outside* CORSMiddleware, so the resulting 500
    # response is missing CORS headers -- the browser then can't read the
    # response at all and fetch() throws, which the frontend was
    # (correctly, given what it saw) reporting as "can't reach the
    # backend" even though the backend was up and had actually handled the
    # request.
    try:
        chunks = retrieve_relevant_chunks(
            request.topic, top_k=request.top_k, document_id=request.document_id
        )
    except Exception as exc:
        logger.exception("Retrieval from Qdrant failed for topic=%r document_id=%r", request.topic, request.document_id)
        raise HTTPException(
            status_code=502,
            detail="Study plan generation failed because the document could not be "
            "retrieved from the vector store. Please try again in a moment.",
        )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No relevant material found for this topic. Has anything been uploaded yet?",
        )

    context = build_context_string(chunks)

    try:
        plan = generate_study_plan(request.topic, context)
    except Exception as exc:
        logger.exception("Study plan generation failed for topic=%r", request.topic)
        raise HTTPException(
            status_code=502, detail="Study plan generation failed. Please try again."
        )

    # Extend with genuinely available retrieval metadata. No fabricated
    # "coverage score" -- only numbers we can actually compute.
    plan["retrieval"] = {
        "chunks_retrieved": len(chunks),
        "sources": [
            {
                "filename": c.get("filename", "unknown"),
                "chunk_index": c.get("chunk_index"),
                "score": round(c.get("score", 0), 4),
                "text": c.get("text", "")[:300],
            }
            for c in chunks
        ],
    }

    return plan