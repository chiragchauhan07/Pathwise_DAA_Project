import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from backend.ai_engine.client import (
    AIAuthenticationError,
    AIConfigurationError,
    AIRateLimitError,
    AIResponseValidationError,
    AIServiceError,
    AITimeoutError,
    _get_configured_api_key,
    _get_configured_model,
    _handle_gemini_exception,
    evaluate_unknown_courses,
    get_genai_client,
    request_prerequisite_proposals,
    validate_and_convert_timeout,
)
from backend.core_engine.analysis_service import generate_learning_path
from backend.core_engine.config import (
    PROJECT_ROOT,
    _parse_env_file_pure_python,
    load_project_env,
    settings,
)


class TestEnvironmentAndConfigLoading:
    """Tests for deterministic .env loading, working directory independence, and secret safety."""

    def test_project_root_deterministic(self):
        assert PROJECT_ROOT.is_dir()
        assert (PROJECT_ROOT / "backend").is_dir()
        assert (PROJECT_ROOT / "requirements.txt").is_file()

    def test_pure_python_env_parser(self, tmp_path):
        env_file = tmp_path / "test.env"
        env_file.write_text(
            "# Comment line\n"
            "TEST_VAR_A=hello_world\n"
            "TEST_VAR_B='quoted value'\n"
            'TEST_VAR_C="double quoted"\n'
            "TEST_VAR_EMPTY=\n",
            encoding="utf-8",
        )
        loaded = _parse_env_file_pure_python(env_file, override=True)
        assert loaded is True
        assert os.environ.get("TEST_VAR_A") == "hello_world"
        assert os.environ.get("TEST_VAR_B") == "quoted value"
        assert os.environ.get("TEST_VAR_C") == "double quoted"
        assert os.environ.get("TEST_VAR_EMPTY") == ""

    def test_pure_python_env_preserves_os_environ_without_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EXISTING_KEY", "os_original")
        env_file = tmp_path / "test2.env"
        env_file.write_text("EXISTING_KEY=from_env_file\nNEW_KEY=from_file\n", encoding="utf-8")

        _parse_env_file_pure_python(env_file, override=False)
        assert os.environ["EXISTING_KEY"] == "os_original"
        assert os.environ["NEW_KEY"] == "from_file"

    def test_loading_from_different_working_directory(self, tmp_path, monkeypatch):
        # Change current working directory to a completely different temporary directory
        monkeypatch.chdir(tmp_path)
        assert Path.cwd() == tmp_path

        # load_project_env should still find the project-root .env via PROJECT_ROOT
        source = load_project_env(override=False)
        assert source in ("os_environ", "dotenv_file", "empty", "none")
        assert settings.service_name == "daa-learning-path-api"

    def test_centralized_model_configuration(self, monkeypatch):
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        settings.reload(override=False)
        assert settings.gemini_model == "gemini-3.5-flash-lite"
        assert _get_configured_model() == "gemini-3.5-flash-lite"

        # Explicit OS env var overrides
        monkeypatch.setenv("GEMINI_MODEL", "gemini-test-custom")
        assert _get_configured_model() == "gemini-test-custom"

    def test_safe_diagnostic_never_leaks_key(self):
        diag = settings.get_ai_diagnostic()
        assert "is_configured" in diag
        assert "is_empty" in diag
        assert "key_source" in diag
        assert "model" in diag
        assert "timeout_seconds" in diag
        assert "max_retries" in diag
        # Assert no key values appear
        assert "gemini_api_key" not in diag
        assert "api_key" not in diag


class TestClientInitializationAndErrorClassification:
    """Tests for missing key, empty key, and SDK exception classifications."""

    def test_missing_api_key_raises_configuration_error(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with patch("backend.ai_engine.client._get_configured_api_key", return_value=None):
            with pytest.raises(AIConfigurationError, match="GEMINI_API_KEY environment variable is not configured"):
                get_genai_client(api_key=None)

    def test_empty_api_key_raises_configuration_error(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "   ")
        with pytest.raises(AIConfigurationError, match="configured but empty"):
            get_genai_client(api_key=None)

        with pytest.raises(AIConfigurationError, match="configured but empty"):
            get_genai_client(api_key="")

    def test_authentication_error_mapping(self):
        class MockAuthException(Exception):
            code = 401

        with pytest.raises(AIAuthenticationError, match="authentication failed"):
            _handle_gemini_exception(MockAuthException("API key invalid"), 15.0, 15000)

    def test_quota_error_mapping(self):
        class MockQuotaException(Exception):
            code = 429

        with pytest.raises(AIRateLimitError, match="rate limit or quota exceeded"):
            _handle_gemini_exception(MockQuotaException("RESOURCE_EXHAUSTED: quota exceeded"), 15.0, 15000)

    def test_timeout_error_mapping(self):
        class MockTimeoutException(Exception):
            code = 504

        with pytest.raises(AITimeoutError, match="timed out"):
            _handle_gemini_exception(MockTimeoutException("DeadlineExceeded"), 15.0, 15000)

    def test_service_unavailable_mapping(self):
        class MockUnavailableException(Exception):
            code = 503

        with pytest.raises(AIServiceError, match="temporarily unavailable"):
            _handle_gemini_exception(MockUnavailableException("high demand / unavailable"), 15.0, 15000)

    def test_model_not_found_mapping(self):
        class MockNotFoundException(Exception):
            code = 404

        with pytest.raises(AIServiceError, match="not supported or not found"):
            _handle_gemini_exception(MockNotFoundException("models/not-found is not found"), 15.0, 15000)


class TestPipelineFallbackAndAIWorkflow:
    """Tests for unknown course evaluation, quota fallback, and proposal integration."""

    def test_quota_fallback_retains_curated_path_with_accurate_warning(self):
        # Mock client to simulate a 429 quota exhaustion
        mock_client = MagicMock()
        mock_exc = Exception("429 RESOURCE_EXHAUSTED Quota exceeded")
        mock_exc.code = 429
        mock_client.models.generate_content.side_effect = mock_exc

        result = generate_learning_path(
            course_names=["Python Programming", "Data Structures"],
            ai_client=mock_client,
            use_ai=True,
            fallback_on_ai_failure=True,
        )

        assert len(result["selected_courses"]) == 2
        assert len(result["ordered_courses"]) == 2
        assert result["ai_proposals_used"] is False
        # Verify the warning accurately states rate limit or quota exceeded, NOT "missing key"
        matching_warning = any("rate limit or quota exceeded" in w.lower() for w in result["warnings"])
        assert matching_warning, f"Expected quota warning, got: {result['warnings']}"

    def test_unknown_course_evaluation_pipeline(self):
        # Mock Gemini response for unknown course evaluation
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"evaluations": [{"query": "Bioinformatics", "is_plausible": true, "canonical_name": "Computational Biology", "course_id": "comp_bio", "difficulty": "intermediate", "category": "Interdisciplinary", "description": "Intro to computational biology"}]}'
        mock_client.models.generate_content.return_value = mock_response

        evals = evaluate_unknown_courses(
            queries=["Bioinformatics"],
            client=mock_client,
            model="gemini-3.5-flash-lite",
            timeout=10.0,
        )
        assert len(evals) == 1
        assert evals[0]["canonical_name"] == "Computational Biology"
        assert evals[0]["course_id"] == "comp_bio"

    def test_malformed_ai_output_raises_validation_error(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"evaluations": "not a list"}'
        mock_client.models.generate_content.return_value = mock_response

        with pytest.raises(AIResponseValidationError):
            evaluate_unknown_courses(
                queries=["Bioinformatics"],
                client=mock_client,
                model="gemini-3.5-flash-lite",
            )
