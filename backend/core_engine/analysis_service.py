import re
from typing import Any, Dict, List, Optional, Set

from backend.ai_engine.client import (
    AIEngineError,
    evaluate_unknown_courses,
    request_prerequisite_proposals,
)
from backend.core_engine.config import settings
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
    """Raised when selected course names cannot be resolved cleanly."""

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
    """Raised when course dependencies form a circular graph conflict."""

    def __init__(self, message: str, cycle_path: Optional[List[str]] = None):
        super().__init__(message)
        self.cycle_path: List[str] = cycle_path or []


class CurricularConstraintError(SchedulerConstraintError, LearningPathError):
    """Raised when user-defined curricular constraints are invalid or cannot be satisfied."""
    pass


def generate_learning_path(
    course_names: List[str],
    learning_goal: Optional[str] = None,
    kb: Optional[KnowledgeBase] = None,
    ai_client: Optional[Any] = None,
    use_ai: bool = True,
    fallback_on_ai_failure: bool = True,
    max_courses_per_semester: Optional[int] = None,
    max_semesters: Optional[int] = None,
) -> Dict[str, Any]:
    """Orchestrates end-to-end learning path generation.

    Coordinates:
      1. Course normalization & canonical resolution via Knowledge Base.
      2. AI-assisted evaluation of unrecognized/unknown courses (when enabled).
      3. Retrieving existing curated prerequisite relationships.
      4. Requesting and validating LLM prerequisite proposals via AI Engine.
      5. Combining relationships in-memory without altering persistent KB data.
      6. Constructing the directed graph and checking for cycles via DAA Engine.
      7. Generating a deterministic learning order via Kahn's algorithm.
      8. Mathematically verifying the topological order against all dependency edges.
      9. Partitioning courses into pedagogically verified semester waves.

    Returns a structured dictionary representing the learning path result.
    """
    target_kb = kb or get_default_knowledge_base()

    # 1. Input validation
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

    # 2. Canonical course resolution against Knowledge Base
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

    # 3. Handle unknown and ambiguous courses
    unknown_evaluated_count = 0
    ambiguous_evaluated_count = 0
    resolution_status_str = "curated_only"

    if not use_ai:
        if ambiguous_queries:
            resolution_errors = [
                a["error_message"] or f"Ambiguous course name: '{a['query']}'"
                for a in ambiguous_queries
            ]
            raise CourseResolutionError(f"Course resolution failed: {'; '.join(resolution_errors)}")

        if unknown_queries:
            error_details = []
            for u in unknown_queries:
                kb_res = target_kb.resolve_course(u)
                if kb_res.candidates:
                    error_details.append(kb_res.error_message or f"Course '{u}' is not recognized in the knowledge base.")
                else:
                    error_details.append(f"Course '{u}' is not recognized in the knowledge base.")
            raise CourseResolutionError(
                f"Course resolution failed: {'; '.join(error_details)} "
                "AI assistance is disabled. Enable AI assistance to infer new courses, or select from the curated courses."
            )
    else:
        # AI is enabled: evaluate unknown and ambiguous queries with context
        queries_to_evaluate: List[str] = []
        for u in unknown_queries:
            if u not in queries_to_evaluate:
                queries_to_evaluate.append(u)
        for a in ambiguous_queries:
            if a["query"] not in queries_to_evaluate:
                queries_to_evaluate.append(a["query"])

        if queries_to_evaluate:
            unknown_evaluated_count = len(unknown_queries)
            ambiguous_evaluated_count = len(ambiguous_queries)

            # Build candidate map from curated Knowledge Base for ambiguous queries
            candidates_map: Dict[str, List[Dict[str, str]]] = {}
            for a in ambiguous_queries:
                q = a["query"]
                c_list: List[Dict[str, str]] = []
                for cid in a.get("candidates", []):
                    c_obj = target_kb.get_course(cid)
                    if c_obj:
                        c_list.append({"course_id": cid, "name": c_obj.get("name", cid)})
                if c_list:
                    candidates_map[q] = c_list

            other_course_names = [c["name"] for c in resolved_courses]

            try:
                evaluations = evaluate_unknown_courses(
                    queries_to_evaluate,
                    client=ai_client,
                    model=settings.gemini_model,
                    timeout=settings.gemini_timeout,
                    learning_goal=learning_goal,
                    other_courses=other_course_names if other_course_names else None,
                    curated_candidates=candidates_map if candidates_map else None,
                )
            except Exception as exc:
                if fallback_on_ai_failure:
                    first_unresolved = queries_to_evaluate[0]
                    raise CourseResolutionError(
                        f"Course '{first_unresolved}' is not recognized in the knowledge base and AI assistance is currently unavailable ({exc}). "
                        "Please choose from the curated courses or verify your AI configuration."
                    ) from exc
                else:
                    if isinstance(exc, AIEngineError):
                        raise exc
                    raise LearningPathError(f"AI course evaluation failed: {exc}") from exc

            # Process evaluated courses
            for eval_item in evaluations:
                query = eval_item["query"]
                is_plausible = eval_item.get("is_plausible", False)
                is_ambiguous = eval_item.get("is_ambiguous", False)
                resolved_from_context = eval_item.get("resolved_from_context", False)
                selected_candidate_id = eval_item.get("selected_candidate_id")
                clarification = eval_item.get("clarification")

                if not is_plausible:
                    raise CourseResolutionError(
                        f"Course '{query}' is not recognized as a valid academic course or subject.",
                        query=query,
                    )

                if is_ambiguous and not resolved_from_context:
                    clarif_msg = clarification or "matches multiple broad disciplines"
                    cand_options = []
                    if query in candidates_map:
                        cand_options = [c["name"] for c in candidates_map[query]]
                    raise CourseResolutionError(
                        f"Course query '{query}' is ambiguous: {clarif_msg}. Please provide a more specific academic course name.",
                        query=query,
                        needs_clarification=True,
                        clarification=clarif_msg,
                        candidates=cand_options,
                    )

                # Context-aware resolution: check if AI picked a curated candidate
                if selected_candidate_id and target_kb.get_course(selected_candidate_id):
                    cand_course = dict(target_kb.get_course(selected_candidate_id))
                    cid = selected_candidate_id
                    if cid not in seen_ids:
                        seen_ids.add(cid)
                        cand_course["source"] = "curated"
                        cand_course["is_curated"] = True
                        cand_course["is_ai_inferred"] = False
                        cand_course["provenance"] = "ai_disambiguated"
                        resolved_courses.append(cand_course)
                        resolution_status_str = "ai_disambiguated"
                        warnings.append(
                            f"Course '{query}' was disambiguated as curated course '{cand_course['name']}' via Google Gemini."
                        )
                else:
                    # Check if canonical_name maps cleanly to a known KB course
                    kb_match = target_kb.resolve_course(eval_item.get("canonical_name", ""))
                    if kb_match.is_resolved and kb_match.course is not None:
                        cid = kb_match.course_id
                        if cid and cid not in seen_ids:
                            seen_ids.add(cid)
                            course_data = dict(kb_match.course)
                            course_data["source"] = "curated"
                            course_data["is_curated"] = True
                            course_data["is_ai_inferred"] = False
                            course_data["provenance"] = "ai_disambiguated"
                            resolved_courses.append(course_data)
                            resolution_status_str = "ai_disambiguated"
                            warnings.append(
                                f"Course '{query}' was resolved to curated course '{course_data['name']}' via Google Gemini."
                            )
                    else:
                        # Legitimate new course inferred by AI
                        cid = eval_item["course_id"]
                        base_cid = cid
                        counter = 1
                        while cid in seen_ids or target_kb.get_course(cid) is not None:
                            cid = f"{base_cid}_{counter}"
                            counter += 1

                        seen_ids.add(cid)
                        canonical_name = eval_item["canonical_name"]
                        inferred_course = {
                            "course_id": cid,
                            "name": canonical_name,
                            "category": eval_item.get("category", "General Computer Science"),
                            "difficulty": eval_item.get("difficulty", "intermediate"),
                            "description": eval_item.get("description", f"AI-inferred academic course: {canonical_name}"),
                            "aliases": [query],
                            "source": "ai_inferred",
                            "is_curated": False,
                            "is_ai_inferred": True,
                            "provenance": "ai_inferred_candidate",
                        }
                        resolved_courses.append(inferred_course)
                        if resolution_status_str != "ai_disambiguated":
                            resolution_status_str = "ai_inferred"

                        if resolved_from_context:
                            warnings.append(
                                f"Course '{query}' was resolved as '{canonical_name}' via Google Gemini based on your learning goal '{learning_goal or 'General Computer Science'}'."
                            )
                        else:
                            warnings.append(
                                f"Course '{query}' was inferred as '{canonical_name}' via Google Gemini (candidate subject, not in curated Knowledge Base)."
                            )

    if not resolved_courses:
        raise CourseResolutionError("No valid courses could be resolved from input.")

    selected_ids = {c["course_id"] for c in resolved_courses}

    # 4. Retrieve relevant curated relationships from Knowledge Base
    curated_prereqs: List[Dict[str, Any]] = []
    for r in target_kb.get_prerequisites():
        src = r.get("source_course_id")
        tgt = r.get("target_course_id")
        if src in selected_ids and tgt in selected_ids:
            item = dict(r)
            item["source"] = "curated"
            item["is_ai_proposed"] = False
            item["evidence_type"] = r.get("evidence_type", "expert_curated")
            item["confidence"] = r.get("confidence")
            curated_prereqs.append(item)

    # 5. Request additional prerequisite proposals from AI Engine
    ai_proposals: List[Dict[str, Any]] = []
    ai_used = False
    proposal_request_status = "disabled" if not use_ai else "skipped"
    proposals_received_count = 0
    proposals_accepted_count = 0
    proposals_rejected_count = 0
    proposal_message = ""

    if use_ai:
        if len(selected_ids) < 2:
            proposal_request_status = "skipped"
            proposal_message = "AI prerequisite analysis was skipped because only a single distinct course was resolved."
            warnings.append(
                "AI prerequisite analysis was skipped because only a single distinct course was resolved. "
                "At least two courses are required to establish prerequisite dependencies."
            )
        else:
            try:
                raw_proposals = request_prerequisite_proposals(
                    learning_goal=learning_goal or "General Computer Science",
                    courses=resolved_courses,
                    existing_prerequisites=curated_prereqs,
                    client=ai_client,
                    model=settings.gemini_model,
                    timeout=settings.gemini_timeout,
                )
                proposal_request_status = "succeeded"
                validation_errors = getattr(raw_proposals, "validation_errors", [])
                total_received = getattr(raw_proposals, "total_received", len(raw_proposals) + len(validation_errors))
                proposals_received_count = total_received
                proposals_rejected_count = len(validation_errors)

                for err in validation_errors:
                    warnings.append(f"AI proposal rejected during validation: {err}")

                for p in raw_proposals:
                    item = dict(p)
                    item["source"] = "ai_proposed"
                    item["is_ai_proposed"] = True
                    item["evidence_type"] = "llm_proposed"
                    item["confidence"] = p.get("confidence")
                    ai_proposals.append(item)

                proposals_accepted_count = len(ai_proposals)

                if ai_proposals:
                    ai_used = True
                    proposal_message = f"AI analysis completed successfully. {len(ai_proposals)} additional relationship(s) accepted."
                else:
                    if validation_errors:
                        proposal_message = "AI analysis completed, but all proposals were rejected during validation."
                        warnings.append(
                            "AI analysis completed, but all proposed relationships were rejected during validation against the course catalog."
                        )
                    else:
                        proposal_message = "AI analysis completed successfully. No additional prerequisite relationships were proposed beyond the curated Knowledge Base."
                        warnings.append(
                            "AI analysis completed successfully, but no additional prerequisite relationships were proposed beyond the curated Knowledge Base."
                        )
            except Exception as exc:
                proposal_request_status = "failed"
                proposal_message = f"AI proposals were unavailable ({exc}). Proceeding with curated Knowledge Base relationships only."
                if fallback_on_ai_failure:
                    ai_used = False
                    warnings.append(
                        f"AI proposals were unavailable ({exc}). Proceeding with curated Knowledge Base relationships only."
                    )
                else:
                    if isinstance(exc, AIEngineError):
                        raise exc
                    raise LearningPathError(f"AI proposal generation failed: {exc}") from exc
    else:
        proposal_request_status = "disabled"
        proposal_message = "AI assistance was disabled. Curated knowledge base relationships used."
        warnings.append("AI assistance was disabled. Proceeding with curated Knowledge Base relationships only.")

    # 6. In-memory combination of relationships (courses.json is untouched)
    all_relationships: List[Dict[str, Any]] = list(curated_prereqs) + list(ai_proposals)

    # 7. Graph construction and cycle verification
    graph = DirectedGraph(selected_ids)
    for r in all_relationships:
        graph.add_edge(r["source_course_id"], r["target_course_id"])

    has_cycle, cycle_path = detect_cycle_dfs(graph)
    if has_cycle:
        raise CycleConflictError(
            f"Cyclic dependency detected among selected courses: {' -> '.join(cycle_path)}. "
            "A valid learning order cannot be formed until conflicting relationships are resolved.",
            cycle_path=cycle_path,
        )

    # 8. Deterministic topological sorting via Kahn's algorithm
    ordered_ids = topological_sort_kahn(graph)

    if not verify_topological_order(graph, ordered_ids):
        raise CycleConflictError("Topological ordering verification failed.")

    # 9. Pedagogical wave scheduling and curricular constraint optimization
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
            required_semesters=exc.required_semesters,
            max_semesters=exc.max_semesters,
            constraint_type=exc.constraint_type,
        ) from exc

    if not verify_semester_schedule(
        schedule_result=schedule_result,
        relationships=all_relationships,
        max_courses_per_semester=max_courses_per_semester,
        max_semesters=max_semesters,
    ):
        raise CurricularConstraintError("Semester schedule verification failed mathematical validation.")

    # 10. Transparent AI Execution Summary
    ai_summary = {
        "requested": use_ai,
        "course_resolution_status": resolution_status_str,
        "unknown_courses_evaluated": unknown_evaluated_count,
        "ambiguous_courses_evaluated": ambiguous_evaluated_count,
        "proposal_request_status": proposal_request_status,
        "proposals_received": proposals_received_count,
        "proposals_accepted": proposals_accepted_count,
        "proposals_rejected": proposals_rejected_count,
        "relationships_added": len(ai_proposals),
        "model": settings.gemini_model if use_ai else None,
        "message": proposal_message,
    }

    return {
        "learning_goal": (learning_goal or "General Computer Science").strip(),
        "selected_courses": resolved_courses,
        "ordered_courses": schedule_result["ordered_courses"],
        "semesters": schedule_result["semesters"],
        "prerequisites": all_relationships,
        "ai_proposals_used": ai_used,
        "warnings": warnings,
        "ai_summary": ai_summary,
    }
