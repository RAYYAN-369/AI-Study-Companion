"""
Study Plan API (Member 3).

Ties retrieval.py + llm_service.py together: user sends a topic, we search
Qdrant for relevant chunks, then ask Gemini to turn that into a plan.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.llm_service import generate_study_plan
from backend.services.retrieval import build_context_string, retrieve_relevant_chunks

router = APIRouter(prefix="/study-plan", tags=["study-plan"])


class StudyPlanRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic the user wants to study")
    top_k: int = Field(5, ge=1, le=20, description="How many chunks to retrieve")


@router.post("")
def create_study_plan(request: StudyPlanRequest):
    chunks = retrieve_relevant_chunks(request.topic, top_k=request.top_k)

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No relevant material found for this topic. Has anything been uploaded yet?",
        )

    context = build_context_string(chunks)

    try:
        plan = generate_study_plan(request.topic, context)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Study plan generation failed: {exc}"
        )

    return plan