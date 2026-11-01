from collections import defaultdict
import heapq
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union


class CycleError(ValueError):
    """Raised when a directed graph contains a cycle and cannot be topologically sorted."""

    def __init__(
        self,
        message: str,
        cycle_nodes: Optional[List[str]] = None,
        unprocessed_nodes: Optional[List[str]] = None,
    ):
        super().__init__(message)
        self.cycle_nodes: List[str] = cycle_nodes or []
        self.unprocessed_nodes: List[str] = unprocessed_nodes or []


class DirectedGraph:
    """Explicit adjacency-list directed graph representing courses and prerequisite dependencies.

    Edge convention: source -> target means source is a PREREQUISITE for target.
    """

    def __init__(self, vertices: Optional[Iterable[str]] = None):
        self._vertices: Set[str] = set()
        self._adjacency: Dict[str, List[str]] = defaultdict(list)
        self._in_degree: Dict[str, int] = defaultdict(int)
        self._edges: Set[Tuple[str, str]] = set()

        if vertices is not None:
            for v in vertices:
                self.add_vertex(v)

    def add_vertex(self, vertex: str) -> None:
        """Adds a vertex to the graph if not already present."""
        if vertex not in self._vertices:
            self._vertices.add(vertex)
            if vertex not in self._adjacency:
                self._adjacency[vertex] = []
            if vertex not in self._in_degree:
                self._in_degree[vertex] = 0

    def add_edge(self, source: str, target: str) -> bool:
        """Adds a directed edge source -> target (source is prerequisite for target).

        Returns True if the edge was newly added, False if duplicate.
        """
        self.add_vertex(source)
        self.add_vertex(target)

        pair = (source, target)
        if pair in self._edges:
            return False

        self._edges.add(pair)
        self._adjacency[source].append(target)
        self._in_degree[target] += 1
        return True

    @property
    def vertices(self) -> List[str]:
        """Returns all vertices sorted lexicographically."""
        return sorted(self._vertices)

    @property
    def edges(self) -> Set[Tuple[str, str]]:
        """Returns the set of directed edges (source, target)."""
        return set(self._edges)

    @property
    def num_vertices(self) -> int:
        return len(self._vertices)

    @property
    def num_edges(self) -> int:
        return len(self._edges)

    def has_vertex(self, vertex: str) -> bool:
        return vertex in self._vertices

    def has_edge(self, source: str, target: str) -> bool:
        return (source, target) in self._edges

    def get_neighbors(self, vertex: str) -> List[str]:
        """Returns outgoing neighbors (courses that depend on this vertex)."""
        return list(self._adjacency.get(vertex, []))

    def get_in_degree(self, vertex: str) -> int:
        """Returns the in-degree (number of direct prerequisites) for this vertex."""
        return self._in_degree.get(vertex, 0)

    def get_adjacency_list(self) -> Dict[str, List[str]]:
        """Returns a copy of the adjacency list."""
        return {v: list(self._adjacency.get(v, [])) for v in sorted(self._vertices)}

    def get_in_degrees(self) -> Dict[str, int]:
        """Returns a copy of all in-degrees."""
        return {v: self._in_degree.get(v, 0) for v in sorted(self._vertices)}


def build_graph(
    vertices: Iterable[str],
    edges: Iterable[Union[Tuple[str, str], Dict[str, Any]]],
    strict: bool = True,
) -> DirectedGraph:
    """Builds a DirectedGraph from an iterable of vertices and edges.

    If strict is True, edges with endpoints not in vertices raise KeyError.
    """
    vertex_set = set(vertices)
    graph = DirectedGraph(vertex_set)

    for edge in edges:
        if isinstance(edge, (tuple, list)) and len(edge) == 2:
            src, tgt = edge[0], edge[1]
        elif isinstance(edge, dict):
            src = edge.get("source_course_id") or edge.get("from")
            tgt = edge.get("target_course_id") or edge.get("to")
        else:
            raise ValueError(f"Invalid edge format: {edge}")

        if strict and (src not in vertex_set or tgt not in vertex_set):
            missing = [node for node in (src, tgt) if node not in vertex_set]
            raise KeyError(f"Edge references unregistered vertex: {missing}")

        graph.add_edge(src, tgt)

    return graph


def build_graph_from_kb(
    kb_data: Any,
    selected_course_ids: Optional[Iterable[str]] = None,
) -> DirectedGraph:
    """Constructs a DirectedGraph directly from a KnowledgeBase instance or dictionary.

    If selected_course_ids is provided, constructs the induced subgraph for only those courses.
    """
    if hasattr(kb_data, "get_all_courses") and hasattr(kb_data, "get_prerequisites"):
        courses = kb_data.get_all_courses()
        prereqs = kb_data.get_prerequisites()
    elif isinstance(kb_data, dict):
        courses = kb_data.get("courses", [])
        prereqs = kb_data.get("prerequisites", [])
    else:
        raise TypeError(f"Expected KnowledgeBase or dict, got {type(kb_data).__name__}")

    all_ids = {c["course_id"] for c in courses if isinstance(c, dict) and "course_id" in c}

    if selected_course_ids is not None:
        target_ids = set(selected_course_ids)
        unknown = target_ids - all_ids
        if unknown:
            raise KeyError(f"Selected course IDs not found in knowledge base: {sorted(unknown)}")
    else:
        target_ids = all_ids

    graph = DirectedGraph(target_ids)

    for r in prereqs:
        if not isinstance(r, dict):
            continue
        src = r.get("source_course_id")
        tgt = r.get("target_course_id")
        if src in target_ids and tgt in target_ids:
            graph.add_edge(src, tgt)

    return graph


def topological_sort_kahn(graph: DirectedGraph) -> List[str]:
    """Computes a topological ordering using Kahn's algorithm with min-heap tie-breaking.

    Deterministic tie-breaking: when multiple vertices have in-degree 0, they are chosen
    in alphabetical (lexicographical) order.

    Time Complexity: O((V + E) + V log V) worst-case time bound with min-heap tie-breaking
    (O(V log V) for heap push/pop operations across V vertices plus O(E) for visiting incident edges).
    Space Complexity: O(V + E)

    Raises CycleError if the graph contains a directed cycle.
    """
    in_degrees = graph.get_in_degrees()
    adjacency = graph.get_adjacency_list()

    # Min-heap of vertices with in-degree 0
    zero_in_degree_heap = [v for v, deg in in_degrees.items() if deg == 0]
    heapq.heapify(zero_in_degree_heap)

    order: List[str] = []
    remaining_in_degrees = dict(in_degrees)

    while zero_in_degree_heap:
        u = heapq.heappop(zero_in_degree_heap)
        order.append(u)

        for neighbor in adjacency.get(u, []):
            remaining_in_degrees[neighbor] -= 1
            if remaining_in_degrees[neighbor] == 0:
                heapq.heappush(zero_in_degree_heap, neighbor)

    if len(order) != graph.num_vertices:
        unprocessed = sorted([v for v in graph.vertices if v not in order])
        has_cycle, cycle_path = detect_cycle_dfs(graph)
        actual_cycle_nodes = sorted(set(cycle_path)) if has_cycle else list(unprocessed)
        downstream = [v for v in unprocessed if v not in actual_cycle_nodes]

        if downstream:
            msg = (
                f"Kahn's topological sort failed: cycle detected involving {actual_cycle_nodes} "
                f"({len(downstream)} downstream node(s) could not be processed: {downstream})."
            )
        else:
            msg = f"Kahn's topological sort failed: cycle detected involving {actual_cycle_nodes}."

        raise CycleError(
            msg,
            cycle_nodes=actual_cycle_nodes,
            unprocessed_nodes=unprocessed,
        )

    return order


def detect_cycle_dfs(graph: DirectedGraph) -> Tuple[bool, List[str]]:
    """Detects cycles in a directed graph using Depth-First Search with 3-state coloring.

    States:
      0: WHITE (unvisited)
      1: GRAY  (currently visiting / on active recursion stack)
      2: BLACK (visited / finished)

    Returns (has_cycle, cycle_path).
    If a cycle exists, cycle_path contains the sequence of vertices forming the cycle.

    Time Complexity: O(V log V + E) due to deterministic sorted vertex traversal
    Space Complexity: O(V)
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    state: Dict[str, int] = {v: WHITE for v in graph.vertices}
    parent: Dict[str, str] = {}
    adjacency = graph.get_adjacency_list()

    for start_node in graph.vertices:
        if state[start_node] != WHITE:
            continue

        stack = [(start_node, 0)]  # (node, next_neighbor_index)
        state[start_node] = GRAY

        while stack:
            u, nbr_idx = stack[-1]
            neighbors = adjacency.get(u, [])

            if nbr_idx < len(neighbors):
                v = neighbors[nbr_idx]
                stack[-1] = (u, nbr_idx + 1)

                if state[v] == GRAY:
                    # Back edge detected: cycle found!
                    cycle = [v]
                    # Backtrack up the active stack
                    for node, _ in reversed(stack):
                        cycle.append(node)
                        if node == v:
                            break
                    cycle.reverse()
                    return True, cycle

                elif state[v] == WHITE:
                    state[v] = GRAY
                    parent[v] = u
                    stack.append((v, 0))
            else:
                state[u] = BLACK
                stack.pop()

    return False, []


def topological_sort_dfs(graph: DirectedGraph) -> List[str]:
    """Computes a topological ordering using Depth-First Search (post-order reversal).

    Time Complexity: O(V log V + E) due to deterministic sorted vertex traversal
    Space Complexity: O(V + E)

    Raises CycleError if the graph contains a directed cycle.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    state: Dict[str, int] = {v: WHITE for v in graph.vertices}
    adjacency = graph.get_adjacency_list()
    post_order: List[str] = []

    for start_node in graph.vertices:
        if state[start_node] != WHITE:
            continue

        stack = [(start_node, 0)]
        state[start_node] = GRAY

        while stack:
            u, nbr_idx = stack[-1]
            neighbors = adjacency.get(u, [])

            if nbr_idx < len(neighbors):
                v = neighbors[nbr_idx]
                stack[-1] = (u, nbr_idx + 1)

                if state[v] == GRAY:
                    cycle = [v]
                    for node, _ in reversed(stack):
                        cycle.append(node)
                        if node == v:
                            break
                    cycle.reverse()
                    raise CycleError(
                        f"DFS topological sort failed: cycle detected along path {' -> '.join(cycle)}",
                        cycle_nodes=cycle,
                    )

                elif state[v] == WHITE:
                    state[v] = GRAY
                    stack.append((v, 0))
            else:
                state[u] = BLACK
                post_order.append(u)
                stack.pop()

    # Reversing post-order yields topological order (prerequisite before dependent)
    return list(reversed(post_order))


def verify_topological_order(graph: DirectedGraph, order: List[str]) -> bool:
    """Verifies that an ordering is a mathematically valid topological order for graph."""
    if len(order) != graph.num_vertices or set(order) != set(graph.vertices):
        return False

    pos = {node: idx for idx, node in enumerate(order)}
    for src, tgt in graph.edges:
        if pos[src] >= pos[tgt]:
            return False

    return True
