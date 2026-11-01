import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.ai_engine.client import (
    AIAuthenticationError,
    AIConfigurationError,
    AIRateLimitError,
    AIResponseValidationError,
    AITimeoutError,
    ProposalList,
)
from backend.core_engine.analysis_service import (
    CourseResolutionError,
    CurricularConstraintError,
    CycleConflictError,
    generate_learning_path,
)
from backend.core_engine.main import app
from backend.knowledge_base.knowledge_base import get_default_knowledge_base

test_client = TestClient(app)


# ===========================================================================
# TEST A: Ambiguous Course Resolution (e.g., "English")
# ===========================================================================

def test_a1_ambiguous_course_resolved_via_context(monkeypatch):
    """Test A.1: Ambiguous query is contextually resolved by AI without early exit."""
    def mock_evaluate(queries, client=None, learning_goal=None, other_courses=None, **kwargs):
        assert "English" in queries
        assert learning_goal == "Natural Language Processing"
        assert "Machine Learning" in (other_courses or [])
        return [
            {
                "query": "English",
                "is_plausible": True,
                "is_ambiguous": False,
                "resolved_from_context": True,
                "canonical_name": "Computational Linguistics",
                "course_id": "computational_linguistics",
                "category": "Interdisciplinary",
                "difficulty": "intermediate",
                "description": "Linguistic foundations for natural language processing.",
                "clarification": None,
                "selected_candidate_id": None,
            }
        ]

    def mock_proposals(*args, **kwargs):
        return ProposalList([])

    monkeypatch.setattr("backend.core_engine.analysis_service.evaluate_unknown_courses", mock_evaluate)
    monkeypatch.setattr("backend.core_engine.analysis_service.request_prerequisite_proposals", mock_proposals)

    result = generate_learning_path(
        ["English", "Machine Learning"],
        learning_goal="Natural Language Processing",
        use_ai=True,
    )

    # "Computational Linguistics" is an alias in the KB for natural_language_processing
    # So the course resolves to natural_language_processing with ai_disambiguated provenance
    ordered_ids = [c["course_id"] for c in result["ordered_courses"]]
    assert "natural_language_processing" in ordered_ids
    assert "machine_learning" in ordered_ids
    assert result["ai_summary"]["requested"] is True
    assert result["ai_summary"]["unknown_courses_evaluated"] == 1
    assert result["ai_summary"]["course_resolution_status"] == "ai_disambiguated"


def test_a2_ambiguous_course_requests_clarification(monkeypatch):
    """Test A.2: Truly ambiguous query without sufficient context returns clarification request."""
    def mock_evaluate(queries, client=None, **kwargs):
        return [
            {
                "query": "English",
                "is_plausible": True,
                "is_ambiguous": True,
                "resolved_from_context": False,
                "canonical_name": "English Composition",
                "course_id": "english_composition",
                "category": "Humanities",
                "difficulty": "beginner",
                "description": "Composition and literature.",
                "clarification": "The query 'English' can refer to Composition, Literature, or Linguistics.",
                "selected_candidate_id": None,
            }
        ]

    monkeypatch.setattr("backend.core_engine.analysis_service.evaluate_unknown_courses", mock_evaluate)

    with pytest.raises(CourseResolutionError) as exc_info:
        generate_learning_path(["English"], learning_goal=None, use_ai=True)

    err = exc_info.value
    assert err.needs_clarification is True
    assert err.query == "English"
    assert "Composition, Literature, or Linguistics" in (err.clarification or "")
    assert "ambiguous" in str(err)


def test_a3_ambiguous_query_api_returns_structured_clarification(monkeypatch):
    """Test A.3: API endpoint returns HTTP 400 with structured clarification payload."""
    def mock_evaluate(queries, client=None, **kwargs):
        return [
            {
                "query": "English",
                "is_plausible": True,
                "is_ambiguous": True,
                "resolved_from_context": False,
                "canonical_name": "English",
                "course_id": "english",
                "category": "Humanities",
                "difficulty": "beginner",
                "description": "General English study.",
                "clarification": "Please specify English Composition, Literature, or ESL.",
                "selected_candidate_id": None,
            }
        ]

    monkeypatch.setattr("backend.core_engine.analysis_service.evaluate_unknown_courses", mock_evaluate)

    response = test_client.post(
        "/api/v1/learning-path",
        json={"courses": ["English"], "learning_goal": "General", "use_ai": True},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "course_resolution_error"
    assert data["detail"]["needs_clarification"] is True
    assert data["detail"]["query"] == "English"
    assert "English Composition" in data["detail"]["clarification"]


def test_a4_disambiguation_picks_curated_candidate(monkeypatch):
    """Test A.4: When AI selects a curated candidate, it resolves to that curated course."""
    def mock_evaluate(queries, client=None, **kwargs):
        return [
            {
                "query": "coding",
                "is_plausible": True,
                "is_ambiguous": False,
                "resolved_from_context": True,
                "canonical_name": "Programming Fundamentals",
                "course_id": "programming_fundamentals",
                "category": "Foundations",
                "difficulty": "beginner",
                "description": "Core programming.",
                "clarification": None,
                "selected_candidate_id": "programming_fundamentals",
            }
        ]

    monkeypatch.setattr("backend.core_engine.analysis_service.evaluate_unknown_courses", mock_evaluate)
    monkeypatch.setattr(
        "backend.core_engine.analysis_service.request_prerequisite_proposals",
        lambda *args, **kwargs: ProposalList([]),
    )

    result = generate_learning_path(["coding", "data_structures"], use_ai=True)
    resolved = next(c for c in result["selected_courses"] if c["course_id"] == "programming_fundamentals")
    assert resolved["is_curated"] is True
    assert resolved["provenance"] == "ai_disambiguated"
    assert result["ai_summary"]["course_resolution_status"] == "ai_disambiguated"


# ===========================================================================
# TEST B: Unknown Course Evaluation
# ===========================================================================

def test_b_unknown_course_evaluation_pipeline(monkeypatch):
    """Test B: Unknown course is evaluated, receives unique ID, and is ordered via DAA."""
    def mock_evaluate(queries, client=None, **kwargs):
        return [
            {
                "query": "Neuromorphic Computing",
                "is_plausible": True,
                "is_ambiguous": False,
                "resolved_from_context": False,
                "canonical_name": "Neuromorphic Computing",
                "course_id": "neuromorphic_computing",
                "category": "Novel Computing Architectures",
                "difficulty": "advanced",
                "description": "Brain-inspired spiking neural network architectures and hardware.",
                "clarification": None,
                "selected_candidate_id": None,
            }
        ]

    def mock_proposals(learning_goal, courses, existing_prerequisites=None, **kwargs):
        return ProposalList([
            {
                "source_course_id": "python_programming",
                "target_course_id": "neuromorphic_computing",
                "relationship_type": "recommended",
                "confidence": 0.85,
                "explanation": "Python is required for Brian2 and Nest spiking neural network simulations.",
            }
        ])

    monkeypatch.setattr("backend.core_engine.analysis_service.evaluate_unknown_courses", mock_evaluate)
    monkeypatch.setattr("backend.core_engine.analysis_service.request_prerequisite_proposals", mock_proposals)

    result = generate_learning_path(
        ["Neuromorphic Computing", "Python Programming"],
        learning_goal="Brain-Inspired Computing",
        use_ai=True,
    )

    ordered_ids = [c["course_id"] for c in result["ordered_courses"]]
    assert ordered_ids == ["python_programming", "neuromorphic_computing"]

    qc = next(c for c in result["selected_courses"] if c["course_id"] == "neuromorphic_computing")
    assert qc["source"] == "ai_inferred"
    assert qc["provenance"] == "ai_inferred_candidate"
    assert result["ai_summary"]["unknown_courses_evaluated"] == 1
    assert result["ai_summary"]["relationships_added"] == 1


# ===========================================================================
# TEST C: Known Courses with AI Enabled (Empty Proposals vs Failure)
# ===========================================================================

def test_c_known_courses_with_empty_proposals_distinguished_from_failure(monkeypatch):
    """Test C: Empty proposals from AI is reported as a successful request, not an API failure."""
    invoked = []

    def mock_proposals(learning_goal, courses, existing_prerequisites=None, **kwargs):
        invoked.append(True)
        return ProposalList([])

    monkeypatch.setattr("backend.core_engine.analysis_service.request_prerequisite_proposals", mock_proposals)

    result = generate_learning_path(
        ["data_structures", "algorithms"],
        learning_goal="Interview Prep",
        use_ai=True,
    )

    assert len(invoked) == 1
    assert result["ai_proposals_used"] is False
    assert result["ai_summary"]["proposal_request_status"] == "succeeded"
    assert result["ai_summary"]["proposals_received"] == 0
    assert result["ai_summary"]["relationships_added"] == 0
    assert any("no additional prerequisite relationships were proposed" in w for w in result["warnings"])
    assert "No additional prerequisite relationships were proposed" in result["ai_summary"]["message"]


# ===========================================================================
# TEST D: AI Proposes Valid Additional Relationship
# ===========================================================================

def test_d_ai_proposes_valid_additional_relationship(monkeypatch):
    """Test D: AI proposes an uncurated edge, incorporated into graph, affects topological order."""
    def mock_proposals(learning_goal, courses, existing_prerequisites=None, **kwargs):
        return ProposalList([
            {
                "source_course_id": "cybersecurity",
                "target_course_id": "cloud_computing",
                "relationship_type": "recommended",
                "confidence": 0.91,
                "explanation": "Security foundational principles apply directly to cloud configuration.",
            }
        ])

    monkeypatch.setattr("backend.core_engine.analysis_service.request_prerequisite_proposals", mock_proposals)

    result = generate_learning_path(
        ["cloud_computing", "cybersecurity"],
        learning_goal="DevSecOps",
        use_ai=True,
    )

    ordered_ids = [c["course_id"] for c in result["ordered_courses"]]
    # Cybersecurity must be scheduled before cloud_computing due to the AI proposed edge
    assert ordered_ids == ["cybersecurity", "cloud_computing"]
    assert result["ai_proposals_used"] is True
    assert result["ai_summary"]["proposal_request_status"] == "succeeded"
    assert result["ai_summary"]["proposals_accepted"] == 1
    assert result["ai_summary"]["relationships_added"] == 1

    ai_rel = next(r for r in result["prerequisites"] if r["is_ai_proposed"])
    assert ai_rel["source_course_id"] == "cybersecurity"
    assert ai_rel["target_course_id"] == "cloud_computing"
    assert ai_rel["confidence"] == 0.91


# ===========================================================================
# TEST E: AI Returns Invalid Relationships (Partial Acceptance & Rejection)
# ===========================================================================

def test_e1_ai_partial_acceptance_valid_accepted_invalid_rejected(monkeypatch):
    """Test E.1: When AI returns both a valid and an invalid proposal, valid is accepted, invalid rejected with warning."""
    def mock_proposals(learning_goal, courses, existing_prerequisites=None, **kwargs):
        # 1 valid proposal, 1 invalid proposal (unknown course ID)
        return ProposalList(
            [
                {
                    "source_course_id": "cybersecurity",
                    "target_course_id": "cloud_computing",
                    "relationship_type": "recommended",
                    "confidence": 0.88,
                    "explanation": "Cloud security context.",
                }
            ],
            validation_errors=["Proposal at index 1 references unknown source_course_id: 'unknown_course_xyz'"],
            total_received=2,
        )

    monkeypatch.setattr("backend.core_engine.analysis_service.request_prerequisite_proposals", mock_proposals)

    result = generate_learning_path(
        ["cloud_computing", "cybersecurity"],
        learning_goal="Security",
        use_ai=True,
    )

    assert result["ai_proposals_used"] is True
    assert result["ai_summary"]["proposals_received"] == 2
    assert result["ai_summary"]["proposals_accepted"] == 1
    assert result["ai_summary"]["proposals_rejected"] == 1
    assert any("AI proposal rejected during validation" in w for w in result["warnings"])


def test_e2_ai_cycle_creates_conflict_error(monkeypatch):
    """Test E.2: When AI proposes an edge that introduces a cycle, CycleConflictError is raised."""
    def mock_proposals(learning_goal, courses, existing_prerequisites=None, **kwargs):
        # programming_fundamentals -> data_structures is already in KB
        # Propose data_structures -> programming_fundamentals to create a cycle
        return ProposalList([
            {
                "source_course_id": "data_structures",
                "target_course_id": "programming_fundamentals",
                "relationship_type": "required",
                "confidence": 0.95,
                "explanation": "Cyclic proposal",
            }
        ])

    monkeypatch.setattr("backend.core_engine.analysis_service.request_prerequisite_proposals", mock_proposals)

    with pytest.raises(CycleConflictError) as exc_info:
        generate_learning_path(
            ["programming_fundamentals", "data_structures"],
            learning_goal="Cycle test",
            use_ai=True,
        )

    assert "Cyclic dependency detected" in str(exc_info.value)
    assert len(exc_info.value.cycle_path) >= 2


# ===========================================================================
# TEST F: AI Returns No Additional Relationships
# ===========================================================================

def test_f_ai_zero_proposals_reported_accurately(monkeypatch):
    """Test F: When Gemini completes and finds no additional edges, report accurately without claiming failure."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({"proposals": []})
    mock_client.models.generate_content.return_value = mock_response

    result = generate_learning_path(
        ["calculus", "linear_algebra"],
        learning_goal="Math Foundations",
        ai_client=mock_client,
        use_ai=True,
    )

    assert result["ai_proposals_used"] is False
    assert result["ai_summary"]["proposal_request_status"] == "succeeded"
    assert result["ai_summary"]["proposals_received"] == 0
    assert result["ai_summary"]["relationships_added"] == 0
    assert "No additional prerequisite relationships were proposed" in result["ai_summary"]["message"]


# ===========================================================================
# TEST G: AI Unavailable (Error Classification & Fallback)
# ===========================================================================

def test_g1_ai_timeout_fallback_to_curated(monkeypatch):
    """Test G.1: AI timeout falls back to curated relationships with diagnostic warning."""
    def mock_proposals(*args, **kwargs):
        raise AITimeoutError("Gemini API request timed out after 15.0s (15000ms).")

    monkeypatch.setattr("backend.core_engine.analysis_service.request_prerequisite_proposals", mock_proposals)

    result = generate_learning_path(
        ["programming_fundamentals", "data_structures"],
        use_ai=True,
        fallback_on_ai_failure=True,
    )

    assert result["ai_proposals_used"] is False
    assert result["ai_summary"]["proposal_request_status"] == "failed"
    assert any("AI proposals were unavailable" in w for w in result["warnings"])
    assert [c["course_id"] for c in result["ordered_courses"]] == ["programming_fundamentals", "data_structures"]


def test_g2_ai_rate_limit_without_fallback_raises(monkeypatch):
    """Test G.2: When fallback_on_ai_failure=False, rate limit exception is propagated."""
    def mock_proposals(*args, **kwargs):
        raise AIRateLimitError("Gemini API rate limit or quota exceeded.")

    monkeypatch.setattr("backend.core_engine.analysis_service.request_prerequisite_proposals", mock_proposals)

    with pytest.raises(AIRateLimitError):
        generate_learning_path(
            ["programming_fundamentals", "data_structures"],
            use_ai=True,
            fallback_on_ai_failure=False,
        )


def test_g3_ai_authentication_failure(monkeypatch):
    """Test G.3: Authentication failure with fallback produces curated path and accurate warning."""
    def mock_proposals(*args, **kwargs):
        raise AIAuthenticationError("Gemini API authentication failed: invalid or unauthorized API credentials.")

    monkeypatch.setattr("backend.core_engine.analysis_service.request_prerequisite_proposals", mock_proposals)

    result = generate_learning_path(
        ["linear_algebra", "machine_learning"],
        use_ai=True,
        fallback_on_ai_failure=True,
    )

    assert result["ai_proposals_used"] is False
    assert result["ai_summary"]["proposal_request_status"] == "failed"
    assert any("authentication failed" in w for w in result["warnings"])


# ===========================================================================
# TEST H: AI Disabled
# ===========================================================================

def test_h_ai_disabled_produces_curated_only():
    """Test H: When use_ai=False, AI is never invoked and ai_summary reflects disabled state."""
    result = generate_learning_path(
        ["linear_algebra", "machine_learning"],
        learning_goal="Math & ML",
        use_ai=False,
    )

    assert result["ai_proposals_used"] is False
    assert result["ai_summary"]["requested"] is False
    assert result["ai_summary"]["proposal_request_status"] == "disabled"
    assert result["ai_summary"]["relationships_added"] == 0
    assert any("AI assistance was disabled" in w for w in result["warnings"])


# ===========================================================================
# TEST I: Scheduling Correctness & Constraints
# ===========================================================================

def test_i_scheduling_and_wave_constraints():
    """Test I: Scheduling respects prerequisites and capacity constraints."""
    result = generate_learning_path(
        ["programming_fundamentals", "data_structures", "algorithms", "operating_systems"],
        use_ai=False,
        max_courses_per_semester=2,
    )

    # All semesters must obey the max 2 courses limit
    for s in result["semesters"]:
        assert len(s["courses"]) <= 2

    # Prerequisite verification across semesters
    sem_of_course = {}
    for s in result["semesters"]:
        for c in s["courses"]:
            sem_of_course[c["course_id"]] = s["semester_number"]

    # In KB: programming_fundamentals -> data_structures -> design_and_analysis_of_algorithms
    assert sem_of_course["programming_fundamentals"] < sem_of_course["data_structures"]
    assert sem_of_course["data_structures"] < sem_of_course["design_and_analysis_of_algorithms"]
