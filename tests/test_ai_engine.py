import json
from unittest.mock import MagicMock, patch
import pytest

from backend.ai_engine.client import (
    AIAuthenticationError,
    AIConfigurationError,
    AIConnectionError,
    AIRateLimitError,
    AIResponseValidationError,
    AIServiceError,
    AITimeoutError,
    build_course_evaluation_prompt,
    build_prerequisite_prompt,
    evaluate_unknown_courses,
    get_genai_client,
    request_prerequisite_proposals,
    validate_ai_proposals,
    validate_course_evaluations,
)


# --- Prompt Builder Tests ---

def test_build_prerequisite_prompt():
    courses = [
        {"course_id": "python_programming", "name": "Python Programming", "description": "Python basics"},
        {"course_id": "machine_learning", "name": "Machine Learning", "description": "ML algorithms"},
    ]
    existing = [
        {"source_course_id": "python_programming", "target_course_id": "machine_learning", "relationship_type": "recommended"}
    ]

    prompt = build_prerequisite_prompt("AI Engineer", courses, existing)

    assert "system" in prompt and "user" in prompt
    assert "AI Engineer" in prompt["user"]
    assert "python_programming" in prompt["user"]
    assert "machine_learning" in prompt["user"]
    assert "python_programming -> machine_learning" in prompt["user"]
    assert "source_course_id" in prompt["system"]


# --- Response Validator Unit Tests ---

def test_validate_valid_proposals():
    raw_json = json.dumps({
        "proposals": [
            {
                "source_course_id": "linear_algebra",
                "target_course_id": "machine_learning",
                "relationship_type": "required",
                "confidence": 0.95,
                "explanation": "Linear algebra is essential for understanding matrix operations in ML.",
            }
        ]
    })
    allowed_ids = {"linear_algebra", "machine_learning"}
    proposals, errors = validate_ai_proposals(raw_json, allowed_ids)

    assert len(errors) == 0
    assert len(proposals) == 1
    assert proposals[0]["source_course_id"] == "linear_algebra"
    assert proposals[0]["confidence"] == 0.95


def test_validate_empty_proposals():
    raw_json = json.dumps({"proposals": []})
    proposals, errors = validate_ai_proposals(raw_json, {"python_programming"})

    assert len(errors) == 0
    assert proposals == []


def test_validate_markdown_wrapped_json():
    raw_markdown = "```json\n{\"proposals\": []}\n```"
    proposals, errors = validate_ai_proposals(raw_markdown, {"python_programming"})

    assert len(errors) == 0
    assert proposals == []


def test_validate_invalid_json():
    raw = "{ invalid json content }"
    proposals, errors = validate_ai_proposals(raw, {"course_a"})

    assert len(proposals) == 0
    assert len(errors) == 1
    assert "Failed to parse model response as JSON" in errors[0]


def test_validate_unknown_course_id():
    raw = json.dumps({
        "proposals": [
            {
                "source_course_id": "unknown_course",
                "target_course_id": "python_programming",
                "relationship_type": "recommended",
                "confidence": 0.8,
                "explanation": "Explanation",
            }
        ]
    })
    proposals, errors = validate_ai_proposals(raw, {"python_programming"})

    assert len(proposals) == 0
    assert any("references unknown source_course_id: 'unknown_course'" in e for e in errors)


def test_validate_self_referential_relationship():
    raw = json.dumps({
        "proposals": [
            {
                "source_course_id": "python_programming",
                "target_course_id": "python_programming",
                "relationship_type": "required",
                "confidence": 0.9,
                "explanation": "Self loop",
            }
        ]
    })
    proposals, errors = validate_ai_proposals(raw, {"python_programming"})

    assert len(proposals) == 0
    assert any("self-referential" in e for e in errors)


def test_validate_invalid_relationship_type():
    raw = json.dumps({
        "proposals": [
            {
                "source_course_id": "course_a",
                "target_course_id": "course_b",
                "relationship_type": "mandatory_core",  # Invalid type
                "confidence": 0.8,
                "explanation": "Reason",
            }
        ]
    })
    proposals, errors = validate_ai_proposals(raw, {"course_a", "course_b"})

    assert len(proposals) == 0
    assert any("invalid relationship_type" in e for e in errors)


def test_validate_rejects_boolean_confidence():
    raw = json.dumps({
        "proposals": [
            {
                "source_course_id": "course_a",
                "target_course_id": "course_b",
                "relationship_type": "recommended",
                "confidence": True,  # Boolean must be rejected
                "explanation": "Reason",
            }
        ]
    })
    proposals, errors = validate_ai_proposals(raw, {"course_a", "course_b"})

    assert len(proposals) == 0
    assert any("confidence cannot be a boolean" in e for e in errors)


def test_validate_out_of_bounds_confidence():
    raw = json.dumps({
        "proposals": [
            {
                "source_course_id": "course_a",
                "target_course_id": "course_b",
                "relationship_type": "recommended",
                "confidence": 1.25,  # Out of [0, 1] bounds
                "explanation": "Reason",
            }
        ]
    })
    proposals, errors = validate_ai_proposals(raw, {"course_a", "course_b"})

    assert len(proposals) == 0
    assert any("invalid confidence" in e for e in errors)


def test_validate_duplicate_proposals():
    raw = json.dumps({
        "proposals": [
            {
                "source_course_id": "course_a",
                "target_course_id": "course_b",
                "relationship_type": "required",
                "confidence": 0.9,
                "explanation": "First declaration",
            },
            {
                "source_course_id": "course_a",
                "target_course_id": "course_b",
                "relationship_type": "recommended",
                "confidence": 0.8,
                "explanation": "Duplicate declaration",
            },
        ]
    })
    proposals, errors = validate_ai_proposals(raw, {"course_a", "course_b"})

    assert len(proposals) == 1
    assert any("Duplicate proposal pair" in e for e in errors)


def test_validate_rejects_existing_relationships():
    raw = json.dumps({
        "proposals": [
            {
                "source_course_id": "course_a",
                "target_course_id": "course_b",
                "relationship_type": "required",
                "confidence": 0.9,
                "explanation": "Already in KB",
            }
        ]
    })
    existing = {("course_a", "course_b")}
    proposals, errors = validate_ai_proposals(raw, {"course_a", "course_b"}, existing_relationships=existing)

    assert len(proposals) == 0
    assert any("already exists in Knowledge Base" in e for e in errors)


# --- Client Execution & Mocked API Tests (Google Gemini) ---

def test_request_prerequisite_proposals_success():
    courses = [
        {"course_id": "linear_algebra", "name": "Linear Algebra", "description": "Vectors and matrices"},
        {"course_id": "machine_learning", "name": "Machine Learning", "description": "ML algorithms"},
    ]

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "proposals": [
            {
                "source_course_id": "linear_algebra",
                "target_course_id": "machine_learning",
                "relationship_type": "required",
                "confidence": 0.9,
                "explanation": "Math foundation for ML",
            }
        ]
    })

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    result = request_prerequisite_proposals("Data Science", courses, client=mock_client)
    assert len(result) == 1
    assert result[0]["source_course_id"] == "linear_algebra"
    assert result[0]["target_course_id"] == "machine_learning"


def test_request_prerequisite_proposals_missing_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    courses = [{"course_id": "python_programming", "name": "Python", "description": "Intro"}]

    with pytest.raises(AIAuthenticationError, match="GEMINI_API_KEY environment variable is not configured"):
        request_prerequisite_proposals("Goal", courses, client=None)


def test_request_prerequisite_proposals_auth_error():
    class MockAuthError(Exception):
        pass
    MockAuthError.__name__ = "PermissionDenied"

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = MockAuthError("Invalid API key or unauthorized")

    courses = [{"course_id": "course_a", "name": "Course A", "description": "Desc"}]
    with pytest.raises(AIAuthenticationError, match="authentication failed"):
        request_prerequisite_proposals("Goal", courses, client=mock_client)


def test_request_prerequisite_proposals_rate_limit_error():
    class MockRateLimitError(Exception):
        pass
    MockRateLimitError.__name__ = "ResourceExhausted"

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = MockRateLimitError("Quota reached (429)")

    courses = [{"course_id": "course_a", "name": "Course A", "description": "Desc"}]
    with pytest.raises(AIRateLimitError, match="rate limit"):
        request_prerequisite_proposals("Goal", courses, client=mock_client)


def test_request_prerequisite_proposals_timeout_error():
    class MockTimeoutError(Exception):
        pass
    MockTimeoutError.__name__ = "DeadlineExceeded"

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = MockTimeoutError("Request timed out (504)")

    courses = [{"course_id": "course_a", "name": "Course A", "description": "Desc"}]
    with pytest.raises(AITimeoutError, match="timed out"):
        request_prerequisite_proposals("Goal", courses, client=mock_client)


def test_request_prerequisite_proposals_connection_error():
    class MockConnectionError(Exception):
        pass
    MockConnectionError.__name__ = "ConnectError"

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = MockConnectionError("Failed to connect")

    courses = [{"course_id": "course_a", "name": "Course A", "description": "Desc"}]
    with pytest.raises(AIConnectionError, match="Failed to connect"):
        request_prerequisite_proposals("Goal", courses, client=mock_client)


def test_request_prerequisite_proposals_validation_failure():
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "proposals": [
            {
                "source_course_id": "hallucinated_course_xyz",
                "target_course_id": "course_a",
                "relationship_type": "required",
                "confidence": 0.9,
                "explanation": "Invented",
            }
        ]
    })
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    courses = [{"course_id": "course_a", "name": "Course A", "description": "Desc"}]
    with pytest.raises(AIResponseValidationError) as exc_info:
        request_prerequisite_proposals("Goal", courses, client=mock_client)
    assert any("unknown source_course_id" in e for e in exc_info.value.validation_errors)


# --- Timeout Conversion & Validation Tests ---

def test_validate_and_convert_timeout_valid(monkeypatch):
    from backend.ai_engine.client import validate_and_convert_timeout

    # Explicit values
    assert validate_and_convert_timeout(15.0) == (15.0, 15000)
    assert validate_and_convert_timeout(1) == (1.0, 1000)
    assert validate_and_convert_timeout("2.5") == (2.5, 2500)
    assert validate_and_convert_timeout(0.1) == (0.1, 100)

    # Environment variable fallback
    monkeypatch.setenv("GEMINI_TIMEOUT", "15.0")
    assert validate_and_convert_timeout(None) == (15.0, 15000)

    monkeypatch.setenv("GEMINI_TIMEOUT", "30")
    assert validate_and_convert_timeout(None) == (30.0, 30000)


def test_validate_and_convert_timeout_invalid():
    import math
    from backend.ai_engine.client import validate_and_convert_timeout

    invalid_values = [0, 0.0, -1, -15.0, float("nan"), float("inf"), float("-inf"), "abc", "", None]
    
    # Non-None invalid values
    for val in invalid_values[:-1]:
        with pytest.raises(ValueError, match="Invalid timeout value"):
            validate_and_convert_timeout(val)


def test_validate_and_convert_timeout_invalid_env(monkeypatch):
    from backend.ai_engine.client import validate_and_convert_timeout

    for bad_env in ["-10", "0", "not_a_number", "inf"]:
        monkeypatch.setenv("GEMINI_TIMEOUT", bad_env)
        with pytest.raises(ValueError, match="Invalid"):
            validate_and_convert_timeout(None)


def test_client_initialization_passes_milliseconds(monkeypatch):
    """Verifies that client initialization passes milliseconds to types.HttpOptions."""
    from google import genai
    from google.genai import types
    from backend.ai_engine.client import request_prerequisite_proposals

    monkeypatch.setenv("GEMINI_API_KEY", "mock-test-key")

    captured_http_options = {}

    original_http_options = types.HttpOptions

    def mock_http_options(**kwargs):
        captured_http_options.update(kwargs)
        return original_http_options(**kwargs)

    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({"proposals": []})
    mock_client_instance.models.generate_content.return_value = mock_response

    monkeypatch.setattr("google.genai.types.HttpOptions", mock_http_options)
    monkeypatch.setattr("google.genai.Client", lambda *args, **kwargs: mock_client_instance)

    courses = [{"course_id": "course_a", "name": "Course A", "description": "Desc"}]
    request_prerequisite_proposals("Goal", courses, client=None, timeout=15.0)

    assert captured_http_options.get("timeout") == 15000


def test_request_prerequisite_proposals_timeout_error_message():
    class MockTimeoutError(Exception):
        pass
    MockTimeoutError.__name__ = "DeadlineExceeded"

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = MockTimeoutError("Deadline exceeded")

    courses = [{"course_id": "course_a", "name": "Course A", "description": "Desc"}]
    with pytest.raises(AITimeoutError) as exc_info:
        request_prerequisite_proposals("Goal", courses, client=mock_client, timeout=15.0)

    # Message must reflect configured seconds (15.0s) and milliseconds (15000ms)
    assert "15.0s (15000ms)" in str(exc_info.value)


# --- Regression Tests: Configuration, Secrets, and Unknown Course Evaluations ---

def test_missing_api_key_raises_ai_configuration_error():
    with patch("backend.ai_engine.client._get_configured_api_key", return_value=None):
        with pytest.raises(AIConfigurationError, match="GEMINI_API_KEY environment variable is not configured"):
            get_genai_client()


def test_configured_client_can_be_constructed():
    with patch("google.genai.Client") as mock_client_cls:
        client = get_genai_client(api_key="test-dummy-key-12345")
        mock_client_cls.assert_called_once()
        assert client is not None


def test_no_api_key_appears_in_error_message():
    secret_key = "SECRET_SUPER_CONFIDENTIAL_KEY_999"
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception(f"403 Forbidden with key {secret_key}")

    courses = [{"course_id": "course_a", "name": "Course A", "description": "Desc"}]
    with pytest.raises(AIAuthenticationError) as exc_info:
        request_prerequisite_proposals("Goal", courses, client=mock_client)

    # Assert that sanitized exception message never exposes the secret key
    assert secret_key not in str(exc_info.value)
    assert "Gemini API authentication failed" in str(exc_info.value)


def test_build_course_evaluation_prompt():
    prompt = build_course_evaluation_prompt(["Quantum Computing", "Bioinformatics"])
    assert "system" in prompt and "user" in prompt
    assert "Quantum Computing" in prompt["user"]
    assert "Bioinformatics" in prompt["user"]
    assert "is_plausible" in prompt["system"]
    assert "canonical_name" in prompt["system"]


def test_validate_course_evaluations_valid():
    raw_json = json.dumps({
        "evaluations": [
            {
                "query": "Quantum Computing",
                "is_plausible": True,
                "is_ambiguous": False,
                "canonical_name": "Quantum Computing",
                "course_id": "quantum_computing",
                "category": "Interdisciplinary Computing",
                "difficulty": "advanced",
                "description": "Foundations of quantum mechanics applied to computation.",
                "clarification": None,
            }
        ]
    })
    evals, errors = validate_course_evaluations(raw_json)
    assert len(errors) == 0
    assert len(evals) == 1
    assert evals[0]["canonical_name"] == "Quantum Computing"
    assert evals[0]["is_plausible"] is True
    assert evals[0]["difficulty"] == "advanced"


def test_validate_course_evaluations_invalid_json():
    evals, errors = validate_course_evaluations("not valid json")
    assert len(evals) == 0
    assert len(errors) == 1
    assert "Failed to parse" in errors[0]


def test_validate_course_evaluations_missing_fields():
    raw_json = json.dumps({
        "evaluations": [
            {
                "is_plausible": True,
                # missing query
            },
            {
                "query": "Some Course",
                "is_plausible": "not_a_bool",
            }
        ]
    })
    evals, errors = validate_course_evaluations(raw_json)
    assert len(evals) == 0
    assert any("missing or invalid 'query'" in e for e in errors)
    assert any("non-boolean 'is_plausible'" in e for e in errors)


def test_evaluate_unknown_courses_invokes_client():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "evaluations": [
            {
                "query": "Reinforcement Learning Applications",
                "is_plausible": True,
                "is_ambiguous": False,
                "canonical_name": "Applied Reinforcement Learning",
                "course_id": "applied_reinforcement_learning",
                "category": "Artificial Intelligence",
                "difficulty": "advanced",
                "description": "Practical RL algorithms and policy gradients.",
                "clarification": None,
            }
        ]
    })
    mock_client.models.generate_content.return_value = mock_response

    results = evaluate_unknown_courses(["Reinforcement Learning Applications"], client=mock_client)
    assert len(results) == 1
    assert results[0]["canonical_name"] == "Applied Reinforcement Learning"
    assert results[0]["course_id"] == "applied_reinforcement_learning"


def test_get_configured_model_precedence(monkeypatch):
    from backend.ai_engine.client import _get_configured_model
    from backend.core_engine.config import settings

    # Explicit argument takes top priority
    assert _get_configured_model("gemini-custom-model") == "gemini-custom-model"

    # Environment variable overrides settings
    monkeypatch.setenv("GEMINI_MODEL", "gemini-env-override")
    assert _get_configured_model() == "gemini-env-override"

    # Fallback to settings
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(settings, "gemini_model", "gemini-3.5-flash")
    assert _get_configured_model() == "gemini-3.5-flash"


def test_exception_classification_503_service_unavailable():
    from backend.ai_engine.client import _handle_gemini_exception

    exc_503 = Exception("503 UNAVAILABLE. This model is currently experiencing high demand.")
    setattr(exc_503, "code", 503)

    with pytest.raises(AIServiceError) as exc_info:
        _handle_gemini_exception(exc_503, 15.0, 15000)

    assert "temporarily unavailable" in str(exc_info.value)
    assert "high demand" in str(exc_info.value)


def test_exception_classification_404_model_not_found():
    from backend.ai_engine.client import _handle_gemini_exception

    exc_404 = Exception("404 NOT_FOUND. models/gemini-2.0-flash is no longer available.")
    setattr(exc_404, "code", 404)

    with pytest.raises(AIServiceError) as exc_info:
        _handle_gemini_exception(exc_404, 15.0, 15000)

    assert "not supported or not found" in str(exc_info.value)


def test_evaluate_unknown_courses_retry_on_503():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "evaluations": [
            {
                "query": "Quantum Computing",
                "is_plausible": True,
                "is_ambiguous": False,
                "canonical_name": "Quantum Computing",
                "course_id": "quantum_computing",
                "category": "Interdisciplinary Computing",
                "difficulty": "advanced",
                "description": "Quantum mechanics applied to computation.",
                "clarification": None,
            }
        ]
    })

    exc_503 = Exception("503 UNAVAILABLE. High demand.")
    setattr(exc_503, "code", 503)

    # First attempt raises 503, second attempt succeeds
    mock_client.models.generate_content.side_effect = [exc_503, mock_response]

    results = evaluate_unknown_courses(["Quantum Computing"], client=mock_client)
    assert len(results) == 1
    assert results[0]["canonical_name"] == "Quantum Computing"
    assert mock_client.models.generate_content.call_count == 2




