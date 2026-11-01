from pathlib import Path
import pytest

from backend.knowledge_base.knowledge_base import (
    KnowledgeBase,
    ResolutionStatus,
    load_knowledge_base,
    normalize_course_name,
    resolve_course,
)
from backend.knowledge_base.validate_kb_by_Claude import validate_kb_data, validate_kb_file


# --- Knowledge Base Loading Tests ---

def test_kb_loads_default_catalog():
    kb = load_knowledge_base()
    courses = kb.get_all_courses()
    prereqs = kb.get_prerequisites()

    assert len(courses) == 70
    assert len(prereqs) == 115
    assert kb.get_course("python_programming") is not None
    assert kb.get_course("data_structures") is not None


def test_kb_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_knowledge_base("nonexistent_path/fake_courses.json")


def test_kb_malformed_json(tmp_path: Path):
    bad_json_file = tmp_path / "bad.json"
    bad_json_file.write_text("{ unquoted_key: invalid }", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed JSON"):
        load_knowledge_base(bad_json_file)


# --- Name Normalization Tests ---

def test_normalize_course_name():
    assert normalize_course_name("  Python   Programming  ") == "python programming"
    assert normalize_course_name("DATA STRUCTURES") == "data structures"
    assert normalize_course_name("\tMachine\nLearning  ") == "machine learning"
    assert normalize_course_name("") == ""
    assert normalize_course_name("   ") == ""


# --- Canonical Name and Alias Resolution Tests ---

def test_resolve_canonical_name():
    res = resolve_course("Python Programming")
    assert res.is_resolved
    assert res.status == ResolutionStatus.RESOLVED
    assert res.course_id == "python_programming"
    assert res.canonical_name == "Python Programming"
    assert res.course is not None
    assert res.course["difficulty"] == "beginner"


def test_resolve_by_course_id():
    res = resolve_course("data_structures")
    assert res.is_resolved
    assert res.course_id == "data_structures"
    assert res.canonical_name == "Data Structures"


def test_resolve_by_aliases():
    res_python = resolve_course("Python")
    assert res_python.is_resolved
    assert res_python.course_id == "python_programming"

    res_intro = resolve_course("Intro to Programming")
    assert res_intro.is_resolved
    assert res_intro.course_id == "programming_fundamentals"

    res_oop = resolve_course("OOP")
    assert res_oop.is_resolved
    assert res_oop.course_id == "object_oriented_programming"


def test_resolve_with_case_and_whitespace_normalization():
    res = resolve_course("   pYtHoN   PrOgRaMmInG   ")
    assert res.is_resolved
    assert res.course_id == "python_programming"

    res_alias = resolve_course("  oOp  ")
    assert res_alias.is_resolved
    assert res_alias.course_id == "object_oriented_programming"


# --- Unknown Course Handling Tests ---

def test_resolve_unknown_course():
    res = resolve_course("Quantum Culinary Arts 101")
    assert res.is_unknown
    assert res.status == ResolutionStatus.UNKNOWN
    assert res.course_id is None
    assert "not recognized" in res.error_message


def test_resolve_empty_query():
    res = resolve_course("   ")
    assert res.is_unknown
    assert res.status == ResolutionStatus.UNKNOWN
    assert res.course_id is None
    assert "empty" in res.error_message.lower()


# --- Ambiguous Alias Detection Tests ---

def test_ambiguous_alias_detection():
    # Construct an in-memory knowledge base with a deliberate duplicate alias
    test_data = {
        "courses": [
            {
                "course_id": "course_a",
                "name": "Course A",
                "aliases": ["Shared Alias"],
                "category": "Test",
                "description": "Desc A",
                "difficulty": "beginner",
            },
            {
                "course_id": "course_b",
                "name": "Course B",
                "aliases": ["Shared Alias"],
                "category": "Test",
                "description": "Desc B",
                "difficulty": "intermediate",
            },
        ],
        "prerequisites": [],
    }
    kb = KnowledgeBase(source=test_data)

    res = kb.resolve_course("Shared Alias")
    assert res.is_ambiguous
    assert res.status == ResolutionStatus.AMBIGUOUS
    assert res.course_id is None
    assert set(res.candidates) == {"course_a", "course_b"}
    assert "ambiguous" in res.error_message.lower()


# --- Knowledge Base Validator Tests ---

def test_validator_on_existing_catalog():
    is_valid, errors, stats = validate_kb_file(Path("backend/knowledge_base/courses.json"))
    assert is_valid is True
    assert len(errors) == 0
    assert stats["courses_count"] == 70
    assert stats["relationships_count"] == 115


def test_validator_rejects_missing_keys():
    errors, _ = validate_kb_data({})
    assert any("courses" in e for e in errors)
    assert any("prerequisites" in e for e in errors)


def test_validator_rejects_invalid_course_id():
    bad_data = {
        "courses": [
            {
                "course_id": "Invalid-ID!",
                "name": "Bad Course",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": "beginner",
            }
        ],
        "prerequisites": [],
    }
    errors, _ = validate_kb_data(bad_data)
    assert any("invalid ID format" in e for e in errors)


def test_validator_rejects_duplicate_course_ids():
    bad_data = {
        "courses": [
            {
                "course_id": "course_a",
                "name": "Course A1",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": "beginner",
            },
            {
                "course_id": "course_a",
                "name": "Course A2",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": "beginner",
            },
        ],
        "prerequisites": [],
    }
    errors, _ = validate_kb_data(bad_data)
    assert any("Duplicate course_id: 'course_a'" in e for e in errors)


def test_validator_rejects_self_loop():
    bad_data = {
        "courses": [
            {
                "course_id": "course_a",
                "name": "Course A",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": "beginner",
            }
        ],
        "prerequisites": [
            {
                "relationship_id": "loop_1",
                "source_course_id": "course_a",
                "target_course_id": "course_a",
                "relationship_type": "required",
                "confidence": 1.0,
                "evidence_type": "expert_curated",
                "explanation": "Self reference",
            }
        ],
    }
    errors, _ = validate_kb_data(bad_data)
    assert any("self-loop" in e for e in errors)


def test_validator_rejects_cycle():
    bad_data = {
        "courses": [
            {
                "course_id": "course_a",
                "name": "Course A",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": "beginner",
            },
            {
                "course_id": "course_b",
                "name": "Course B",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": "beginner",
            },
        ],
        "prerequisites": [
            {
                "relationship_id": "rel_ab",
                "source_course_id": "course_a",
                "target_course_id": "course_b",
                "relationship_type": "required",
                "confidence": 1.0,
                "evidence_type": "expert_curated",
                "explanation": "A before B",
            },
            {
                "relationship_id": "rel_ba",
                "source_course_id": "course_b",
                "target_course_id": "course_a",
                "relationship_type": "required",
                "confidence": 1.0,
                "evidence_type": "expert_curated",
                "explanation": "B before A",
            },
        ],
    }
    errors, _ = validate_kb_data(bad_data)
    assert any("contains a cycle" in e for e in errors)


def test_validator_rejects_invalid_confidence():
    bad_data = {
        "courses": [
            {
                "course_id": "course_a",
                "name": "Course A",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": "beginner",
            },
            {
                "course_id": "course_b",
                "name": "Course B",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": "beginner",
            },
        ],
        "prerequisites": [
            {
                "relationship_id": "rel_ab",
                "source_course_id": "course_a",
                "target_course_id": "course_b",
                "relationship_type": "required",
                "confidence": 1.5,  # Out of [0, 1] bounds
                "evidence_type": "expert_curated",
                "explanation": "Explanation",
            }
        ],
    }
    errors, _ = validate_kb_data(bad_data)
    assert any("invalid confidence" in e for e in errors)


def test_validator_rejects_boolean_confidence():
    bad_data = {
        "courses": [
            {
                "course_id": "course_a",
                "name": "Course A",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": "beginner",
            },
            {
                "course_id": "course_b",
                "name": "Course B",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": "beginner",
            },
        ],
        "prerequisites": [
            {
                "relationship_id": "rel_ab",
                "source_course_id": "course_a",
                "target_course_id": "course_b",
                "relationship_type": "required",
                "confidence": True,  # Boolean must be rejected
                "evidence_type": "expert_curated",
                "explanation": "Explanation",
            }
        ],
    }
    errors, _ = validate_kb_data(bad_data)
    assert any("confidence cannot be a boolean" in e for e in errors)


def test_validator_rejects_unexpected_field_types():
    bad_data = {
        "courses": [
            {
                "course_id": "course_a",
                "name": "Course A",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": ["beginner"],  # List instead of string
            },
            {
                "course_id": True,  # Boolean instead of string
                "name": "Course B",
                "aliases": [],
                "category": "Test",
                "description": "Desc",
                "difficulty": "beginner",
            },
        ],
        "prerequisites": [
            {
                "relationship_id": "rel_ab",
                "source_course_id": 12345,  # Integer instead of string
                "target_course_id": "course_a",
                "relationship_type": {"type": "required"},  # Dict instead of string
                "confidence": 0.9,
                "evidence_type": "expert_curated",
                "explanation": "Explanation",
            }
        ],
    }
    errors, _ = validate_kb_data(bad_data)
    assert any("invalid difficulty" in e for e in errors)
    assert any("invalid 'course_id'" in e for e in errors)
    assert any("source_course_id must be a non-empty string" in e for e in errors)
    assert any("invalid relationship_type" in e for e in errors)


def test_resolve_with_safe_normalization_and_punctuation():
    res_period = resolve_course("Python Programming.")
    assert res_period.is_resolved
    assert res_period.course_id == "python_programming"

    res_hyphen = resolve_course("Object-Oriented-Programming")
    assert res_hyphen.is_resolved
    assert res_hyphen.course_id == "object_oriented_programming"

    res_ampersand = resolve_course("Probability & Statistics")
    assert res_ampersand.is_resolved
    assert res_ampersand.course_id == "probability_and_statistics"


def test_resolve_singular_plural_inflections():
    res_os = resolve_course("Operating System")
    assert res_os.is_resolved
    assert res_os.course_id == "operating_systems"

    res_ds = resolve_course("Data Structure")
    assert res_ds.is_resolved
    assert res_ds.course_id == "data_structures"


def test_resolve_high_confidence_spelling_correction():
    res_typo = resolve_course("Machne Learning")
    assert res_typo.is_resolved
    assert res_typo.is_corrected
    assert res_typo.course_id == "machine_learning"


def test_resolve_suggests_close_candidates_on_unknown():
    res_unknown = resolve_course("Pythen")
    assert res_unknown.is_unknown
    assert "Did you mean:" in res_unknown.error_message
    assert "Python Programming" in res_unknown.error_message


def test_resolve_broad_keyword_ambiguity():
    # "Programming" matches 5 courses in KB and must be flagged as ambiguous, not silently autocorrected
    res_prog = resolve_course("Programming")
    assert res_prog.is_ambiguous
    assert res_prog.status == ResolutionStatus.AMBIGUOUS
    assert res_prog.course_id is None
    assert "ambiguous and matches multiple courses" in res_prog.error_message
    assert "C Programming" in res_prog.error_message
    assert "Python Programming" in res_prog.error_message

    # "Data" matches multiple courses in KB
    res_data = resolve_course("Data")
    assert res_data.is_ambiguous
    assert res_data.status == ResolutionStatus.AMBIGUOUS
    assert res_data.course_id is None
    assert "Data Structures" in res_data.error_message


def test_resolve_required_input_list():
    # Canonical exact
    assert resolve_course("Python Programming").course_id == "python_programming"
    assert resolve_course("Software Engineering").course_id == "software_engineering"
    assert resolve_course("Machine Learning").course_id == "machine_learning"
    assert resolve_course("Design and Analysis of Algorithms").course_id == "design_and_analysis_of_algorithms"
    assert resolve_course("Java Programming").course_id == "java_programming"

    # Case insensitive
    assert resolve_course("python programming").course_id == "python_programming"

    # Aliases
    assert resolve_course("Python").course_id == "python_programming"
    assert resolve_course("DAA").course_id == "design_and_analysis_of_algorithms"

    # Typos (must be corrected)
    assert resolve_course("Desgn and Analys of Algorthms").course_id == "design_and_analysis_of_algorithms"
    assert resolve_course("Machne Learning").course_id == "machine_learning"

    # Unknowns
    assert resolve_course("English").is_unknown
    assert resolve_course("Web Design").is_unknown
    assert resolve_course("asdfghjk qwerty 12345").is_unknown


