"""DAA Logic Engine: Graph algorithms for prerequisite validation, cycle detection, and topological sorting."""

from backend.daa_engine.graph import (
    CycleError,
    DirectedGraph,
    build_graph,
    build_graph_from_kb,
    detect_cycle_dfs,
    topological_sort_dfs,
    topological_sort_kahn,
    verify_topological_order,
)
from backend.daa_engine.scheduler import (
    CurricularConstraintError,
    schedule_courses,
    verify_semester_schedule,
)

__all__ = [
    "CurricularConstraintError",
    "CycleError",
    "DirectedGraph",
    "build_graph",
    "build_graph_from_kb",
    "detect_cycle_dfs",
    "schedule_courses",
    "topological_sort_dfs",
    "topological_sort_kahn",
    "verify_semester_schedule",
    "verify_topological_order",
]
