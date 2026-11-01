import pytest

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
from backend.knowledge_base.knowledge_base import load_knowledge_base


# --- Graph Construction & Basics ---

def test_empty_graph():
    graph = DirectedGraph()
    assert graph.num_vertices == 0
    assert graph.num_edges == 0

    has_cycle, cycle = detect_cycle_dfs(graph)
    assert not has_cycle
    assert cycle == []
    assert topological_sort_kahn(graph) == []
    assert topological_sort_dfs(graph) == []


def test_isolated_vertices():
    graph = DirectedGraph(["course_b", "course_a", "course_c"])
    assert graph.num_vertices == 3
    assert graph.num_edges == 0

    has_cycle, _ = detect_cycle_dfs(graph)
    assert not has_cycle

    # Kahn ordering must deterministically sort isolated vertices alphabetically
    kahn_order = topological_sort_kahn(graph)
    assert kahn_order == ["course_a", "course_b", "course_c"]
    assert verify_topological_order(graph, kahn_order)

    dfs_order = topological_sort_dfs(graph)
    assert verify_topological_order(graph, dfs_order)


def test_edge_direction_and_in_degrees():
    # Convention: source (prerequisite) -> target (dependent)
    graph = DirectedGraph()
    assert graph.add_edge("programming_fundamentals", "python_programming")

    assert graph.get_in_degree("programming_fundamentals") == 0
    assert graph.get_in_degree("python_programming") == 1
    assert graph.get_neighbors("programming_fundamentals") == ["python_programming"]
    assert graph.get_neighbors("python_programming") == []


def test_duplicate_edge_handling():
    graph = DirectedGraph()
    assert graph.add_edge("math", "calculus") is True
    assert graph.add_edge("math", "calculus") is False  # Duplicate

    assert graph.num_edges == 1
    assert graph.get_in_degree("calculus") == 1
    assert graph.get_neighbors("math") == ["calculus"]


def test_build_graph_strict_missing_endpoint():
    with pytest.raises(KeyError, match="unregistered vertex"):
        build_graph(
            vertices=["course_a"],
            edges=[("course_a", "course_b")],
            strict=True,
        )


# --- Disconnected Components & Deterministic Tie-Breaking ---

def test_disconnected_components():
    # Component 1: c1 -> c2
    # Component 2: d1 -> d2
    # Isolated: e0
    vertices = ["c1", "c2", "d1", "d2", "e0"]
    edges = [("c1", "c2"), ("d1", "d2")]
    graph = build_graph(vertices, edges)

    kahn_order = topological_sort_kahn(graph)
    dfs_order = topological_sort_dfs(graph)

    assert verify_topological_order(graph, kahn_order)
    assert verify_topological_order(graph, dfs_order)

    # In Kahn, c1, d1, e0 all start with in-degree 0.
    # Min-heap tie-breaking must pick c1 first.
    assert kahn_order[0] == "c1"


def test_kahn_deterministic_tie_breaking():
    # Diamond graph:
    #       root
    #      /    \
    #    b_node  a_node
    #      \    /
    #       sink
    vertices = ["root", "b_node", "a_node", "sink"]
    edges = [
        ("root", "b_node"),
        ("root", "a_node"),
        ("b_node", "sink"),
        ("a_node", "sink"),
    ]
    graph = build_graph(vertices, edges)

    # After root is popped, a_node and b_node have in-degree 0.
    # Min-heap must select a_node before b_node.
    order = topological_sort_kahn(graph)
    assert order == ["root", "a_node", "b_node", "sink"]
    assert verify_topological_order(graph, order)


# --- Cycle Detection & Error Reporting ---

def test_self_loop_detection():
    graph = DirectedGraph()
    graph.add_edge("course_a", "course_a")

    has_cycle, cycle = detect_cycle_dfs(graph)
    assert has_cycle
    assert "course_a" in cycle

    with pytest.raises(CycleError) as exc_kahn:
        topological_sort_kahn(graph)
    assert "course_a" in exc_kahn.value.cycle_nodes

    with pytest.raises(CycleError) as exc_dfs:
        topological_sort_dfs(graph)
    assert "course_a" in exc_dfs.value.cycle_nodes


def test_two_node_cycle_detection():
    graph = DirectedGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "a")

    has_cycle, cycle = detect_cycle_dfs(graph)
    assert has_cycle
    assert len(cycle) >= 2

    with pytest.raises(CycleError):
        topological_sort_kahn(graph)

    with pytest.raises(CycleError):
        topological_sort_dfs(graph)


def test_multi_node_cycle_detection():
    # a -> b -> c -> d -> b
    graph = build_graph(
        vertices=["a", "b", "c", "d", "e"],
        edges=[("a", "b"), ("b", "c"), ("c", "d"), ("d", "b"), ("d", "e")],
    )

    has_cycle, cycle = detect_cycle_dfs(graph)
    assert has_cycle
    assert any(n in cycle for n in ["b", "c", "d"])

    with pytest.raises(CycleError) as exc_info:
        topological_sort_kahn(graph)
    assert set(exc_info.value.cycle_nodes) == {"b", "c", "d"}
    assert "e" not in exc_info.value.cycle_nodes
    assert set(exc_info.value.unprocessed_nodes) == {"b", "c", "d", "e"}

    with pytest.raises(CycleError):
        topological_sort_dfs(graph)


def test_kahn_cycle_error_distinguishes_downstream_nodes():
    # Graph structure:
    # Cycle: c1 -> c2 -> c1
    # Downstream: c2 -> d1 -> d2
    # Independent: i1 (processed successfully because in-degree is 0)
    graph = build_graph(
        vertices=["c1", "c2", "d1", "d2", "i1"],
        edges=[("c1", "c2"), ("c2", "c1"), ("c2", "d1"), ("d1", "d2")],
    )

    with pytest.raises(CycleError) as exc_info:
        topological_sort_kahn(graph)

    err = exc_info.value
    # Actual cycle participants
    assert set(err.cycle_nodes) == {"c1", "c2"}
    assert "d1" not in err.cycle_nodes
    assert "d2" not in err.cycle_nodes
    # Downstream nodes unable to be processed
    assert set(err.unprocessed_nodes) == {"c1", "c2", "d1", "d2"}
    assert "downstream node(s) could not be processed" in str(err)


def test_dfs_and_kahn_agreement_on_cycles():
    # Acyclic graph: both succeed
    dag = build_graph(["x", "y", "z"], [("x", "y"), ("y", "z")])
    assert detect_cycle_dfs(dag)[0] is False
    kahn_order = topological_sort_kahn(dag)
    dfs_order = topological_sort_dfs(dag)
    assert verify_topological_order(dag, kahn_order)
    assert verify_topological_order(dag, dfs_order)

    # Cyclic graph: both fail
    cyclic = build_graph(["x", "y", "z"], [("x", "y"), ("y", "z"), ("z", "x")])
    assert detect_cycle_dfs(cyclic)[0] is True
    with pytest.raises(CycleError):
        topological_sort_kahn(cyclic)
    with pytest.raises(CycleError):
        topological_sort_dfs(cyclic)


# --- Full Knowledge Base Tests ---

def test_graph_from_actual_knowledge_base():
    kb = load_knowledge_base()
    graph = build_graph_from_kb(kb)

    assert graph.num_vertices == 70
    assert graph.num_edges == 115

    # Verify edge direction on real data
    # programming_fundamentals is prerequisite for c_programming
    assert graph.has_edge("programming_fundamentals", "c_programming")
    assert not graph.has_edge("c_programming", "programming_fundamentals")

    # Knowledge Base must be acyclic
    has_cycle, cycle = detect_cycle_dfs(graph)
    assert not has_cycle
    assert cycle == []

    # Run Kahn's algorithm
    kahn_order = topological_sort_kahn(graph)
    assert len(kahn_order) == 70
    assert verify_topological_order(graph, kahn_order)

    # Run DFS topological sort
    dfs_order = topological_sort_dfs(graph)
    assert len(dfs_order) == 70
    assert verify_topological_order(graph, dfs_order)

    # Verify that in BOTH orderings, EVERY single prerequisite precedes its dependent course
    kahn_pos = {cid: idx for idx, cid in enumerate(kahn_order)}
    dfs_pos = {cid: idx for idx, cid in enumerate(dfs_order)}

    for prereq in kb.get_prerequisites():
        src = prereq["source_course_id"]
        tgt = prereq["target_course_id"]
        assert kahn_pos[src] < kahn_pos[tgt], f"Kahn failed: {src} not before {tgt}"
        assert dfs_pos[src] < dfs_pos[tgt], f"DFS failed: {src} not before {tgt}"


def test_induced_subgraph_from_kb():
    kb = load_knowledge_base()
    selected = [
        "python_programming",
        "linear_algebra",
        "machine_learning",
        "deep_learning",
    ]
    graph = build_graph_from_kb(kb, selected_course_ids=selected)

    assert graph.num_vertices == 4
    # Check that edges exist between selected courses
    assert graph.has_edge("python_programming", "machine_learning")
    assert graph.has_edge("linear_algebra", "machine_learning")
    assert graph.has_edge("machine_learning", "deep_learning")

    order = topological_sort_kahn(graph)
    assert len(order) == 4
    assert verify_topological_order(graph, order)

    pos = {cid: idx for idx, cid in enumerate(order)}
    assert pos["python_programming"] < pos["machine_learning"]
    assert pos["linear_algebra"] < pos["machine_learning"]
    assert pos["machine_learning"] < pos["deep_learning"]


def test_induced_subgraph_with_unknown_course():
    kb = load_knowledge_base()
    with pytest.raises(KeyError, match="Selected course IDs not found"):
        build_graph_from_kb(kb, selected_course_ids=["python_programming", "nonexistent_course"])


# --- Level 6: Algorithm Hardening & Edge Cases ---

def test_single_vertex_graph_operations():
    g = DirectedGraph(["single_node"])
    assert g.num_vertices == 1
    assert g.num_edges == 0
    assert g.has_vertex("single_node") is True
    assert g.has_vertex("other") is False
    assert g.has_edge("single_node", "single_node") is False
    assert g.get_neighbors("single_node") == []
    assert g.get_in_degree("single_node") == 0
    assert g.get_adjacency_list() == {"single_node": []}
    assert g.get_in_degrees() == {"single_node": 0}

    has_cycle, cycle = detect_cycle_dfs(g)
    assert not has_cycle
    assert cycle == []

    kahn = topological_sort_kahn(g)
    assert kahn == ["single_node"]
    assert verify_topological_order(g, kahn) is True

    dfs = topological_sort_dfs(g)
    assert dfs == ["single_node"]
    assert verify_topological_order(g, dfs) is True


def test_mixed_isolated_and_connected_components():
    # Vertices: isolated i1, i2; connected c1 -> c2 -> c3
    g = build_graph(
        vertices=["i2", "c2", "i1", "c1", "c3"],
        edges=[("c1", "c2"), ("c2", "c3")],
    )
    assert g.num_vertices == 5
    assert g.num_edges == 2

    kahn = topological_sort_kahn(g)
    # in-degree 0 at start: c1, i1, i2. Min-heap order: c1, then i1, then i2
    assert kahn[0] == "c1"
    assert verify_topological_order(g, kahn) is True

    dfs = topological_sort_dfs(g)
    assert verify_topological_order(g, dfs) is True


def test_multiple_valid_toposorts_deterministic_kahn():
    # Diamond graph where multiple valid topological orders exist:
    # 1. root, a, b, sink
    # 2. root, b, a, sink
    g = build_graph(
        vertices=["root", "b", "a", "sink"],
        edges=[("root", "b"), ("root", "a"), ("b", "sink"), ("a", "sink")],
    )
    # Both are mathematically valid:
    assert verify_topological_order(g, ["root", "a", "b", "sink"]) is True
    assert verify_topological_order(g, ["root", "b", "a", "sink"]) is True

    # But Kahn must deterministically return 'a' before 'b' because 'a' < 'b'
    order1 = topological_sort_kahn(g)
    order2 = topological_sort_kahn(g)
    assert order1 == ["root", "a", "b", "sink"]
    assert order1 == order2


def test_build_graph_non_strict_adds_missing_vertices():
    # strict=False should dynamically register unknown endpoint vertices
    g = build_graph(
        vertices=["course_a"],
        edges=[("course_a", "course_b"), ("course_b", "course_c")],
        strict=False,
    )
    assert g.num_vertices == 3
    assert g.has_vertex("course_b")
    assert g.has_vertex("course_c")
    assert g.num_edges == 2
    assert verify_topological_order(g, topological_sort_kahn(g)) is True


def test_disconnected_graph_with_cycle_in_one_component():
    # Component 1 (acyclic): ok1 -> ok2
    # Component 2 (cyclic): cyc1 -> cyc2 -> cyc1
    g = build_graph(
        vertices=["ok1", "ok2", "cyc1", "cyc2"],
        edges=[("ok1", "ok2"), ("cyc1", "cyc2"), ("cyc2", "cyc1")],
    )
    has_cycle, cycle = detect_cycle_dfs(g)
    assert has_cycle is True
    assert set(cycle) == {"cyc1", "cyc2"}

    with pytest.raises(CycleError) as exc_kahn:
        topological_sort_kahn(g)
    assert set(exc_kahn.value.cycle_nodes) == {"cyc1", "cyc2"}
    assert "ok1" not in exc_kahn.value.cycle_nodes

    with pytest.raises(CycleError) as exc_dfs:
        topological_sort_dfs(g)
    assert set(exc_dfs.value.cycle_nodes) == {"cyc1", "cyc2"}


def test_large_deep_chain_no_recursion_error():
    # Deep chain of 1500 vertices: v0 -> v1 -> ... -> v1499
    # Tests that iterative DFS and Kahn do not exceed Python's recursion limit (default 1000)
    n = 1500
    vertices = [f"v{i:04d}" for i in range(n)]
    edges = [(vertices[i], vertices[i + 1]) for i in range(n - 1)]
    g = build_graph(vertices, edges)

    # 1. Cycle detection must not recurse or fail
    has_cycle, cycle = detect_cycle_dfs(g)
    assert has_cycle is False
    assert cycle == []

    # 2. Topological sort Kahn
    kahn = topological_sort_kahn(g)
    assert len(kahn) == n
    assert kahn == vertices
    assert verify_topological_order(g, kahn) is True

    # 3. Topological sort DFS (iterative implementation)
    dfs = topological_sort_dfs(g)
    assert len(dfs) == n
    assert dfs == vertices
    assert verify_topological_order(g, dfs) is True


def test_cycle_path_validity_and_closure():
    # Cycle: a -> b -> c -> d -> b (with attached inlet x -> a)
    g = build_graph(
        vertices=["x", "a", "b", "c", "d"],
        edges=[("x", "a"), ("a", "b"), ("b", "c"), ("c", "d"), ("d", "b")],
    )
    has_cycle, cycle_path = detect_cycle_dfs(g)
    assert has_cycle is True
    assert len(cycle_path) >= 2

    # Must close the cycle: first and last nodes match
    assert cycle_path[0] == cycle_path[-1]

    # Every consecutive pair must correspond to an actual directed edge in the graph
    for i in range(len(cycle_path) - 1):
        src = cycle_path[i]
        tgt = cycle_path[i + 1]
        assert g.has_edge(src, tgt), f"Edge ({src} -> {tgt}) not in graph!"


def test_verifier_rejects_edge_violation():
    g = build_graph(["a", "b"], [("a", "b")])
    # Reverse order violates the edge a -> b
    assert verify_topological_order(g, ["b", "a"]) is False


def test_verifier_rejects_missing_vertex():
    g = build_graph(["a", "b", "c"], [("a", "b"), ("b", "c")])
    assert verify_topological_order(g, ["a", "b"]) is False


def test_verifier_rejects_duplicate_vertex():
    g = build_graph(["a", "b"], [("a", "b")])
    assert verify_topological_order(g, ["a", "a"]) is False
    assert verify_topological_order(g, ["a", "b", "b"]) is False


def test_verifier_rejects_unexpected_vertex():
    g = build_graph(["a", "b"], [("a", "b")])
    assert verify_topological_order(g, ["a", "b", "intruder"]) is False
    assert verify_topological_order(g, ["a", "intruder"]) is False


def test_verifier_rejects_cyclic_graph():
    g = build_graph(["a", "b"], [("a", "b"), ("b", "a")])
    assert verify_topological_order(g, ["a", "b"]) is False
    assert verify_topological_order(g, ["b", "a"]) is False

