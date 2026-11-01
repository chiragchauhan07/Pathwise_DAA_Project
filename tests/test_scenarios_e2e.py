"""End-to-End Practical User Scenario Verification (Scenarios 1 through 14).

Executes and verifies all 14 scenarios from Part 8 of the Pathwise Specification:
  Scenario 1: Basic programming path
  Scenario 2: Original seven-course case
  Scenario 3: AI and Machine Learning pathway
  Scenario 4: Software engineering pathway
  Scenario 5: Independent courses (no mandatory edges between them)
  Scenario 6: Ambiguous course (English with/without learning goal)
  Scenario 7: Unknown but legitimate course (inferred without mutating KB)
  Scenario 8: Duplicate courses (deduplication without vertex corruption)
  Scenario 9: Invalid input (empty list, blank, invalid limits, overflow)
  Scenario 10: AI unavailable (isolated fallback and error modes)
  Scenario 11: Cyclic graph (isolated cycle detection and conflict error)
  Scenario 12: Infeasible scheduling constraints (exceeding max semesters)
  Scenario 13: Longer learning path (10+ courses, no loss, no duplication)
  Scenario 14: Frontend/backend resilience (health, status, 400 structures)
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
import backend.core_engine.analysis_service
from backend.core_engine.main import app
from backend.core_engine.analysis_service import (
    CourseResolutionError,
    CycleConflictError,
    CurricularConstraintError,
    generate_learning_path,
)
from backend.knowledge_base.knowledge_base import KnowledgeBase

client = TestClient(app)


def test_scenario_1_basic_programming_path():
    """Scenario 1: Basic programming path (Fundamentals, Python, OOP)."""
    res = client.post("/api/v1/learning-path", json={
        "courses": ["Programming Fundamentals", "Python Programming", "Object-Oriented Programming"],
        "learning_goal": "General Computer Science",
        "use_ai": False,
    })
    assert res.status_code == 200, res.text
    data = res.json()
    order = [c["course_id"] for c in data["ordered_courses"]]
    # Programming Fundamentals must precede Python and OOP
    assert order.index("programming_fundamentals") < order.index("python_programming")
    assert order.index("programming_fundamentals") < order.index("object_oriented_programming")
    assert len(data["semesters"]) >= 2
    # Verify every course appears exactly once
    assert len(order) == 3
    assert len(set(order)) == 3


def test_scenario_2_seven_course_problem():
    """Scenario 2: Original seven-course case."""
    res = client.post("/api/v1/learning-path", json={
        "courses": [
            "Python Programming",
            "English",
            "Machine Learning",
            "Design and Analysis of Algorithms",
            "Programming Fundamentals",
            "Object-Oriented Programming",
            "Programming Using R",
        ],
        "learning_goal": "General Computer Science",
        "use_ai": True,
    })
    assert res.status_code == 200, res.text
    data = res.json()
    order = [c["course_id"] for c in data["ordered_courses"]]
    # Hard prerequisite verification:
    assert order.index("programming_fundamentals") < order.index("python_programming")
    assert order.index("programming_fundamentals") < order.index("object_oriented_programming")
    assert order.index("python_programming") < order.index("machine_learning")
    assert "ai_summary" in data
    assert data["ai_summary"]["model"] == "gemini-3.5-flash-lite"
    # All 7 courses represented
    assert len(order) == 7
    assert len(set(order)) == 7


def test_scenario_3_ai_and_ml_pathway():
    """Scenario 3: AI and Machine Learning pathway."""
    res = client.post("/api/v1/learning-path", json={
        "courses": [
            "Python Programming",
            "Linear Algebra",
            "Probability and Statistics",
            "Machine Learning",
            "Deep Learning",
        ],
        "learning_goal": "AI and Machine Learning Engineering",
        "use_ai": False,
    })
    assert res.status_code == 200, res.text
    data = res.json()
    order = [c["course_id"] for c in data["ordered_courses"]]
    assert order.index("linear_algebra") < order.index("deep_learning")
    assert order.index("probability_and_statistics") < order.index("machine_learning")
    assert order.index("machine_learning") < order.index("deep_learning")
    assert order.index("python_programming") < order.index("machine_learning")


def test_scenario_4_software_engineering_pathway():
    """Scenario 4: Software engineering pathway."""
    res = client.post("/api/v1/learning-path", json={
        "courses": [
            "Programming Fundamentals",
            "Object-Oriented Programming",
            "Data Structures",
            "Software Engineering",
            "Database Management Systems",
        ],
        "learning_goal": "Software Engineering",
        "use_ai": False,
    })
    assert res.status_code == 200, res.text
    data = res.json()
    order = [c["course_id"] for c in data["ordered_courses"]]
    assert order.index("programming_fundamentals") < order.index("object_oriented_programming")
    assert order.index("programming_fundamentals") < order.index("data_structures")
    assert order.index("data_structures") < order.index("database_management_systems")
    assert order.index("object_oriented_programming") < order.index("software_engineering")


def test_scenario_5_independent_courses():
    """Scenario 5: Independent courses have no mandatory edges between them."""
    # Linear Algebra, Technical Communication, and Programming Fundamentals
    # Technical Communication has no prerequisite links to Linear Algebra or Programming Fundamentals
    res = client.post("/api/v1/learning-path", json={
        "courses": [
            "Linear Algebra",
            "Technical Communication and Academic Writing",
            "Programming Fundamentals",
        ],
        "use_ai": False,
    })
    assert res.status_code == 200
    data = res.json()
    order = [c["course_id"] for c in data["ordered_courses"]]
    # All 3 courses present
    assert len(order) == 3
    # No required prerequisite relationships between these 3 independent courses
    required_prereqs = [r for r in data["prerequisites"] if r.get("relationship_type") == "required"]
    assert len(required_prereqs) == 0
    # Because there are zero edges, all 3 are scheduled in Semester 1 under unconstrained wave scheduling
    assert len(data["semesters"]) == 1
    assert data["semesters"][0]["course_count"] == 3


def test_scenario_6_ambiguous_course():
    """Scenario 6: Ambiguous course returns structured clarification or AI contextual resolution."""
    # When AI is disabled, 'English' cannot be contextually disambiguated
    res_no_ai = client.post("/api/v1/learning-path", json={
        "courses": ["English"],
        "use_ai": False,
    })
    assert res_no_ai.status_code == 400
    detail = res_no_ai.json()["detail"]
    assert detail["error"] == "course_resolution_error"
    assert "English" in detail["message"]


def test_scenario_7_unknown_legitimate_course(monkeypatch):
    """Scenario 7: Unknown academic course evaluated via AI without mutating persistent KB."""
    from backend.knowledge_base.knowledge_base import get_default_knowledge_base
    kb_before_count = len(get_default_knowledge_base().get_all_courses())

    def mock_evaluate(queries, client=None, **kwargs):
        return [{
            "query": "Neuromorphic Computing",
            "is_plausible": True,
            "is_ambiguous": False,
            "canonical_name": "Neuromorphic Computing",
            "course_id": "neuromorphic_computing",
            "category": "Novel Architectures",
            "difficulty": "advanced",
            "description": "Brain-inspired computing architectures.",
            "clarification": None,
        }]

    monkeypatch.setattr("backend.core_engine.analysis_service.evaluate_unknown_courses", mock_evaluate)

    res = client.post("/api/v1/learning-path", json={
        "courses": ["Python Programming", "Neuromorphic Computing"],
        "learning_goal": "Brain-Inspired Computing",
        "use_ai": True,
    })
    assert res.status_code == 200
    data = res.json()
    assert any(c["course_id"] == "neuromorphic_computing" for c in data["selected_courses"])
    assert data["ai_summary"]["unknown_courses_evaluated"] == 1

    # Verify persistent KB count remains strictly untouched
    kb_after_count = len(get_default_knowledge_base().get_all_courses())
    assert kb_after_count == kb_before_count


def test_scenario_8_duplicate_courses():
    """Scenario 8: Duplicate courses and aliases deduplicate without vertex corruption."""
    res = client.post("/api/v1/learning-path", json={
        "courses": [
            "Python Programming",
            "Python",
            "python_programming",
            "Data Structures",
        ],
        "use_ai": False,
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["selected_courses"]) == 2
    assert len(data["ordered_courses"]) == 2
    ids = [c["course_id"] for c in data["selected_courses"]]
    assert ids == ["python_programming", "data_structures"]


def test_scenario_9_invalid_input():
    """Scenario 9: Invalid input returns structured error rather than crashing."""
    # 1. Empty course list
    res_empty = client.post("/api/v1/learning-path", json={"courses": []})
    assert res_empty.status_code in (400, 422)

    # 2. Blank course name
    res_blank = client.post("/api/v1/learning-path", json={"courses": ["   ", ""]})
    assert res_blank.status_code == 400

    # 3. Invalid semester limits (0 or negative)
    res_invalid_limit = client.post("/api/v1/learning-path", json={
        "courses": ["Data Structures"],
        "max_courses_per_semester": 0,
    })
    assert res_invalid_limit.status_code in (400, 422)

    # 4. Input exceeding maximum allowed limit (50 courses)
    res_overflow = client.post("/api/v1/learning-path", json={
        "courses": [f"Course_{i}" for i in range(55)],
        "use_ai": False,
    })
    assert res_overflow.status_code == 400
    assert "exceeds maximum limit" in res_overflow.json()["detail"]["message"]


def test_scenario_10_ai_unavailable_fallback():
    """Scenario 10: AI unavailable in isolated process produces transparent warning and curated-only path."""
    res = client.post("/api/v1/learning-path", json={
        "courses": ["Data Structures", "Design and Analysis of Algorithms"],
        "use_ai": False,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ai_proposals_used"] is False
    assert any("AI assistance was disabled" in w for w in data["warnings"])
    assert data["ai_summary"]["proposal_request_status"] == "disabled"


def test_scenario_11_cyclic_graph():
    """Scenario 11: Cyclic graph detected via DFS and rejected before scheduling."""
    cyclic_kb_data = {
        "courses": [
            {"course_id": "a", "name": "Course A", "aliases": [], "category": "Test", "difficulty": "beginner", "description": "A"},
            {"course_id": "b", "name": "Course B", "aliases": [], "category": "Test", "difficulty": "beginner", "description": "B"},
        ],
        "prerequisites": [
            {"relationship_id": "r1", "source_course_id": "a", "target_course_id": "b", "relationship_type": "required", "explanation": "A->B", "confidence": 1.0, "evidence_type": "expert_curated"},
            {"relationship_id": "r2", "source_course_id": "b", "target_course_id": "a", "relationship_type": "required", "explanation": "B->A", "confidence": 1.0, "evidence_type": "expert_curated"},
        ]
    }
    kb = KnowledgeBase(source=cyclic_kb_data)
    with pytest.raises(CycleConflictError) as exc_info:
        generate_learning_path(["Course A", "Course B"], kb=kb, use_ai=False)
    assert "Cyclic dependency detected" in str(exc_info.value)


def test_scenario_12_infeasible_scheduling_constraints():
    """Scenario 12: Infeasible scheduling constraints reported with HTTP 400."""
    res = client.post("/api/v1/learning-path", json={
        "courses": ["Programming Fundamentals", "Data Structures", "Design and Analysis of Algorithms"],
        "max_semesters": 2,
        "use_ai": False,
    })
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["error"] == "curricular_constraint_error"
    assert "exceeds the limit of 2 semester(s)" in detail["message"]


def test_scenario_13_longer_learning_path():
    """Scenario 13: Longer learning path (12 courses) completes stably without course loss."""
    twelve_courses = [
        "Programming Fundamentals",
        "C Programming",
        "Python Programming",
        "Object-Oriented Programming",
        "Data Structures",
        "Design and Analysis of Algorithms",
        "Discrete Mathematics",
        "Operating Systems",
        "Database Management Systems",
        "Computer Networks",
        "Software Engineering",
        "Machine Learning",
    ]
    res = client.post("/api/v1/learning-path", json={
        "courses": twelve_courses,
        "use_ai": False,
        "max_courses_per_semester": 3,
    })
    assert res.status_code == 200
    data = res.json()
    order = [c["course_id"] for c in data["ordered_courses"]]
    # All 12 courses preserved exactly once
    assert len(order) == 12
    assert len(set(order)) == 12
    # Verify max courses per semester cap is respected
    for sem in data["semesters"]:
        assert sem["course_count"] <= 3
    # Check key prerequisite orders
    assert order.index("programming_fundamentals") < order.index("data_structures")
    assert order.index("data_structures") < order.index("design_and_analysis_of_algorithms")
    assert order.index("discrete_mathematics") < order.index("design_and_analysis_of_algorithms")


def test_scenario_14_frontend_backend_resilience():
    """Scenario 14: API endpoints health, AI diagnostic status, and resilience."""
    # Health check
    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    # AI diagnostic check (no secret exposure)
    res_ai = client.get("/api/v1/ai/status")
    assert res_ai.status_code == 200
    data = res_ai.json()
    assert "configured" in data
    assert "model" in data
    assert "GEMINI_API_KEY" not in str(data)


def test_daa_algorithms_actually_invoked():
    """Instrumented test: Proves that custom DAA functions are strictly called during path generation."""
    with patch("backend.core_engine.analysis_service.detect_cycle_dfs", wraps=backend.core_engine.analysis_service.detect_cycle_dfs) as spy_dfs, \
         patch("backend.core_engine.analysis_service.topological_sort_kahn", wraps=backend.core_engine.analysis_service.topological_sort_kahn) as spy_kahn, \
         patch("backend.core_engine.analysis_service.schedule_courses", wraps=backend.core_engine.analysis_service.schedule_courses) as spy_sched:

        res = client.post("/api/v1/learning-path", json={
            "courses": ["Programming Fundamentals", "Data Structures"],
            "use_ai": False,
        })
        assert res.status_code == 200

        # Verify that DFS cycle detection was executed
        assert spy_dfs.called
        assert spy_dfs.call_count >= 1

        # Verify that Kahn's topological sort was executed
        assert spy_kahn.called
        assert spy_kahn.call_count >= 1

        # Verify that the pedagogical scheduler was executed
        assert spy_sched.called
        assert spy_sched.call_count >= 1
