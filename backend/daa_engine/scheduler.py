"""DAA Logic Engine: Pedagogical course scheduler and curricular constraint optimizer.

Provides:
  1. Wave-based (DAG layer) curriculum scheduling.
  2. Workload capacity constraints (maximum courses per semester).
  3. Semester deadline feasibility checks (maximum total semesters).
  4. Pedagogical difficulty progression smoothing (beginner -> intermediate -> advanced).
  5. Distinction between hard 'required' dependencies and soft 'recommended'/'optional' edges.
  6. Mathematical verification of generated semester schedules.
"""

from typing import Any, Dict, List, Optional, Set, Tuple


class CurricularConstraintError(Exception):
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


DIFFICULTY_RANK: Dict[str, int] = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
}


def _validate_constraints(
    max_courses_per_semester: Optional[int],
    max_semesters: Optional[int],
) -> None:
    """Validates that constraint arguments are strictly positive integers."""
    if max_courses_per_semester is not None:
        if isinstance(max_courses_per_semester, bool) or not isinstance(max_courses_per_semester, int):
            raise CurricularConstraintError(
                f"Invalid constraint: 'max_courses_per_semester' must be an integer, got {type(max_courses_per_semester).__name__}.",
                constraint_type="type_error",
            )
        if max_courses_per_semester < 1:
            raise CurricularConstraintError(
                f"Invalid constraint: 'max_courses_per_semester' must be at least 1, got {max_courses_per_semester}.",
                constraint_type="value_error",
            )

    if max_semesters is not None:
        if isinstance(max_semesters, bool) or not isinstance(max_semesters, int):
            raise CurricularConstraintError(
                f"Invalid constraint: 'max_semesters' must be an integer, got {type(max_semesters).__name__}.",
                constraint_type="type_error",
            )
        if max_semesters < 1:
            raise CurricularConstraintError(
                f"Invalid constraint: 'max_semesters' must be at least 1, got {max_semesters}.",
                constraint_type="value_error",
            )


def schedule_courses(
    courses: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    max_courses_per_semester: Optional[int] = None,
    max_semesters: Optional[int] = None,
) -> Dict[str, Any]:
    """Schedules courses into semesters or waves respecting prerequisite constraints and capacity limits.

    Rules for Curricular Constraints:
      1. A 'required' prerequisite must be completed in a strictly earlier semester (s_prereq < s_target).
      2. A 'recommended' or 'optional' relationship allows concurrent enrollment in the same semester
         (s_prereq <= s_target), but if assigned to separate semesters, s_prereq < s_target.
      3. Within the same semester, recommended prerequisites strictly precede dependent courses.
      4. Workload Balancing (when max_courses_per_semester is set): Uses list-scheduling with priority:
         (critical_path_depth DESC, uncompleted_recommended_prereqs ASC, difficulty ASC, course_id ASC).
      5. Natural Wave Layering (when max_courses_per_semester is None): Groups courses into waves
         corresponding to their earliest valid completion term.
      6. Infeasibility Checking: If required semesters exceed max_semesters, raises CurricularConstraintError
         with actionable diagnostic details.

    Time Complexity:
      - Unconstrained Wave Scheduling (max_courses_per_semester is None):
        O(V log V + E) time, derived from O(V + E) wave layering followed by within-wave
        min-heap ordering summing to O(V log V + E).
      - Workload-Constrained List Scheduling (max_courses_per_semester is not None):
        O(V^2 log V + V * E) time general worst-case bound. In each of up to V course-selection
        iterations, candidate scanning evaluates required and soft prerequisite subset conditions
        across unassigned nodes taking O(V + E) per iteration (summing to O(V^2 + V * E)), and
        sorting eligible candidates takes O(V log V) per iteration (summing to O(V^2 log V)).
        Within-semester topological ordering takes O(V log V + E) total across all semesters.
        On sparse graphs where E = O(V), the bound simplifies to O(V^2 log V). On dense graphs
        where E = Theta(V^2), this reaches O(V^3).
    Auxiliary Space Complexity:
      O(V + E) auxiliary space for required/soft adjacency lists, incoming prerequisite sets,
      longest-path memoization tables, and semester grouping structures.
    """
    _validate_constraints(max_courses_per_semester, max_semesters)

    if not courses:
        return {
            "semesters": [],
            "total_semesters": 0,
            "course_to_semester": {},
            "ordered_courses": [],
        }

    course_map: Dict[str, Dict[str, Any]] = {c["course_id"]: dict(c) for c in courses}
    all_course_ids: Set[str] = set(course_map.keys())

    # Build required and soft dependency graphs restricted to selected courses
    required_adj: Dict[str, List[str]] = {cid: [] for cid in all_course_ids}
    required_incoming: Dict[str, Set[str]] = {cid: set() for cid in all_course_ids}

    soft_adj: Dict[str, List[str]] = {cid: [] for cid in all_course_ids}
    soft_incoming: Dict[str, Set[str]] = {cid: set() for cid in all_course_ids}

    all_adj: Dict[str, List[str]] = {cid: [] for cid in all_course_ids}
    all_incoming: Dict[str, Set[str]] = {cid: set() for cid in all_course_ids}

    for r in relationships:
        src = r.get("source_course_id")
        tgt = r.get("target_course_id")
        rel_type = (r.get("relationship_type") or "required").lower()

        if src in all_course_ids and tgt in all_course_ids:
            all_adj[src].append(tgt)
            all_incoming[tgt].add(src)

            if rel_type == "required":
                required_adj[src].append(tgt)
                required_incoming[tgt].add(src)
            elif rel_type in ("recommended", "optional"):
                soft_adj[src].append(tgt)
                soft_incoming[tgt].add(src)

    # -------------------------------------------------------------------------
    # Critical Path (Longest Path to Sink in Required DAG)
    # -------------------------------------------------------------------------
    depth_memo: Dict[str, int] = {}
    chain_memo: Dict[str, List[str]] = {}

    def get_longest_path(node: str) -> Tuple[int, List[str]]:
        if node in depth_memo:
            return depth_memo[node], chain_memo[node]

        max_d = 0
        best_subchain: List[str] = []
        for nbr in sorted(required_adj.get(node, [])):
            d, sub = get_longest_path(nbr)
            if d > max_d:
                max_d = d
                best_subchain = sub

        total_d = 1 + max_d
        chain = [node] + best_subchain
        depth_memo[node] = total_d
        chain_memo[node] = chain
        return total_d, chain

    max_req_chain_len = 0
    longest_chain: List[str] = []
    for cid in all_course_ids:
        d, ch = get_longest_path(cid)
        if d > max_req_chain_len:
            max_req_chain_len = d
            longest_chain = ch

    # Check immediate feasibility against max_semesters
    if max_semesters is not None:
        if max_req_chain_len > max_semesters:
            chain_str = " -> ".join(longest_chain)
            raise CurricularConstraintError(
                f"Curricular constraint conflict: required prerequisite chain ({chain_str}) "
                f"requires at least {max_req_chain_len} semesters, which exceeds the limit of {max_semesters} semester(s).",
                required_semesters=max_req_chain_len,
                max_semesters=max_semesters,
                constraint_type="prerequisite_depth_conflict",
            )

        if max_courses_per_semester is not None:
            min_semesters_by_capacity = (len(all_course_ids) + max_courses_per_semester - 1) // max_courses_per_semester
            if min_semesters_by_capacity > max_semesters:
                raise CurricularConstraintError(
                    f"Curricular constraint conflict: scheduling {len(all_course_ids)} courses with at most "
                    f"{max_courses_per_semester} course(s) per semester requires at least {min_semesters_by_capacity} "
                    f"semesters, which exceeds the limit of {max_semesters} semester(s).",
                    required_semesters=min_semesters_by_capacity,
                    max_semesters=max_semesters,
                    constraint_type="capacity_limit_conflict",
                )

    # -------------------------------------------------------------------------
    # Scheduling Execution
    # -------------------------------------------------------------------------
    scheduled_semesters: List[List[Dict[str, Any]]] = []
    course_to_semester: Dict[str, int] = {}
    completed: Set[str] = set()
    assigned: Set[str] = set()

    if max_courses_per_semester is None:
        # Case A: Natural Wave-Based Layering (DAG Layering)
        # wave[v] >= wave[u] + 1 for (u, v) in required
        # wave[v] >= wave[u] for (u, v) in soft
        wave_map: Dict[str, int] = {}

        def get_wave(node: str) -> int:
            if node in wave_map:
                return wave_map[node]

            req_prereqs = required_incoming.get(node, set())
            soft_prereqs = soft_incoming.get(node, set())

            w = 1
            if req_prereqs:
                w = max(w, 1 + max(get_wave(p) for p in req_prereqs))
            if soft_prereqs:
                w = max(w, max(get_wave(p) for p in soft_prereqs))

            wave_map[node] = w
            return w

        for cid in all_course_ids:
            get_wave(cid)

        total_waves = max(wave_map.values()) if wave_map else 0
        if max_semesters is not None and total_waves > max_semesters:
            raise CurricularConstraintError(
                f"Curricular constraint conflict: prerequisite requirements require at least "
                f"{total_waves} semesters, which exceeds the limit of {max_semesters} semester(s).",
                required_semesters=total_waves,
                max_semesters=max_semesters,
                constraint_type="prerequisite_depth_conflict",
            )

        # Group by wave
        waves_dict: Dict[int, List[str]] = {w: [] for w in range(1, total_waves + 1)}
        for cid, w in wave_map.items():
            waves_dict[w].append(cid)

        # Order courses within wave consistent with internal dependencies & difficulty
        for w in range(1, total_waves + 1):
            nodes = waves_dict[w]
            sub_order = _order_within_wave(nodes, all_adj, course_map)
            semester_courses = []
            for cid in sub_order:
                c_record = dict(course_map[cid])
                c_record["semester"] = w
                c_record["wave"] = w
                semester_courses.append(c_record)
                course_to_semester[cid] = w

            scheduled_semesters.append(semester_courses)

    else:
        # Case B: Workload-Constrained List Scheduling
        # At most max_courses_per_semester courses per term
        current_semester = 1
        while len(assigned) < len(all_course_ids):
            term_assigned: List[str] = []
            while (
                len(term_assigned) < max_courses_per_semester
                and (len(assigned) + len(term_assigned)) < len(all_course_ids)
            ):
                term_assigned_set = set(term_assigned)
                completed_with_term = completed | term_assigned_set

                # Candidate courses:
                # 1. Course must not be already assigned or selected in the current term.
                # 2. All required prerequisites must be completed in an earlier semester (< current_semester).
                # 3. All recommended/optional (soft) prerequisites must either have been completed
                #    in an earlier semester or be already selected earlier in the current semester.
                #    This guarantees a dependent course cannot be selected if its soft prerequisite
                #    is left for a later semester.
                current_available = [
                    cid
                    for cid in all_course_ids
                    if cid not in assigned
                    and cid not in term_assigned_set
                    and required_incoming[cid].issubset(completed)
                    and soft_incoming[cid].issubset(completed_with_term)
                ]

                if not current_available:
                    break

                # Pedagogical priority key:
                # 1. Critical path depth DESC (unblock future terms)
                # 2. Uncompleted soft prereqs count ASC (fewer missing soft prereqs first)
                # 3. Difficulty rank ASC (beginner -> intermediate -> advanced)
                # 4. Canonical course ID ASC (determinism)
                current_available.sort(
                    key=lambda x: (
                        -depth_memo.get(x, 1),
                        len(soft_incoming.get(x, set()) - completed_with_term),
                        DIFFICULTY_RANK.get(course_map[x].get("difficulty", "intermediate"), 2),
                        x,
                    )
                )

                term_assigned.append(current_available[0])

            if not term_assigned:
                # Safety break
                break

            # Order selected courses within the term respecting internal dependencies & difficulty
            sub_order = _order_within_wave(term_assigned, all_adj, course_map)

            term_courses = []
            for cid in sub_order:
                assigned.add(cid)
                c_record = dict(course_map[cid])
                c_record["semester"] = current_semester
                c_record["wave"] = current_semester
                term_courses.append(c_record)
                course_to_semester[cid] = current_semester

            scheduled_semesters.append(term_courses)
            completed.update(term_assigned)
            current_semester += 1

        total_terms = len(scheduled_semesters)
        if max_semesters is not None and total_terms > max_semesters:
            raise CurricularConstraintError(
                f"Curricular constraint conflict: scheduling with at most {max_courses_per_semester} "
                f"course(s) per semester required {total_terms} semesters, which exceeds the limit of {max_semesters} semester(s).",
                required_semesters=total_terms,
                max_semesters=max_semesters,
                constraint_type="capacity_limit_conflict",
            )

    # Build response format
    semesters_output = []
    flat_ordered_courses = []
    for s_idx, sem_courses in enumerate(scheduled_semesters, start=1):
        semesters_output.append({
            "semester_number": s_idx,
            "courses": sem_courses,
            "course_count": len(sem_courses),
        })
        flat_ordered_courses.extend(sem_courses)

    return {
        "semesters": semesters_output,
        "total_semesters": len(scheduled_semesters),
        "course_to_semester": course_to_semester,
        "ordered_courses": flat_ordered_courses,
    }


def _order_within_wave(
    nodes: List[str],
    adjacency: Dict[str, List[str]],
    course_map: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Orders a subset of courses sharing a wave to respect internal edges, difficulty, and ID."""
    if len(nodes) <= 1:
        return list(nodes)

    node_set = set(nodes)
    in_degree: Dict[str, int] = {n: 0 for n in nodes}
    for u in nodes:
        for v in adjacency.get(u, []):
            if v in node_set:
                in_degree[v] += 1

    import heapq
    # Priority tuple: (in_degree, difficulty_rank, course_id)
    ready: List[Tuple[int, int, str]] = []
    for n in nodes:
        if in_degree[n] == 0:
            diff = DIFFICULTY_RANK.get(course_map.get(n, {}).get("difficulty", "intermediate"), 2)
            heapq.heappush(ready, (0, diff, n))

    ordered: List[str] = []
    while ready:
        _, _, u = heapq.heappop(ready)
        ordered.append(u)
        for v in adjacency.get(u, []):
            if v in node_set:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    diff = DIFFICULTY_RANK.get(course_map.get(v, {}).get("difficulty", "intermediate"), 2)
                    heapq.heappush(ready, (0, diff, v))

    if len(ordered) < len(nodes):
        for n in nodes:
            if n not in ordered:
                ordered.append(n)

    return ordered


def verify_semester_schedule(
    schedule_result: Dict[str, Any],
    relationships: List[Dict[str, Any]],
    max_courses_per_semester: Optional[int] = None,
    max_semesters: Optional[int] = None,
) -> bool:
    """Mathematically verifies that a computed semester schedule satisfies all curricular constraints
    and maintains cross-representation structural consistency.

    Verifies:
      1. Structural representation consistency:
         - Each semester group has sequential 1-indexed semester_number matching its position.
         - Each semester group's course_count matches the actual length of its courses list.
         - Every course in semester groups has matching 'semester' attribute.
         - The course_to_semester mapping strictly agrees with each course's semester group.
         - Flattened ordered_courses matches the exact sequence of courses across semester groups.
         - Every course appears exactly once across semester groups and ordered_courses.
         - total_semesters agrees with len(semesters).
      2. For every 'required' relationship (u -> v), semester[u] < semester[v].
      3. For every 'recommended' or 'optional' relationship (u -> v), semester[u] <= semester[v],
         and if semester[u] == semester[v], position[u] < position[v] in the flattened order.
      4. If max_courses_per_semester is specified, no semester contains more than the limit.
      5. If max_semesters is specified, total_semesters <= max_semesters.

    Time Complexity: O(V + E) where V is the total number of scheduled courses and E is the
    number of prerequisite relationships. Traverses semester groups and ordered courses in O(V)
    and verifies all relationship edge constraints in O(E).
    Auxiliary Space Complexity: O(V) auxiliary space for ID lists and position lookup map.
    """
    if not isinstance(schedule_result, dict):
        return False

    semesters = schedule_result.get("semesters")
    if not isinstance(semesters, list):
        return False

    course_to_sem = schedule_result.get("course_to_semester")
    if not isinstance(course_to_sem, dict):
        return False

    ordered_courses = schedule_result.get("ordered_courses")
    if not isinstance(ordered_courses, list):
        return False

    # Check total_semesters consistency if present
    if "total_semesters" in schedule_result:
        if schedule_result["total_semesters"] != len(semesters):
            return False

    group_course_ids: List[str] = []
    for idx, sem in enumerate(semesters, start=1):
        if not isinstance(sem, dict):
            return False

        if sem.get("semester_number") != idx:
            return False

        sem_courses = sem.get("courses")
        if not isinstance(sem_courses, list):
            return False

        if sem.get("course_count") != len(sem_courses):
            return False

        if max_courses_per_semester is not None and len(sem_courses) > max_courses_per_semester:
            return False

        for c in sem_courses:
            if not isinstance(c, dict) or "course_id" not in c:
                return False
            cid = c["course_id"]
            if c.get("semester") != idx:
                return False
            if course_to_sem.get(cid) != idx:
                return False
            group_course_ids.append(cid)

    # Check uniqueness across semester groups
    if len(group_course_ids) != len(set(group_course_ids)):
        return False

    # Extract ordered course IDs from flattened ordered_courses
    ordered_ids: List[str] = []
    for c in ordered_courses:
        if not isinstance(c, dict) or "course_id" not in c:
            return False
        cid = c["course_id"]
        if c.get("semester") != course_to_sem.get(cid):
            return False
        ordered_ids.append(cid)

    # Flattened ordered_courses must match group_course_ids exactly in content and order
    if group_course_ids != ordered_ids:
        return False

    # Completeness and bijection with course_to_sem
    if set(ordered_ids) != set(course_to_sem.keys()):
        return False
    if len(ordered_ids) != len(course_to_sem):
        return False

    # Max semesters constraint
    if max_semesters is not None and len(semesters) > max_semesters:
        return False

    # Position map for within-semester order
    pos_map = {cid: idx for idx, cid in enumerate(ordered_ids)}

    # Dependency assertions
    for r in relationships:
        if not isinstance(r, dict):
            continue
        src = r.get("source_course_id")
        tgt = r.get("target_course_id")
        rel_type = (r.get("relationship_type") or "required").lower()

        if src in course_to_sem and tgt in course_to_sem:
            s_src = course_to_sem[src]
            s_tgt = course_to_sem[tgt]

            if rel_type == "required":
                # Strict hard precedence across terms
                if s_src >= s_tgt:
                    return False
            else:
                # Soft relationship: src must not be in a strictly later semester than tgt
                if s_src > s_tgt:
                    return False
                # If in same semester, src must precede tgt linearly
                if s_src == s_tgt and pos_map[src] >= pos_map[tgt]:
                    return False

    return True
