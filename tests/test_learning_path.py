import json
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.ai_engine.client import (
    AIAuthenticationError,
    AIRateLimitError,
    AITimeoutError,
)
from backend.core_engine.analysis_service import (
    CourseResolutionError,
    CycleConflictError,
    generate_learning_path,
)
from backend.core_engine.main import app
from backend.knowledge_base.knowledge_base import get_default_knowledge_base

test_client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit / Service Integration Tests: generate_learning_path
# ---------------------------------------------------------------------------


def test_generate_learning_path_empty_input():
    with pytest.raises(CourseResolutionError, match="Course list cannot be empty"):
        generate_learning_path([])


def test_generate_learning_path_unknown_course():
    with pytest.raises(CourseResolutionError, match="Course 'Quantum Time Travel 101' is not recognized"):
        generate_learning_path(["Python Programming", "Quantum Time Travel 101"], use_ai=False)


def test_generate_learning_path_course_normalization_and_alias():
    # "python" -> python_programming, "ml" -> machine_learning
    # In KB, python_programming -> machine_learning is a recommended prerequisite
    result = generate_learning_path(
        ["ml", "python"],
        learning_goal="AI/ML Track",
        use_ai=False,
    )
    ordered_ids = [c["course_id"] for c in result["ordered_courses"]]
    assert ordered_ids == ["python_programming", "machine_learning"]
    assert result["learning_goal"] == "AI/ML Track"
    assert result["ai_proposals_used"] is False


def test_generate_learning_path_preserves_prerequisite_ordering():
    # KB chain: programming_fundamentals -> data_structures -> design_and_analysis_of_algorithms
    result = generate_learning_path(
        ["Algorithms", "Data Structures", "Intro to Programming"],
        learning_goal="Master Algorithms",
        use_ai=False,
    )
    ordered_ids = [c["course_id"] for c in result["ordered_courses"]]
    assert ordered_ids == ["programming_fundamentals", "data_structures", "design_and_analysis_of_algorithms"]

    # Verify that every prerequisite appears before its dependent
    index_map = {cid: i for i, cid in enumerate(ordered_ids)}
    for prereq in result["prerequisites"]:
        src = prereq["source_course_id"]
        tgt = prereq["target_course_id"]
        assert index_map[src] < index_map[tgt]


def test_generate_learning_path_without_ai():
    result = generate_learning_path(
        ["linear_algebra", "machine_learning"],
        learning_goal="ML Fundamentals",
        use_ai=False,
    )
    ordered_ids = [c["course_id"] for c in result["ordered_courses"]]
    # linear_algebra is a prerequisite for machine_learning
    assert ordered_ids == ["linear_algebra", "machine_learning"]
    assert result["ai_proposals_used"] is False
    assert any("AI assistance was disabled" in w for w in result["warnings"])


def test_generate_learning_path_incorporates_valid_ai_proposals():
    # Two courses without a direct KB edge: cloud_computing and cybersecurity
    mock_gemini_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "proposals": [
            {
                "source_course_id": "cybersecurity",
                "target_course_id": "cloud_computing",
                "relationship_type": "recommended",
                "confidence": 0.92,
                "explanation": "Cloud security architecture builds upon fundamental cybersecurity concepts.",
            }
        ]
    })
    mock_gemini_client.models.generate_content.return_value = mock_response

    result = generate_learning_path(
        ["cloud_computing", "cybersecurity"],
        learning_goal="Cloud Security Specialist",
        ai_client=mock_gemini_client,
        use_ai=True,
    )

    ordered_ids = [c["course_id"] for c in result["ordered_courses"]]
    assert ordered_ids == ["cybersecurity", "cloud_computing"]
    assert result["ai_proposals_used"] is True
    ai_prereqs = [
        p for p in result["prerequisites"]
        if p["source_course_id"] == "cybersecurity" and p["target_course_id"] == "cloud_computing"
    ]
    assert len(ai_prereqs) == 1
    assert ai_prereqs[0]["relationship_type"] == "recommended"


def test_generate_learning_path_does_not_duplicate_existing_relationships():
    # In KB, programming_fundamentals -> data_structures is already curated
    mock_gemini_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "proposals": [
            {
                "source_course_id": "programming_fundamentals",
                "target_course_id": "data_structures",
                "relationship_type": "recommended",
                "confidence": 0.85,
                "reasoning": "Duplicate of existing KB relationship.",
            }
        ]
    })
    mock_gemini_client.models.generate_content.return_value = mock_response

    result = generate_learning_path(
        ["programming_fundamentals", "data_structures"],
        learning_goal="Fundamentals",
        ai_client=mock_gemini_client,
        use_ai=True,
    )

    edges = [
        p for p in result["prerequisites"]
        if p["source_course_id"] == "programming_fundamentals" and p["target_course_id"] == "data_structures"
    ]
    assert len(edges) == 1
    assert edges[0]["relationship_type"] == "required"


def test_generate_learning_path_rejects_invalid_ai_proposals():
    # AI proposes an invalid course not in the selected subset
    mock_gemini_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "proposals": [
            {
                "source_course_id": "quantum_computing",
                "target_course_id": "programming_fundamentals",
                "relationship_type": "recommended",
                "confidence": 0.9,
                "reasoning": "External course outside selection",
            }
        ]
    })
    mock_gemini_client.models.generate_content.return_value = mock_response

    result = generate_learning_path(
        ["programming_fundamentals", "data_structures"],
        learning_goal="Basics",
        ai_client=mock_gemini_client,
        use_ai=True,
    )

    ordered_ids = [c["course_id"] for c in result["ordered_courses"]]
    assert "quantum_computing" not in ordered_ids
    assert ordered_ids == ["programming_fundamentals", "data_structures"]


def test_generate_learning_path_ai_cycle_detection_and_rejection():
    # KB edge: programming_fundamentals -> data_structures
    # AI proposes inverse edge: data_structures -> programming_fundamentals (creates cycle)
    mock_gemini_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "proposals": [
            {
                "source_course_id": "data_structures",
                "target_course_id": "programming_fundamentals",
                "relationship_type": "recommended",
                "confidence": 0.95,
                "explanation": "Cyclic proposal causing loop",
            }
        ]
    })
    mock_gemini_client.models.generate_content.return_value = mock_response

    with pytest.raises(CycleConflictError) as exc_info:
        generate_learning_path(
            ["programming_fundamentals", "data_structures"],
            learning_goal="Cycle test",
            ai_client=mock_gemini_client,
            use_ai=True,
        )

    assert "Cyclic dependency detected" in str(exc_info.value)
    assert len(exc_info.value.cycle_path) >= 2


def test_generate_learning_path_ai_failure_safe_fallback():
    mock_gemini_client = MagicMock()
    mock_gemini_client.models.generate_content.side_effect = AITimeoutError("Gemini timed out")

    result = generate_learning_path(
        ["programming_fundamentals", "data_structures"],
        learning_goal="Fallback test",
        ai_client=mock_gemini_client,
        use_ai=True,
        fallback_on_ai_failure=True,
    )

    assert result["ai_proposals_used"] is False
    assert any("AI proposals were unavailable" in w for w in result["warnings"])
    assert [c["course_id"] for c in result["ordered_courses"]] == ["programming_fundamentals", "data_structures"]


def test_generate_learning_path_ai_failure_without_fallback_raises():
    mock_gemini_client = MagicMock()
    mock_gemini_client.models.generate_content.side_effect = AIRateLimitError("Gemini quota exhausted")

    with pytest.raises(AIRateLimitError):
        generate_learning_path(
            ["programming_fundamentals", "data_structures"],
            learning_goal="No fallback test",
            ai_client=mock_gemini_client,
            use_ai=True,
            fallback_on_ai_failure=False,
        )


def test_original_knowledge_base_remains_unchanged():
    kb = get_default_knowledge_base()
    initial_course_count = len(kb.get_all_courses())
    initial_prereq_count = len(kb.get_prerequisites())

    assert initial_course_count == 70
    assert initial_prereq_count == 115

    mock_gemini_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "proposals": [
            {
                "source_course_id": "linear_algebra",
                "target_course_id": "machine_learning",
                "relationship_type": "recommended",
                "confidence": 0.9,
                "reasoning": "Linear algebra aids ML understanding",
            }
        ]
    })
    mock_gemini_client.models.generate_content.return_value = mock_response

    generate_learning_path(
        ["machine_learning", "linear_algebra"],
        learning_goal="In-Memory Test",
        kb=kb,
        ai_client=mock_gemini_client,
        use_ai=True,
    )

    assert len(kb.get_all_courses()) == initial_course_count
    assert len(kb.get_prerequisites()) == initial_prereq_count


# ---------------------------------------------------------------------------
# API Endpoint Integration Tests: POST /api/v1/learning-path
# ---------------------------------------------------------------------------


def test_api_learning_path_success(monkeypatch):
    def mock_proposals(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "backend.core_engine.analysis_service.request_prerequisite_proposals",
        mock_proposals,
    )

    payload = {
        "courses": ["Intro to Programming", "Data Structures", "Algorithms"],
        "learning_goal": "Master Technical Interviews",
        "use_ai": True,
        "fallback_on_ai_failure": True,
    }
    response = test_client.post("/api/v1/learning-path", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["learning_goal"] == "Master Technical Interviews"
    assert len(data["selected_courses"]) == 3
    assert len(data["ordered_courses"]) == 3

    ordered_ids = [c["course_id"] for c in data["ordered_courses"]]
    assert ordered_ids == ["programming_fundamentals", "data_structures", "design_and_analysis_of_algorithms"]
    assert isinstance(data["prerequisites"], list)


def test_api_learning_path_unknown_course():
    payload = {
        "courses": ["Python Programming", "NonExistentCourseXYZ"],
        "learning_goal": "Failure Test",
    }
    response = test_client.post("/api/v1/learning-path", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "course_resolution_error"
    assert "NonExistentCourseXYZ" in data["detail"]["message"]


def test_api_learning_path_empty_courses_validation():
    payload = {
        "courses": [],
        "learning_goal": "Empty test",
    }
    response = test_client.post("/api/v1/learning-path", json=payload)
    assert response.status_code == 422


def test_api_learning_path_cycle_error(monkeypatch):
    def mock_proposals(*args, **kwargs):
        return [
            {
                "source_course_id": "data_structures",
                "target_course_id": "programming_fundamentals",
                "relationship_type": "recommended",
                "confidence": 0.99,
                "reasoning": "Cyclic feedback loop",
            }
        ]

    monkeypatch.setattr(
        "backend.core_engine.analysis_service.request_prerequisite_proposals",
        mock_proposals,
    )

    payload = {
        "courses": ["Programming Fundamentals", "Data Structures"],
        "learning_goal": "Detect Cycle",
        "use_ai": True,
        "fallback_on_ai_failure": True,
    }
    response = test_client.post("/api/v1/learning-path", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "cyclic_dependency_error"
    assert "cycle_path" in data["detail"]


def test_api_learning_path_ai_error_without_fallback(monkeypatch):
    def mock_proposals(*args, **kwargs):
        raise AIAuthenticationError("Invalid API key")

    monkeypatch.setattr(
        "backend.core_engine.analysis_service.request_prerequisite_proposals",
        mock_proposals,
    )

    payload = {
        "courses": ["Python Programming", "Data Structures"],
        "learning_goal": "Fail AI Test",
        "use_ai": True,
        "fallback_on_ai_failure": False,
    }
    response = test_client.post("/api/v1/learning-path", json=payload)
    assert response.status_code == 502
    data = response.json()
    assert data["detail"]["error"] == "ai_service_error"


# --- Single Course AI Skip & Empty Proposals Tests ---

def test_generate_learning_path_single_course_skips_ai():
    mock_client = MagicMock()

    result = generate_learning_path(
        ["Python Programming"],
        learning_goal="Learn Python",
        ai_client=mock_client,
        use_ai=True,
    )

    # Gemini must NOT be called for a single course
    mock_client.models.generate_content.assert_not_called()
    assert result["ai_proposals_used"] is False
    assert len(result["ordered_courses"]) == 1
    assert result["ordered_courses"][0]["course_id"] == "python_programming"
    assert any("skipped because only a single distinct course was resolved" in w for w in result["warnings"])


def test_generate_learning_path_two_courses_calls_ai():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({"proposals": []})
    mock_client.models.generate_content.return_value = mock_response

    result = generate_learning_path(
        ["Python Programming", "Machine Learning"],
        learning_goal="AI Track",
        ai_client=mock_client,
        use_ai=True,
    )

    # Gemini must be called when at least 2 courses are selected
    mock_client.models.generate_content.assert_called_once()
    assert len(result["ordered_courses"]) == 2


def test_generate_learning_path_empty_ai_proposals_sets_flag_false():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({"proposals": []})
    mock_client.models.generate_content.return_value = mock_response

    result = generate_learning_path(
        ["Linear Algebra", "Machine Learning"],
        learning_goal="Math and ML",
        ai_client=mock_client,
        use_ai=True,
    )

    # When Gemini returns empty proposals, ai_proposals_used must be False
    assert result["ai_proposals_used"] is False
    assert any("no additional prerequisite relationships were proposed" in w for w in result["warnings"])


def test_api_learning_path_provenance(monkeypatch):
    # Propose an additional AI relationship between cybersecurity and cloud_computing
    def mock_proposals(*args, **kwargs):
        return [
            {
                "source_course_id": "cybersecurity",
                "target_course_id": "cloud_computing",
                "relationship_type": "recommended",
                "confidence": 0.88,
                "explanation": "Security is crucial for cloud deployments.",
            }
        ]

    monkeypatch.setattr(
        "backend.core_engine.analysis_service.request_prerequisite_proposals",
        mock_proposals,
    )

    payload = {
        "courses": ["Intro to Programming", "Data Structures", "Cloud Computing", "Cybersecurity"],
        "learning_goal": "Cloud and Security Engineering",
        "use_ai": True,
    }
    response = test_client.post("/api/v1/learning-path", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["ai_proposals_used"] is True

    # Check that both curated and AI-proposed records retain provenance
    prereqs = data["prerequisites"]
    curated_records = [p for p in prereqs if p["source"] == "curated"]
    ai_records = [p for p in prereqs if p["source"] == "ai_proposed"]

    assert len(curated_records) >= 1
    for cr in curated_records:
        assert cr["is_ai_proposed"] is False
        assert cr["evidence_type"] == "expert_curated"
        assert "confidence" in cr

    assert len(ai_records) == 1
    ai_rec = ai_records[0]
    assert ai_rec["source_course_id"] == "cybersecurity"
    assert ai_rec["target_course_id"] == "cloud_computing"
    assert ai_rec["is_ai_proposed"] is True
    assert ai_rec["confidence"] == 0.88
    assert ai_rec["evidence_type"] == "llm_proposed"
    assert "Security is crucial" in ai_rec["explanation"]


def test_knowledge_base_remains_unchanged_on_failed_cycle_request():
    kb = get_default_knowledge_base()
    initial_courses = len(kb.get_all_courses())
    initial_prereqs = len(kb.get_prerequisites())

    # Mock AI proposing a cyclic dependency
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "proposals": [
            {
                "source_course_id": "data_structures",
                "target_course_id": "programming_fundamentals",
                "relationship_type": "required",
                "confidence": 0.99,
                "explanation": "Artificial cycle proposal",
            }
        ]
    })
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(CycleConflictError):
        generate_learning_path(
            ["Programming Fundamentals", "Data Structures"],
            learning_goal="Cycle Failure Test",
            kb=kb,
            ai_client=mock_client,
            use_ai=True,
        )

    # Assert KB was not mutated despite the failed request
    assert len(kb.get_all_courses()) == initial_courses
    assert len(kb.get_prerequisites()) == initial_prereqs


# --- Phase 7 Regression Tests: Unknown Courses, DAA Authority, and Security ---

def test_generate_learning_path_with_plausible_unknown_course(monkeypatch):
    """Proves that Gemini is reached for eligible unknown courses and incorporated safely."""
    # Mock evaluate_unknown_courses
    def mock_evaluate(queries, client=None, **kwargs):
        return [
            {
                "query": "Neuromorphic Computing",
                "is_plausible": True,
                "is_ambiguous": False,
                "canonical_name": "Neuromorphic Computing",
                "course_id": "neuromorphic_computing",
                "category": "Novel Computing Architectures",
                "difficulty": "advanced",
                "description": "Brain-inspired spiking neural network architectures and hardware.",
                "clarification": None,
            }
        ]

    # Mock request_prerequisite_proposals to propose Linear Algebra -> Neuromorphic Computing
    def mock_proposals(learning_goal, courses, existing_prerequisites=None, client=None, **kwargs):
        return [
            {
                "source_course_id": "linear_algebra",
                "target_course_id": "neuromorphic_computing",
                "relationship_type": "required",
                "confidence": 0.95,
                "explanation": "Linear algebra is fundamental for state space vectors.",
            }
        ]

    monkeypatch.setattr("backend.core_engine.analysis_service.evaluate_unknown_courses", mock_evaluate)
    monkeypatch.setattr("backend.core_engine.analysis_service.request_prerequisite_proposals", mock_proposals)

    result = generate_learning_path(
        ["Linear Algebra", "Neuromorphic Computing"],
        learning_goal="Brain-Inspired Computing Fundamentals",
        use_ai=True,
    )

    ordered_ids = [c["course_id"] for c in result["ordered_courses"]]
    # Linear Algebra must precede Neuromorphic Computing
    assert ordered_ids == ["linear_algebra", "neuromorphic_computing"]

    # Verify provenance of the unknown course
    qc_course = next(c for c in result["selected_courses"] if c["course_id"] == "neuromorphic_computing")
    assert qc_course["source"] == "ai_inferred"
    assert qc_course["is_ai_inferred"] is True
    assert qc_course["provenance"] == "ai_inferred_candidate"

    # Verify provenance of the AI proposed relationship
    qc_rel = next(r for r in result["prerequisites"] if r["target_course_id"] == "neuromorphic_computing")
    assert qc_rel["source"] == "ai_proposed"
    assert qc_rel["is_ai_proposed"] is True
    assert qc_rel["evidence_type"] == "llm_proposed"


def test_unknown_course_implausible_rejected(monkeypatch):
    """Proves that non-academic queries are rejected safely."""
    def mock_evaluate(queries, client=None, **kwargs):
        return [
            {
                "query": "xyz123nonsense",
                "is_plausible": False,
                "is_ambiguous": False,
                "canonical_name": "Not Applicable",
                "course_id": "not_applicable",
                "category": "Invalid",
                "difficulty": "beginner",
                "description": "Nonsense query.",
                "clarification": None,
            }
        ]

    monkeypatch.setattr("backend.core_engine.analysis_service.evaluate_unknown_courses", mock_evaluate)

    with pytest.raises(CourseResolutionError, match="not recognized as a valid academic course"):
        generate_learning_path(["Python Programming", "xyz123nonsense"], use_ai=True)


def test_unknown_course_ambiguous_rejected_with_clarification(monkeypatch):
    """Proves that ambiguous unknown queries request clarification."""
    def mock_evaluate(queries, client=None, **kwargs):
        return [
            {
                "query": "General Coding",
                "is_plausible": True,
                "is_ambiguous": True,
                "canonical_name": "General Coding",
                "course_id": "general_coding",
                "category": "Programming",
                "difficulty": "beginner",
                "description": "Overly broad query.",
                "clarification": "Too broad. Please choose a specific language like Python, Java, or C.",
            }
        ]

    monkeypatch.setattr("backend.core_engine.analysis_service.evaluate_unknown_courses", mock_evaluate)

    with pytest.raises(CourseResolutionError, match="ambiguous: Too broad"):
        generate_learning_path(["General Coding"], use_ai=True)


def test_unknown_courses_do_not_mutate_courses_json(monkeypatch):
    """Proves that resolving an unknown course does not write to courses.json."""
    kb = get_default_knowledge_base()
    courses_before = len(kb.get_all_courses())
    prereqs_before = len(kb.get_prerequisites())

    def mock_evaluate(queries, client=None, **kwargs):
        return [
            {
                "query": "Cloud Native Architecture",
                "is_plausible": True,
                "is_ambiguous": False,
                "canonical_name": "Cloud Native Architecture",
                "course_id": "cloud_native_architecture",
                "category": "Cloud Computing",
                "difficulty": "advanced",
                "description": "Cloud native patterns.",
                "clarification": None,
            }
        ]

    def mock_proposals(*args, **kwargs):
        return []

    monkeypatch.setattr("backend.core_engine.analysis_service.evaluate_unknown_courses", mock_evaluate)
    monkeypatch.setattr("backend.core_engine.analysis_service.request_prerequisite_proposals", mock_proposals)

    generate_learning_path(["Cloud Native Architecture"], use_ai=True)

    assert len(kb.get_all_courses()) == courses_before
    assert len(kb.get_prerequisites()) == prereqs_before


def test_no_api_key_exposed_in_api_response():
    """Proves that no secret API key appears in any field of the API response."""
    payload = {
        "courses": ["Python Programming", "Data Structures"],
        "learning_goal": "Check security",
        "use_ai": False,
    }
    response = test_client.post("/api/v1/learning-path", json=payload)
    assert response.status_code == 200
    raw_text = response.text
    # Check that neither key prefixes nor env patterns leak
    assert "GEMINI_API_KEY" not in raw_text
    assert "AQ." not in raw_text



