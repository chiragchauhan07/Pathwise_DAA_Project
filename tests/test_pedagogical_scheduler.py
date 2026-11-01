"""Tests for Level 7: Advanced Pedagogical Optimization and Curricular Constraints.

Verifies:
  1. Natural wave-based DAG layering.
  2. Prerequisite correctness (required prereqs in strictly earlier semesters).
  3. Soft dependency handling (recommended/optional allow concurrent semesters, but preserve precedence).
  4. Workload capacity constraints (max_courses_per_semester).
  5. Critical path prioritization under capacity limits.
  6. Difficulty progression smoothing (beginner -> intermediate -> advanced).
  7. Feasibility and deadline checking (max_semesters).
  8. Mathematical schedule verification.
  9. End-to-end API integration and backward compatibility.
"""

import pytest
from fastapi.testclient import TestClient

from backend.core_engine.analysis_service import generate_learning_path
from backend.core_engine.main import app
from backend.daa_engine.scheduler import (
    CurricularConstraintError,
    schedule_courses,
    verify_semester_schedule,
)


@pytest.fixture
def client():
    return TestClient(app)


# -----------------------------------------------------------------------------
# Unit Tests for schedule_courses and verify_semester_schedule
# -----------------------------------------------------------------------------

def test_empty_courses_scheduling():
    result = schedule_courses([], [])
    assert result["semesters"] == []
    assert result["total_semesters"] == 0
    assert result["ordered_courses"] == []
    assert verify_semester_schedule(result, []) is True


def test_independent_courses_share_first_wave():
    # 3 independent courses with no prerequisites
    courses = [
        {"course_id": "c1", "difficulty": "intermediate"},
        {"course_id": "c2", "difficulty": "beginner"},
        {"course_id": "c3", "difficulty": "advanced"},
    ]
    result = schedule_courses(courses, [])
    assert result["total_semesters"] == 1
    assert len(result["semesters"]) == 1

    sem1 = result["semesters"][0]
    assert sem1["semester_number"] == 1
    assert sem1["course_count"] == 3

    # Difficulty progression within Wave 1: beginner (c2), intermediate (c1), advanced (c3)
    cids = [c["course_id"] for c in sem1["courses"]]
    assert cids == ["c2", "c1", "c3"]
    assert verify_semester_schedule(result, []) is True


def test_linear_required_chain_requires_sequential_waves():
    # c1 -> c2 -> c3 (required)
    courses = [
        {"course_id": "c1", "difficulty": "beginner"},
        {"course_id": "c2", "difficulty": "intermediate"},
        {"course_id": "c3", "difficulty": "advanced"},
    ]
    prereqs = [
        {"source_course_id": "c1", "target_course_id": "c2", "relationship_type": "required"},
        {"source_course_id": "c2", "target_course_id": "c3", "relationship_type": "required"},
    ]
    result = schedule_courses(courses, prereqs)
    assert result["total_semesters"] == 3
    assert len(result["semesters"]) == 3

    assert [c["course_id"] for c in result["semesters"][0]["courses"]] == ["c1"]
    assert [c["course_id"] for c in result["semesters"][1]["courses"]] == ["c2"]
    assert [c["course_id"] for c in result["semesters"][2]["courses"]] == ["c3"]

    assert result["course_to_semester"]["c1"] < result["course_to_semester"]["c2"]
    assert result["course_to_semester"]["c2"] < result["course_to_semester"]["c3"]
    assert verify_semester_schedule(result, prereqs) is True


def test_multiple_prerequisites_diamond_graph():
    # Diamond: root -> left, root -> right; left -> sink, right -> sink (all required)
    courses = [
        {"course_id": "root", "difficulty": "beginner"},
        {"course_id": "left", "difficulty": "intermediate"},
        {"course_id": "right", "difficulty": "intermediate"},
        {"course_id": "sink", "difficulty": "advanced"},
    ]
    prereqs = [
        {"source_course_id": "root", "target_course_id": "left", "relationship_type": "required"},
        {"source_course_id": "root", "target_course_id": "right", "relationship_type": "required"},
        {"source_course_id": "left", "target_course_id": "sink", "relationship_type": "required"},
        {"source_course_id": "right", "target_course_id": "sink", "relationship_type": "required"},
    ]
    result = schedule_courses(courses, prereqs)
    assert result["total_semesters"] == 3

    assert [c["course_id"] for c in result["semesters"][0]["courses"]] == ["root"]
    assert set(c["course_id"] for c in result["semesters"][1]["courses"]) == {"left", "right"}
    assert [c["course_id"] for c in result["semesters"][2]["courses"]] == ["sink"]
    assert verify_semester_schedule(result, prereqs) is True


def test_recommended_prerequisite_allows_concurrent_wave():
    # c1 -> c2 is recommended, not required
    courses = [
        {"course_id": "c1", "difficulty": "beginner"},
        {"course_id": "c2", "difficulty": "intermediate"},
    ]
    prereqs = [
        {"source_course_id": "c1", "target_course_id": "c2", "relationship_type": "recommended"},
    ]
    # Without capacity limits, both can be taken in Wave 1
    result = schedule_courses(courses, prereqs)
    assert result["total_semesters"] == 1
    sem1 = result["semesters"][0]
    assert sem1["course_count"] == 2
    # But within the wave, c1 strictly precedes c2
    cids = [c["course_id"] for c in sem1["courses"]]
    assert cids == ["c1", "c2"]
    assert verify_semester_schedule(result, prereqs) is True


def test_optional_prerequisite_does_not_force_separate_waves():
    courses = [
        {"course_id": "c1", "difficulty": "intermediate"},
        {"course_id": "c2", "difficulty": "advanced"},
    ]
    prereqs = [
        {"source_course_id": "c1", "target_course_id": "c2", "relationship_type": "optional"},
    ]
    result = schedule_courses(courses, prereqs)
    assert result["total_semesters"] == 1
    assert [c["course_id"] for c in result["semesters"][0]["courses"]] == ["c1", "c2"]
    assert verify_semester_schedule(result, prereqs) is True


def test_recommended_prerequisite_respected_when_split_by_capacity():
    # c1 -> c2 recommended; capacity limit max_courses_per_semester = 1
    courses = [
        {"course_id": "c1", "difficulty": "intermediate"},
        {"course_id": "c2", "difficulty": "intermediate"},
    ]
    prereqs = [
        {"source_course_id": "c1", "target_course_id": "c2", "relationship_type": "recommended"},
    ]
    result = schedule_courses(courses, prereqs, max_courses_per_semester=1)
    assert result["total_semesters"] == 2
    assert [c["course_id"] for c in result["semesters"][0]["courses"]] == ["c1"]
    assert [c["course_id"] for c in result["semesters"][1]["courses"]] == ["c2"]
    assert verify_semester_schedule(result, prereqs, max_courses_per_semester=1) is True


def test_workload_capacity_partitions_independent_courses():
    # 4 independent courses with max_courses_per_semester = 2 -> exactly 2 semesters of 2 courses
    courses = [
        {"course_id": f"c_{i}", "difficulty": "intermediate"} for i in range(4)
    ]
    result = schedule_courses(courses, [], max_courses_per_semester=2)
    assert result["total_semesters"] == 2
    assert result["semesters"][0]["course_count"] == 2
    assert result["semesters"][1]["course_count"] == 2
    assert verify_semester_schedule(result, [], max_courses_per_semester=2) is True


def test_critical_path_prioritization_under_capacity():
    # c1 is bottleneck for long required chain: c1 -> c2 -> c3
    # c_indep has no dependents
    # With max_courses_per_semester = 1: c1 must be scheduled first to avoid delaying c2 and c3
    courses = [
        {"course_id": "c_indep", "difficulty": "beginner"},
        {"course_id": "c1", "difficulty": "beginner"},
        {"course_id": "c2", "difficulty": "intermediate"},
        {"course_id": "c3", "difficulty": "advanced"},
    ]
    prereqs = [
        {"source_course_id": "c1", "target_course_id": "c2", "relationship_type": "required"},
        {"source_course_id": "c2", "target_course_id": "c3", "relationship_type": "required"},
    ]
    result = schedule_courses(courses, prereqs, max_courses_per_semester=1)
    assert result["total_semesters"] == 4
    # c1 has critical depth 3, c_indep has depth 1 -> c1 must be scheduled in semester 1
    assert result["semesters"][0]["courses"][0]["course_id"] == "c1"
    assert verify_semester_schedule(result, prereqs, max_courses_per_semester=1) is True


def test_max_semesters_constraint_satisfied():
    courses = [
        {"course_id": "c1", "difficulty": "beginner"},
        {"course_id": "c2", "difficulty": "intermediate"},
    ]
    prereqs = [
        {"source_course_id": "c1", "target_course_id": "c2", "relationship_type": "required"},
    ]
    # Chain length 2 fits in max_semesters = 2
    result = schedule_courses(courses, prereqs, max_semesters=2)
    assert result["total_semesters"] == 2
    assert verify_semester_schedule(result, prereqs, max_semesters=2) is True


def test_max_semesters_violation_by_required_prerequisite_depth():
    courses = [
        {"course_id": "c1", "difficulty": "beginner"},
        {"course_id": "c2", "difficulty": "intermediate"},
        {"course_id": "c3", "difficulty": "advanced"},
    ]
    prereqs = [
        {"source_course_id": "c1", "target_course_id": "c2", "relationship_type": "required"},
        {"source_course_id": "c2", "target_course_id": "c3", "relationship_type": "required"},
    ]
    # Chain length 3 cannot fit in max_semesters = 2
    with pytest.raises(CurricularConstraintError) as exc_info:
        schedule_courses(courses, prereqs, max_semesters=2)

    assert exc_info.value.required_semesters == 3
    assert exc_info.value.max_semesters == 2
    assert "requires at least 3 semesters" in str(exc_info.value)
    assert "c1 -> c2 -> c3" in str(exc_info.value)


def test_max_semesters_violation_by_capacity_limit():
    courses = [{"course_id": f"c_{i}", "difficulty": "intermediate"} for i in range(5)]
    # 5 courses with capacity 2 requires at least ceil(5/2) = 3 semesters
    with pytest.raises(CurricularConstraintError) as exc_info:
        schedule_courses(courses, [], max_courses_per_semester=2, max_semesters=2)

    assert exc_info.value.required_semesters == 3
    assert exc_info.value.max_semesters == 2
    assert "requires at least 3 semesters" in str(exc_info.value)


def test_invalid_constraint_types_and_values():
    courses = [{"course_id": "c1", "difficulty": "beginner"}]

    with pytest.raises(CurricularConstraintError):
        schedule_courses(courses, [], max_courses_per_semester=0)

    with pytest.raises(CurricularConstraintError):
        schedule_courses(courses, [], max_courses_per_semester=-2)

    with pytest.raises(CurricularConstraintError):
        schedule_courses(courses, [], max_courses_per_semester=True)  # bool rejected

    with pytest.raises(CurricularConstraintError):
        schedule_courses(courses, [], max_semesters=0)

    with pytest.raises(CurricularConstraintError):
        schedule_courses(courses, [], max_semesters=-1)


def test_verifier_catches_invalid_schedules():
    courses = [
        {"course_id": "c1", "difficulty": "beginner", "semester": 1},
        {"course_id": "c2", "difficulty": "advanced", "semester": 1},
    ]
    prereqs = [
        {"source_course_id": "c1", "target_course_id": "c2", "relationship_type": "required"},
    ]
    # Fabricate an invalid schedule where required prereq is in same semester
    bad_schedule = {
        "semesters": [
            {
                "semester_number": 1,
                "courses": courses,
                "course_count": 2,
            }
        ],
        "course_to_semester": {"c1": 1, "c2": 1},
        "ordered_courses": courses,
    }
    # Fails because c1 and c2 are in same semester but c1 is a required prerequisite for c2
    assert verify_semester_schedule(bad_schedule, prereqs) is False

    # Capacity violation
    bad_cap_schedule = {
        "semesters": [
            {
                "semester_number": 1,
                "courses": courses,
                "course_count": 2,
            }
        ],
        "course_to_semester": {"c1": 1, "c2": 1},
        "ordered_courses": courses,
    }
    assert verify_semester_schedule(bad_cap_schedule, [], max_courses_per_semester=1) is False


def test_soft_prerequisite_not_inverted_by_critical_path_recommended():
    """Reproduction case for soft prerequisite scheduling under capacity limits.

    Courses: S, T, A, B
    Dependencies:
      - S -> T (recommended)
      - T -> A (required)
      - A -> B (required)
    Constraint: max_courses_per_semester = 1

    Bug: Critical path previously prioritized T (depth 3) over S (depth 1),
    placing T before S, which produced an invalid schedule.
    Fix: S must be scheduled in an earlier semester than T, producing:
      Sem 1: S, Sem 2: T, Sem 3: A, Sem 4: B.
    """
    courses = [
        {"course_id": "S", "difficulty": "intermediate"},
        {"course_id": "T", "difficulty": "intermediate"},
        {"course_id": "A", "difficulty": "intermediate"},
        {"course_id": "B", "difficulty": "intermediate"},
    ]
    prereqs = [
        {"source_course_id": "S", "target_course_id": "T", "relationship_type": "recommended"},
        {"source_course_id": "T", "target_course_id": "A", "relationship_type": "required"},
        {"source_course_id": "A", "target_course_id": "B", "relationship_type": "required"},
    ]

    result = schedule_courses(courses, prereqs, max_courses_per_semester=1)

    assert result["total_semesters"] == 4
    assert len(result["semesters"]) == 4

    # 1. S is scheduled before T
    assert result["course_to_semester"]["S"] < result["course_to_semester"]["T"]
    # 2. T is scheduled before A
    assert result["course_to_semester"]["T"] < result["course_to_semester"]["A"]
    # 3. A is scheduled before B
    assert result["course_to_semester"]["A"] < result["course_to_semester"]["B"]

    # Exact expected assignment: Sem 1: S, Sem 2: T, Sem 3: A, Sem 4: B
    assert [c["course_id"] for c in result["semesters"][0]["courses"]] == ["S"]
    assert [c["course_id"] for c in result["semesters"][1]["courses"]] == ["T"]
    assert [c["course_id"] for c in result["semesters"][2]["courses"]] == ["A"]
    assert [c["course_id"] for c in result["semesters"][3]["courses"]] == ["B"]

    # 4. No semester contains more than one course
    for sem in result["semesters"]:
        assert sem["course_count"] == 1
        assert len(sem["courses"]) == 1

    # 5. Passes mathematical schedule verification
    assert verify_semester_schedule(result, prereqs, max_courses_per_semester=1) is True

    # 6. Determinism: repeated calls produce identical schedules
    for _ in range(5):
        repeat_result = schedule_courses(courses, prereqs, max_courses_per_semester=1)
        assert repeat_result == result


def test_soft_prerequisite_not_inverted_by_critical_path_optional():
    """Verifies that optional dependencies follow the same soft-precedence policy."""
    courses = [
        {"course_id": "S", "difficulty": "intermediate"},
        {"course_id": "T", "difficulty": "intermediate"},
        {"course_id": "A", "difficulty": "intermediate"},
        {"course_id": "B", "difficulty": "intermediate"},
    ]
    prereqs = [
        {"source_course_id": "S", "target_course_id": "T", "relationship_type": "optional"},
        {"source_course_id": "T", "target_course_id": "A", "relationship_type": "required"},
        {"source_course_id": "A", "target_course_id": "B", "relationship_type": "required"},
    ]

    result = schedule_courses(courses, prereqs, max_courses_per_semester=1)

    assert result["total_semesters"] == 4
    assert result["course_to_semester"]["S"] < result["course_to_semester"]["T"]
    assert result["course_to_semester"]["T"] < result["course_to_semester"]["A"]
    assert result["course_to_semester"]["A"] < result["course_to_semester"]["B"]

    assert [c["course_id"] for c in result["semesters"][0]["courses"]] == ["S"]
    assert [c["course_id"] for c in result["semesters"][1]["courses"]] == ["T"]
    assert [c["course_id"] for c in result["semesters"][2]["courses"]] == ["A"]
    assert [c["course_id"] for c in result["semesters"][3]["courses"]] == ["B"]

    assert verify_semester_schedule(result, prereqs, max_courses_per_semester=1) is True

    # Determinism
    for _ in range(5):
        assert schedule_courses(courses, prereqs, max_courses_per_semester=1) == result


def test_critical_path_prioritization_retained_when_no_dependency_conflict():
    """Verifies critical-path prioritization is preserved when it does not conflict
    with prerequisite constraints.

    Chain 1: req_c1 -> req_c2 -> req_c3 (required, depth 3)
    Chain 2: req_d1 -> req_d2 (required, depth 2)
    Capacity: 1 course per semester.

    At semester 1, both req_c1 and req_d1 are eligible.
    req_c1 must be selected first because it unblocks a longer chain.
    """
    courses = [
        {"course_id": "req_d1", "difficulty": "intermediate"},
        {"course_id": "req_d2", "difficulty": "intermediate"},
        {"course_id": "req_c1", "difficulty": "intermediate"},
        {"course_id": "req_c2", "difficulty": "intermediate"},
        {"course_id": "req_c3", "difficulty": "intermediate"},
    ]
    prereqs = [
        {"source_course_id": "req_c1", "target_course_id": "req_c2", "relationship_type": "required"},
        {"source_course_id": "req_c2", "target_course_id": "req_c3", "relationship_type": "required"},
        {"source_course_id": "req_d1", "target_course_id": "req_d2", "relationship_type": "required"},
    ]

    result = schedule_courses(courses, prereqs, max_courses_per_semester=1)
    assert result["total_semesters"] == 5

    # req_c1 has depth 3, req_d1 has depth 2 -> req_c1 must be scheduled in semester 1
    assert result["semesters"][0]["courses"][0]["course_id"] == "req_c1"
    assert verify_semester_schedule(result, prereqs, max_courses_per_semester=1) is True


def test_verifier_rejects_inconsistent_course_count():
    """Verifier must reject schedules where course_count disagrees with len(courses)."""
    courses = [{"course_id": "c1", "semester": 1}]
    inconsistent = {
        "semesters": [
            {
                "semester_number": 1,
                "courses": courses,
                "course_count": 99,  # Mismatched! Actual is 1
            }
        ],
        "course_to_semester": {"c1": 1},
        "ordered_courses": courses,
        "total_semesters": 1,
    }
    assert verify_semester_schedule(inconsistent, []) is False


def test_verifier_rejects_non_sequential_semester_number():
    """Verifier must reject schedules where semester_number is out of 1-indexed sequence."""
    c1 = {"course_id": "c1", "semester": 1}
    c2 = {"course_id": "c2", "semester": 3}
    inconsistent = {
        "semesters": [
            {"semester_number": 1, "courses": [c1], "course_count": 1},
            {"semester_number": 3, "courses": [c2], "course_count": 1},  # Skipped 2!
        ],
        "course_to_semester": {"c1": 1, "c2": 3},
        "ordered_courses": [c1, c2],
        "total_semesters": 2,
    }
    assert verify_semester_schedule(inconsistent, []) is False


def test_verifier_rejects_course_to_semester_mapping_contradiction():
    """Verifier must reject schedules where course_to_semester contradicts group assignment."""
    c1 = {"course_id": "c1", "semester": 1}
    inconsistent = {
        "semesters": [
            {"semester_number": 1, "courses": [c1], "course_count": 1},
        ],
        "course_to_semester": {"c1": 2},  # Claims semester 2, but appears in semester 1 group!
        "ordered_courses": [c1],
        "total_semesters": 1,
    }
    assert verify_semester_schedule(inconsistent, []) is False


def test_verifier_rejects_ordered_courses_mismatch():
    """Verifier must reject schedules where flattened ordered_courses diverges from groups."""
    c1 = {"course_id": "c1", "semester": 1}
    c2 = {"course_id": "c2", "semester": 2}
    inconsistent = {
        "semesters": [
            {"semester_number": 1, "courses": [c1], "course_count": 1},
            {"semester_number": 2, "courses": [c2], "course_count": 1},
        ],
        "course_to_semester": {"c1": 1, "c2": 2},
        "ordered_courses": [c2, c1],  # Inverted sequence compared to semester groups!
        "total_semesters": 2,
    }
    assert verify_semester_schedule(inconsistent, []) is False


def test_verifier_rejects_duplicate_course_across_semesters():
    """Verifier must reject schedules where a course appears more than once across groups."""
    c1_a = {"course_id": "c1", "semester": 1}
    c1_b = {"course_id": "c1", "semester": 2}
    inconsistent = {
        "semesters": [
            {"semester_number": 1, "courses": [c1_a], "course_count": 1},
            {"semester_number": 2, "courses": [c1_b], "course_count": 1},
        ],
        "course_to_semester": {"c1": 1},
        "ordered_courses": [c1_a, c1_b],
        "total_semesters": 2,
    }
    assert verify_semester_schedule(inconsistent, []) is False


def test_verifier_rejects_total_semesters_mismatch():
    """Verifier must reject schedules where total_semesters contradicts len(semesters)."""
    c1 = {"course_id": "c1", "semester": 1}
    inconsistent = {
        "semesters": [
            {"semester_number": 1, "courses": [c1], "course_count": 1},
        ],
        "course_to_semester": {"c1": 1},
        "ordered_courses": [c1],
        "total_semesters": 5,  # Contradicts len(semesters) == 1
    }
    assert verify_semester_schedule(inconsistent, []) is False


def test_verifier_rejects_course_internal_semester_mismatch():
    """Verifier must reject schedules where a course dict's 'semester' contradicts group number."""
    c1 = {"course_id": "c1", "semester": 9}  # Contradicts group semester_number 1
    inconsistent = {
        "semesters": [
            {"semester_number": 1, "courses": [c1], "course_count": 1},
        ],
        "course_to_semester": {"c1": 1},
        "ordered_courses": [c1],
        "total_semesters": 1,
    }
    assert verify_semester_schedule(inconsistent, []) is False


def test_verifier_rejects_missing_course_semester_attribute():
    """Verifier must reject an otherwise valid schedule if a course record is missing 'semester'."""
    # Structurally valid schedule where all counts, mappings, and IDs agree, but c1 lacks 'semester'
    c1 = {"course_id": "c1"}  # Missing 'semester'!
    schedule = {
        "semesters": [
            {"semester_number": 1, "courses": [c1], "course_count": 1},
        ],
        "course_to_semester": {"c1": 1},
        "ordered_courses": [c1],
        "total_semesters": 1,
    }
    assert verify_semester_schedule(schedule, []) is False


# -----------------------------------------------------------------------------
# End-to-End Service & API Integration Tests
# -----------------------------------------------------------------------------

def test_service_generates_learning_path_with_natural_waves():
    # KB chain: programming_fundamentals -> data_structures -> design_and_analysis_of_algorithms
    result = generate_learning_path(
        ["Algorithms", "Data Structures", "Intro to Programming"],
        learning_goal="DAA Foundations",
        use_ai=False,
    )
    assert "semesters" in result
    assert len(result["semesters"]) == 3
    assert result["semesters"][0]["courses"][0]["course_id"] == "programming_fundamentals"
    assert result["semesters"][1]["courses"][0]["course_id"] == "data_structures"
    assert result["semesters"][2]["courses"][0]["course_id"] == "design_and_analysis_of_algorithms"

    for sem in result["semesters"]:
        assert sem["course_count"] == len(sem["courses"])
        for c in sem["courses"]:
            assert c["semester"] == sem["semester_number"]
            assert c["wave"] == sem["semester_number"]


def test_service_generates_learning_path_with_workload_capacity():
    # Two independent courses: python_programming and calculus
    result = generate_learning_path(
        ["python_programming", "calculus"],
        learning_goal="Math and Coding",
        use_ai=False,
        max_courses_per_semester=1,
    )
    assert len(result["semesters"]) == 2
    assert result["semesters"][0]["course_count"] == 1
    assert result["semesters"][1]["course_count"] == 1


def test_api_learning_path_with_curricular_constraints(client):
    payload = {
        "courses": ["Intro to Programming", "Data Structures", "Algorithms"],
        "learning_goal": "Interview Prep",
        "use_ai": False,
        "max_courses_per_semester": 1,
        "max_semesters": 4,
    }
    response = client.post("/api/v1/learning-path", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "semesters" in data
    assert len(data["semesters"]) == 3
    assert data["semesters"][0]["courses"][0]["course_id"] == "programming_fundamentals"
    assert data["semesters"][1]["courses"][0]["course_id"] == "data_structures"
    assert data["semesters"][2]["courses"][0]["course_id"] == "design_and_analysis_of_algorithms"


def test_api_learning_path_rejects_infeasible_max_semesters(client):
    payload = {
        "courses": ["Intro to Programming", "Data Structures", "Algorithms"],
        "learning_goal": "Too Fast Track",
        "use_ai": False,
        "max_semesters": 2,  # Chain requires 3 semesters!
    }
    response = client.post("/api/v1/learning-path", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "curricular_constraint_error"
    assert "requires at least 3 semesters" in data["detail"]["message"]
    assert data["detail"]["required_semesters"] == 3
    assert data["detail"]["max_semesters"] == 2


def test_api_learning_path_rejects_invalid_constraint_values(client):
    payload = {
        "courses": ["Python Programming"],
        "learning_goal": "Validation Test",
        "max_courses_per_semester": 0,
    }
    response = client.post("/api/v1/learning-path", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "curricular_constraint_error"
    assert "must be at least 1" in data["detail"]["message"]


def test_api_learning_path_backward_compatibility_when_scheduling_omitted(client):
    payload = {
        "courses": ["Python Programming", "Machine Learning"],
        "learning_goal": "ML Foundations",
        "use_ai": False,
    }
    response = client.post("/api/v1/learning-path", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Existing fields remain fully populated and functional
    assert "learning_goal" in data
    assert "selected_courses" in data
    assert "ordered_courses" in data
    assert "prerequisites" in data
    assert "ai_proposals_used" in data
    assert "warnings" in data

    # Level 7 extended field present
    assert "semesters" in data
    assert isinstance(data["semesters"], list)
    assert len(data["semesters"]) >= 1
