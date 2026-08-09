"""
LLM integration service.

Takes retrieved context + the user's topic, prompts an LLM, and returns a
structured JSON study plan. Uses Groq (OpenAI-compatible chat completions
API via the official `groq` SDK) instead of Gemini -- swapped because that's
the API key actually available for this project.
"""

import json
from typing import Dict

from groq import Groq

from backend.config import settings

# Groq's current fast general-purpose model. See
# https://console.groq.com/docs/models for the up-to-date list.
MODEL_NAME = "llama-3.3-70b-versatile"

STUDY_PLAN_SCHEMA_DESCRIPTION = """{
  "topic": string,
  "summary": string,
  "estimated_total_hours": number,
  "days": [
    {
      "day": integer,
      "focus": string,
      "tasks": [string, ...],
      "estimated_hours": number
    }
  ]
}"""

SYSTEM_PROMPT = f"""You are a study planning assistant. You will be given
retrieved context from a student's own notes/syllabus, plus a topic they
want to study. Produce a realistic, day-by-day study plan grounded ONLY in
the provided context. Do not invent facts that aren't supported by the
context. If the context is insufficient to cover the topic fully, say so in
the summary field rather than making things up.

Respond with ONLY a single valid JSON object, no markdown fences, no
commentary, matching exactly this shape:
{STUDY_PLAN_SCHEMA_DESCRIPTION}"""


def _get_client() -> Groq:
    return Groq(api_key=settings.GROQ_API_KEY)


def generate_study_plan(topic: str, context: str) -> Dict:
    """
    Calls Groq with the retrieved context and returns a parsed study plan
    dict. Raises on API failure or malformed JSON -- callers (study_plan.py)
    are responsible for turning that into a proper HTTP error.
    """
    client = _get_client()

    user_prompt = f"""Topic requested: {topic}

Retrieved context from the student's materials:
{context}

Return the study plan as JSON matching the required schema."""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    raw = response.choices[0].message.content

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model returned malformed JSON: {exc}") from exc

    # Minimal shape validation -- catch a malformed response early rather
    # than silently sending a broken object to the frontend.
    for field in ("topic", "summary", "days"):
        if field not in plan:
            raise ValueError(f"Model response missing required field: {field}")

    return plan
