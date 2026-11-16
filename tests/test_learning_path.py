import pytest
from fastapi.testclient import TestClient

from backend.core_engine.analysis_service import (
    CourseResolutionError,
    CurricularConstraintError,
    CycleConflictError,
    generate_learning_path,
)
from backend.core_engine.main import app
from backend.knowledge_base.knowledge_base import get_default_knowledge_base, KnowledgeBase

test_client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit / Service Integration Tests: generate_learning_path (Pure DAA Engine)
# ---------------------------------------------------------------------------


def test_generate_learning_path_empty_input():
    with pytest.raises(CourseResolutionError, match="Course list cannot be empty"):
        generate_learning_path([])


def test_generate_learning_path_unknown_course():
    with pytest.raises(CourseResolutionError, match="is not recognized in the knowledge base catalog"):
        generate_learning_path(["Python Programming", "Quantum Time Travel 101"])


def test_generate_learning_path_course_normalization_and_alias():
    # "python" -> python_programming, "ml" -> machine_learning
    result = generate_learning_path(
        ["ml", "python"],
        learning_goal="AI/ML Track",
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
    )
    ordered_ids = [c["course_id"] for c in result["ordered_courses"]]
    assert ordered_ids == ["programming_fundamentals", "data_structures", "design_and_analysis_of_algorithms"]

    # Verify that every prerequisite appears before its dependent
    index_map = {cid: i for i, cid in enumerate(ordered_ids)}
    for prereq in result["prerequisites"]:
        src = prereq["source_course_id"]
        tgt = prereq["target_course_id"]
        assert index_map[src] < index_map[tgt]


def test_generate_learning_path_multiple_prerequisites():
    # Machine Learning requires python_programming, linear_algebra, probability_and_statistics
    result = generate_learning_path(
        ["machine_learning", "python_programming", "linear_algebra", "probability_and_statistics"],
        learning_goal="Machine Learning Foundation",
    )
    ordered_ids = [c["course_id"] for c in result["ordered_courses"]]
    ml_idx = ordered_ids.index("machine_learning")
    assert ordered_ids.index("python_programming") < ml_idx
    assert ordered_ids.index("linear_algebra") < ml_idx
    assert ordered_ids.index("probability_and_statistics") < ml_idx


def test_generate_learning_path_cycle_detection():
    cyclic_kb_data = {
        "courses": [
            {"course_id": "c1", "name": "Course 1", "aliases": [], "category": "Test", "difficulty": "introductory", "description": "1"},
            {"course_id": "c2", "name": "Course 2", "aliases": [], "category": "Test", "difficulty": "introductory", "description": "2"},
        ],
        "prerequisites": [
            {"relationship_id": "r1", "source_course_id": "c1", "target_course_id": "c2", "relationship_type": "required", "explanation": "1->2", "confidence": 1.0, "evidence_type": "expert_curated"},
            {"relationship_id": "r2", "source_course_id": "c2", "target_course_id": "c1", "relationship_type": "required", "explanation": "2->1", "confidence": 1.0, "evidence_type": "expert_curated"},
        ]
    }
    kb = KnowledgeBase(source=cyclic_kb_data)
    with pytest.raises(CycleConflictError) as exc_info:
        generate_learning_path(["Course 1", "Course 2"], kb=kb)
    assert "Cyclic dependency detected" in str(exc_info.value)
    assert exc_info.value.cycle_path is not None
    assert len(exc_info.value.cycle_path) >= 2


def test_generate_learning_path_deterministic_tie_breaking():
    # Two independent courses with no prerequisites: Technical Communication vs Discrete Math
    # Kahn's algorithm min-heap tie breaker orders lexicographically by course name
    result1 = generate_learning_path(["Technical Communication and Academic Writing", "Discrete Mathematics"])
    result2 = generate_learning_path(["Discrete Mathematics", "Technical Communication and Academic Writing"])
    order1 = [c["course_id"] for c in result1["ordered_courses"]]
    order2 = [c["course_id"] for c in result2["ordered_courses"]]
    assert order1 == order2
    # Discrete Mathematics comes before Technical Communication alphabetically
    assert order1 == ["discrete_mathematics", "technical_communication_and_academic_writing"]


def test_generate_learning_path_semester_scheduling_unconstrained():
    # Chain: Fundamentals -> Data Structures -> DAA
    result = generate_learning_path(
        ["programming_fundamentals", "data_structures", "design_and_analysis_of_algorithms"]
    )
    semesters = result["semesters"]
    assert len(semesters) == 3
    assert semesters[0]["courses"][0]["course_id"] == "programming_fundamentals"
    assert semesters[1]["courses"][0]["course_id"] == "data_structures"
    assert semesters[2]["courses"][0]["course_id"] == "design_and_analysis_of_algorithms"


def test_generate_learning_path_semester_scheduling_with_cap():
    # 4 independent courses with max 2 courses per semester -> 2 semesters
    result = generate_learning_path(
        ["linear_algebra", "discrete_mathematics", "calculus_i", "technical_communication_and_academic_writing"],
        max_courses_per_semester=2,
    )
    semesters = result["semesters"]
    assert len(semesters) == 2
    for sem in semesters:
        assert sem["course_count"] <= 2


def test_generate_learning_path_max_semesters_constraint():
    with pytest.raises(CurricularConstraintError) as exc_info:
        generate_learning_path(
            ["programming_fundamentals", "data_structures", "design_and_analysis_of_algorithms"],
            max_semesters=2,
        )
    assert "exceeds the limit of 2 semester(s)" in str(exc_info.value)


def test_generate_learning_path_course_deduplication():
    result = generate_learning_path(
        ["Python Programming", "python", "python_programming", "Data Structures"]
    )
    assert len(result["selected_courses"]) == 2
    assert len(result["ordered_courses"]) == 2
    # Lexicographical min-heap tie breaking places data_structures before python_programming
    assert [c["course_id"] for c in result["ordered_courses"]] == ["data_structures", "python_programming"]


def test_api_endpoint_learning_path():
    response = test_client.post("/api/v1/learning-path", json={
        "courses": ["Programming Fundamentals", "Data Structures", "Design and Analysis of Algorithms"],
        "learning_goal": "Algorithm Mastery",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["total_courses"] == 3
    assert data["total_prerequisites"] >= 2
    assert data["total_semesters"] == 3
    assert data["ai_proposals_used"] is False
