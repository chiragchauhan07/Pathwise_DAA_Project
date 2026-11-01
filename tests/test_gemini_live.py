"""Live Gemini API integration test.

Runs against the real Google Gemini API using the project's configured key and model.
Skips gracefully if GEMINI_API_KEY is not configured or in offline environments.
"""

import pytest
from backend.core_engine.config import settings
from backend.ai_engine.client import get_genai_client, evaluate_unknown_courses
from backend.core_engine.analysis_service import generate_learning_path


@pytest.mark.skipif(
    not settings.is_gemini_configured,
    reason="GEMINI_API_KEY is not configured; skipping live Gemini API test.",
)
class TestGeminiLiveIntegration:
    """Verifies live communication with the Google Gemini API using real credentials."""

    def test_live_minimal_completion(self):
        client = get_genai_client()
        assert client is not None

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents="Reply with only the single word: OK",
        )
        text = (response.text or "").strip()
        assert "ok" in text.lower(), f"Unexpected live Gemini response: {text}"

    def test_live_unknown_course_evaluation(self):
        client = get_genai_client()
        evals = evaluate_unknown_courses(
            queries=["Quantum Computing"],
            client=client,
            model=settings.gemini_model,
            timeout=settings.gemini_timeout,
        )
        assert len(evals) == 1
        eval_item = evals[0]
        assert eval_item["query"] == "Quantum Computing"
        assert "canonical_name" in eval_item
        assert "course_id" in eval_item
        assert eval_item["is_plausible"] is True

    def test_live_learning_path_with_unknown_course(self):
        result = generate_learning_path(
            course_names=["Quantum Computing", "Python Programming"],
            learning_goal="Quantum Information Science",
            use_ai=True,
            fallback_on_ai_failure=True,
        )
        assert result is not None
        course_names = [c["name"] for c in result["selected_courses"]]
        assert "Python Programming" in course_names
        # Ensure the unknown course was evaluated and included
        assert any("quantum" in c.lower() for c in course_names)
        assert len(result["ordered_courses"]) >= 2
        assert len(result["semesters"]) >= 1

