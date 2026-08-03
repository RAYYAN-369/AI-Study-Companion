"""
LLM integration service (Member 3).

Takes retrieved context + the user's topic, prompts Gemini, and returns a
structured JSON study plan. Uses the google-genai SDK.
"""

import json
from typing import Dict

from google import genai
from google.genai import types

from backend.config import settings

MODEL_NAME = "gemini-flash-latest"

STUDY_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "summary": {"type": "string"},
        "estimated_total_hours": {"type": "number"},
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "integer"},
                    "focus": {"type": "string"},
                    "tasks": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "estimated_hours": {"type": "number"},
                },
                "required": ["day", "focus", "tasks"],
            },
        },
    },
    "required": ["topic", "summary", "days"],
}

SYSTEM_PROMPT = """You are a study planning assistant. You will be given
retrieved context from a student's own notes/syllabus, plus a topic they
want to study. Produce a realistic, day-by-day study plan grounded ONLY in
the provided context. Do not invent facts that aren't supported by the
context. If the context is insufficient to cover the topic fully, say so in
the summary field rather than making things up."""


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_study_plan(topic: str, context: str) -> Dict:
    """
    Calls Gemini with the retrieved context and returns a parsed,
    schema-validated study plan dict.
    """
    client = _get_client()

    user_prompt = f"""Topic requested: {topic}

Retrieved context from the student's materials:
{context}

Return the study plan as JSON matching the required schema."""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=STUDY_PLAN_SCHEMA,
        ),
    )

    return json.loads(response.text)