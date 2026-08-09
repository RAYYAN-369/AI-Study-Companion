"""
Unit tests for llm_service.py, mocking the Groq client so no real API key
or network call is needed.
"""

import json
from unittest.mock import MagicMock, patch

from backend.services.llm_service import generate_study_plan


@patch("backend.services.llm_service._get_client")
def test_generate_study_plan_parses_valid_json(mock_get_client):
    fake_plan = {
        "topic": "photosynthesis",
        "summary": "Grounded summary",
        "estimated_total_hours": 4,
        "days": [{"day": 1, "focus": "Basics", "tasks": ["read notes"], "estimated_hours": 2}],
    }
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(fake_plan)))]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    plan = generate_study_plan("photosynthesis", "some context")
    assert plan["topic"] == "photosynthesis"
    assert isinstance(plan["days"], list)


@patch("backend.services.llm_service._get_client")
def test_generate_study_plan_malformed_json_raises(mock_get_client):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="not json"))]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    try:
        generate_study_plan("topic", "context")
        assert False, "expected ValueError"
    except ValueError:
        pass


@patch("backend.services.llm_service._get_client")
def test_generate_study_plan_missing_field_raises(mock_get_client):
    incomplete = {"topic": "x"}  # missing summary/days
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(incomplete)))]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    try:
        generate_study_plan("topic", "context")
        assert False, "expected ValueError"
    except ValueError:
        pass
