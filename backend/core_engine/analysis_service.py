from typing import Any, Dict, List, Optional, Set

from backend.daa_engine.graph import (
    DirectedGraph,
    detect_cycle_dfs,
    topological_sort_kahn,
    verify_topological_order,
)
from backend.daa_engine.scheduler import (
    CurricularConstraintError as SchedulerConstraintError,
    schedule_courses,
    verify_semester_schedule,
)
from backend.knowledge_base.knowledge_base import (
    KnowledgeBase,
    get_default_knowledge_base,
)


class LearningPathError(Exception):
    """Base exception for learning path generation failures."""
    pass


class CourseResolutionError(LearningPathError):
    """Raised when selected course names cannot be resolved cleanly against the Knowledge Base."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        needs_clarification: bool = False,
        clarification: Optional[str] = None,
        candidates: Optional[List[Any]] = None,
    ):
        super().__init__(message)
        self.query: Optional[str] = query
        self.needs_clarification: bool = needs_clarification
        self.clarification: Optional[str] = clarification
        self.candidates: List[Any] = candidates or []


class CycleConflictError(LearningPathError):
    """Raised when course dependencies form a circular prerequisite graph conflict."""

    def __init__(self, message: str, cycle_path: Optional[List[str]] = None):
        super().__init__(message)
        self.cycle_path: List[str] = cycle_path or []


class CurricularConstraintError(SchedulerConstraintError, LearningPathError):
    """Raised when user-defined curricular constraints are invalid or cannot be satisfied."""

    def __init__(
        self,
        message: str,
        required_semesters: Optional[int] = None,
        max_semesters: Optional[int] = None,
        constraint_type: Optional[str] = None,
    ):
        super().__init__(message)
        self.required_semesters = required_semesters
        self.max_semesters = max_semesters
        self.constraint_type = constraint_type


def generate_learning_path(
    course_names: List[str],
    learning_goal: Optional[str] = None,
    kb: Optional[KnowledgeBase] = None,
    max_courses_per_semester: Optional[int] = None,
    max_semesters: Optional[int] = None,
    **kwargs: Any,  # Safely absorb any legacy kwargs without error
) -> Dict[str, Any]:
    """Orchestrates end-to-end learning path generation using pure DAA and Curated Knowledge Base.

    Coordinates:
      1. Course normalization & canonical resolution against Knowledge Base.
      2. Rejection of uncataloged/unknown course entries.
      3. Validating user-defined constraints.
      4. Retrieving verified prerequisite relationships among selected courses.
      5. Constructing the directed graph and checking for cycles via iterative 3-state DFS.
      6. Generating a deterministic learning order via min-heap Kahn's algorithm.
      7. Mathematically verifying the topological order against all dependency edges.
      8. Partitioning courses into pedagogically verified semester waves subject to capacity limits.

    Returns a structured dictionary representing the verified learning path result.
    """
    target_kb = kb or get_default_knowledge_base()

    # 1. Constraint validation
    if max_courses_per_semester is not None:
        if not isinstance(max_courses_per_semester, int) or max_courses_per_semester < 1:
            raise CurricularConstraintError("max_courses_per_semester must be at least 1.")

    if max_semesters is not None:
        if not isinstance(max_semesters, int) or max_semesters < 1:
            raise CurricularConstraintError("max_semesters must be at least 1.")

    # 2. Input course validation
    if not course_names or not isinstance(course_names, list):
        raise CourseResolutionError("Course list cannot be empty. Please select at least one course.")

    cleaned_names: List[str] = []
    for c in course_names:
        if isinstance(c, str):
            clean = c.strip()
            if clean:
                if len(clean) > 100:
                    raise CourseResolutionError(f"Course name exceeds 100 characters: '{clean[:50]}...'")
                cleaned_names.append(clean)

    if not cleaned_names:
        raise CourseResolutionError("Course list contains no valid non-empty course names.")

    if len(cleaned_names) > 50:
        raise CourseResolutionError(f"Course list exceeds maximum limit of 50 courses (received {len(cleaned_names)}).")

    # 3. Canonical course resolution against Knowledge Base
    resolved_courses: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    unknown_queries: List[str] = []
    ambiguous_queries: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for raw_name in cleaned_names:
        res = target_kb.resolve_course(raw_name)
        if res.is_resolved and res.course is not None:
            cid = res.course_id
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                course_data = dict(res.course)
                course_data["source"] = "curated"
                course_data["is_curated"] = True
                course_data["is_ai_inferred"] = False
                course_data["provenance"] = "expert_curated"
                resolved_courses.append(course_data)
        elif res.is_ambiguous:
            ambiguous_queries.append({
                "query": raw_name,
                "candidates": res.candidates,
                "error_message": res.error_message,
            })
        elif res.is_unknown:
            unknown_queries.append(raw_name)

    # 4. Handle unknown and ambiguous courses (Strict Knowledge Base validation)
    if ambiguous_queries:
        first_amb = ambiguous_queries[0]
        resolution_errors = [
            a["error_message"] or f"Ambiguous course name: '{a['query']}'"
            for a in ambiguous_queries
        ]
        raise CourseResolutionError(
            f"Course resolution failed: {'; '.join(resolution_errors)}",
            query=first_amb.get("query"),
            needs_clarification=True,
            clarification=first_amb.get("clarification"),
            candidates=first_amb.get("candidates", []),
        )

    if unknown_queries:
        import difflib
        all_courses = target_kb.get_all_courses()
        name_map = {c["name"].lower(): c["name"] for c in all_courses}
        resolution_errors = []
        all_matches = []
        for q in unknown_queries:
            matches = difflib.get_close_matches(q.lower(), name_map.keys(), n=3, cutoff=0.4)
            if matches:
                cand_names = [f"'{name_map[m]}'" for m in matches]
                all_matches.extend([name_map[m] for m in matches])
                resolution_errors.append(
                    f"Course '{q}' is not recognized in the knowledge base catalog. Did you mean: {', '.join(cand_names)}?"
                )
            else:
                resolution_errors.append(
                    f"Course '{q}' is not recognized in the knowledge base catalog. Please select an available course."
                )
        raise CourseResolutionError(
            f"Course resolution failed: {'; '.join(resolution_errors)}",
            query=unknown_queries[0],
            candidates=all_matches,
        )

    if not resolved_courses:
        raise CourseResolutionError("None of the specified courses could be resolved against the academic catalog.")

    selected_ids = set(c["course_id"] for c in resolved_courses)

    # 5. Retrieve curated prerequisite relationships from Knowledge Base
    all_relationships: List[Dict[str, Any]] = []
    for r in target_kb.get_prerequisites():
        src = r.get("source_course_id")
        tgt = r.get("target_course_id")
        if src in selected_ids and tgt in selected_ids:
            item = dict(r)
            item["source"] = "curated"
            item["is_ai_proposed"] = False
            item["evidence_type"] = r.get("evidence_type", "expert_curated")
            item["confidence"] = r.get("confidence")
            all_relationships.append(item)

    # 6. Single-course early exit
    if len(selected_ids) == 1:
        single_course = resolved_courses[0]
        schedule_result = schedule_courses(
            courses=resolved_courses,
            relationships=[],
            max_courses_per_semester=max_courses_per_semester,
            max_semesters=max_semesters,
        )
        return {
            "learning_goal": (learning_goal or "General Computer Science").strip(),
            "selected_courses": resolved_courses,
            "ordered_courses": schedule_result["ordered_courses"],
            "semesters": schedule_result["semesters"],
            "prerequisites": [],
            "ai_proposals_used": False,
            "warnings": [f"Single course selected: '{single_course['name']}'. No prerequisite sequencing required."],
            "total_courses": 1,
            "total_prerequisites": 0,
            "total_semesters": len(schedule_result["semesters"]),
            "ai_summary": {
                "requested": False,
                "course_resolution_status": "curated_only",
                "message": "Pure DAA Knowledge Base mode (AI disabled)",
            },
        }

    # 7. Directed graph construction
    graph = DirectedGraph(list(selected_ids))
    for r in all_relationships:
        graph.add_edge(r["source_course_id"], r["target_course_id"])

    # 8. Cycle verification via iterative 3-state DFS
    has_cycle, cycle_path = detect_cycle_dfs(graph)
    if has_cycle:
        raise CycleConflictError(
            f"Cyclic dependency detected among selected courses: {' -> '.join(cycle_path)}. "
            "A valid learning order cannot be formed until conflicting prerequisite relationships are resolved.",
            cycle_path=cycle_path,
        )

    # 9. Deterministic topological sorting via Kahn's algorithm with min-heap
    ordered_ids = topological_sort_kahn(graph)

    # 10. Formal mathematical invariant verification
    if not verify_topological_order(graph, ordered_ids):
        raise CycleConflictError("Topological ordering verification failed mathematical validation.")

    # 11. Pedagogical wave scheduling and workload-constrained optimization
    try:
        schedule_result = schedule_courses(
            courses=resolved_courses,
            relationships=all_relationships,
            max_courses_per_semester=max_courses_per_semester,
            max_semesters=max_semesters,
        )
    except SchedulerConstraintError as exc:
        raise CurricularConstraintError(
            str(exc),
            required_semesters=getattr(exc, "required_semesters", None),
            max_semesters=getattr(exc, "max_semesters", None),
            constraint_type=getattr(exc, "constraint_type", None),
        ) from exc

    if not verify_semester_schedule(
        schedule_result=schedule_result,
        relationships=all_relationships,
        max_courses_per_semester=max_courses_per_semester,
        max_semesters=max_semesters,
    ):
        raise CurricularConstraintError("Semester schedule verification failed mathematical validation.")

    course_map = {c["course_id"]: c for c in resolved_courses}
    return {
        "learning_goal": (learning_goal or "General Computer Science").strip(),
        "selected_courses": resolved_courses,
        "ordered_courses": [course_map[cid] for cid in ordered_ids],
        "semesters": schedule_result["semesters"],
        "prerequisites": all_relationships,
        "ai_proposals_used": False,
        "warnings": warnings,
        "total_courses": len(resolved_courses),
        "total_prerequisites": len(all_relationships),
        "total_semesters": len(schedule_result["semesters"]),
        "ai_summary": {
            "requested": False,
            "course_resolution_status": "curated_only",
            "message": "Pure DAA Knowledge Base mode (AI disabled)",
        },
    }
