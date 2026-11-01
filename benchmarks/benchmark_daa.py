"""Reproducible DAA Performance Benchmark Suite.

Benchmarks:
  1. Kahn's Topological Sort (with min-heap tie-breaking)
  2. Iterative DFS Cycle Detection (3-state coloring)
  3. DFS-Based Topological Sort (post-order reversal)
  4. Topological Order Verification

Across Graph Structures:
  - Sparse DAG
  - Dense DAG (~10% of all possible forward edges)
  - Linear Chain
  - Disconnected DAG (multi-component)
  - Cyclic Graph (embedded directed loop)

Across Sizes:
  - V = 10, 100, 500, 1000

Guarantees:
  - Correctness verification is performed BEFORE timing.
  - Graph construction is strictly isolated from algorithm timing.
  - Deterministic random seed (42).
  - High-resolution timing (time.perf_counter) with warm-up runs and median aggregation.
"""

import os
import platform
import random
import statistics
import sys
import time
from typing import Any, Callable, Dict, List, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.daa_engine.graph import (
    CycleError,
    DirectedGraph,
    build_graph,
    detect_cycle_dfs,
    topological_sort_dfs,
    topological_sort_kahn,
    verify_topological_order,
)


def generate_sparse_dag(v_count: int, seed: int = 42) -> DirectedGraph:
    """Generates a sparse DAG with approx 1.5 * V edges."""
    rng = random.Random(seed)
    vertices = [f"c_{i:04d}" for i in range(v_count)]
    graph = DirectedGraph(vertices)

    target_edges = int(v_count * 1.5)
    added = 0
    attempts = 0
    max_attempts = target_edges * 10

    while added < target_edges and attempts < max_attempts:
        attempts += 1
        i = rng.randint(0, v_count - 2)
        j = rng.randint(i + 1, v_count - 1)  # Strictly i < j guarantees acyclic
        if graph.add_edge(vertices[i], vertices[j]):
            added += 1

    return graph


def generate_dense_dag(v_count: int, seed: int = 42) -> DirectedGraph:
    """Generates a dense DAG targeting approximately 10% of all possible forward edges.

    target_edges = int(0.10 * V * (V - 1) / 2)
    Preserves acyclicity by directing edges strictly from lower to higher vertex indices.
    """
    rng = random.Random(seed)
    vertices = [f"c_{i:04d}" for i in range(v_count)]
    graph = DirectedGraph(vertices)

    if v_count < 2:
        return graph

    max_possible = v_count * (v_count - 1) // 2
    target_edges = int(0.10 * max_possible)
    if target_edges == 0 and max_possible > 0:
        target_edges = 1

    added = 0
    attempts = 0
    max_attempts = max(target_edges * 20, 1000)

    while added < target_edges and attempts < max_attempts:
        attempts += 1
        i = rng.randint(0, v_count - 2)
        j = rng.randint(i + 1, v_count - 1)
        if graph.add_edge(vertices[i], vertices[j]):
            added += 1

    # Fallback to ensure target is reached if random collisions saturated
    if added < target_edges:
        for i in range(v_count - 1):
            for j in range(i + 1, v_count):
                if added >= target_edges:
                    break
                if graph.add_edge(vertices[i], vertices[j]):
                    added += 1
            if added >= target_edges:
                break

    return graph


def generate_linear_chain(v_count: int) -> DirectedGraph:
    """Generates a deep linear chain: v0 -> v1 -> ... -> v(n-1)."""
    vertices = [f"c_{i:04d}" for i in range(v_count)]
    graph = DirectedGraph(vertices)
    for i in range(v_count - 1):
        graph.add_edge(vertices[i], vertices[i + 1])
    return graph


def generate_disconnected_dag(v_count: int, num_components: int = 5, seed: int = 42) -> DirectedGraph:
    """Generates multiple independent acyclic components."""
    rng = random.Random(seed)
    vertices = [f"c_{i:04d}" for i in range(v_count)]
    graph = DirectedGraph(vertices)

    # Partition vertices into components
    comp_size = v_count // num_components
    for c in range(num_components):
        start = c * comp_size
        end = v_count if c == num_components - 1 else (c + 1) * comp_size
        comp_nodes = vertices[start:end]
        if len(comp_nodes) < 2:
            continue
        # Add edges only within the component
        edges_to_add = int(len(comp_nodes) * 1.5)
        added = 0
        attempts = 0
        while added < edges_to_add and attempts < edges_to_add * 10:
            attempts += 1
            i = rng.randint(0, len(comp_nodes) - 2)
            j = rng.randint(i + 1, len(comp_nodes) - 1)
            if graph.add_edge(comp_nodes[i], comp_nodes[j]):
                added += 1

    return graph


def generate_cyclic_graph(v_count: int, seed: int = 42) -> DirectedGraph:
    """Generates an otherwise sparse DAG with a deliberate back-edge forming a cycle."""
    graph = generate_sparse_dag(v_count, seed=seed)
    vertices = graph.vertices
    if v_count >= 3:
        # Create a 3-node cycle: c0 -> c1 -> c2 -> c0
        c0, c1, c2 = vertices[0], vertices[1], vertices[2]
        graph.add_edge(c0, c1)
        graph.add_edge(c1, c2)
        graph.add_edge(c2, c0)  # Back edge creates cycle
    elif v_count == 2:
        graph.add_edge(vertices[0], vertices[1])
        graph.add_edge(vertices[1], vertices[0])
    elif v_count == 1:
        graph.add_edge(vertices[0], vertices[0])
    return graph


def benchmark_function(
    func: Callable[[], Any],
    warmup_runs: int = 2,
    timed_runs: int = 5,
) -> float:
    """Measures median execution time in milliseconds."""
    for _ in range(warmup_runs):
        func()

    durations = []
    for _ in range(timed_runs):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        durations.append((end - start) * 1000.0)  # ms

    return statistics.median(durations)


def run_benchmark_suite() -> List[Dict[str, Any]]:
    print("=" * 80)
    print("DAA ENGINE PERFORMANCE BENCHMARK SUITE")
    print(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python:   {platform.python_version()} ({platform.python_implementation()})")
    print("=" * 80)

    graph_configs = [
        ("Sparse DAG", generate_sparse_dag, False),
        ("Dense DAG", generate_dense_dag, False),
        ("Linear Chain", lambda v: generate_linear_chain(v), False),
        ("Disconnected DAG", lambda v: generate_disconnected_dag(v, 5), False),
        ("Cyclic Graph", generate_cyclic_graph, True),
    ]

    sizes = [10, 100, 500, 1000]
    results = []

    for graph_type, generator, is_cyclic in graph_configs:
        print(f"\nEvaluating: {graph_type}...")
        for v in sizes:
            graph = generator(v)
            num_v = graph.num_vertices
            num_e = graph.num_edges

            # -----------------------------------------------------------
            # Pre-benchmark Correctness Gate
            # -----------------------------------------------------------
            if not is_cyclic:
                # 1. Cycle detection must find no cycle
                has_cycle, _ = detect_cycle_dfs(graph)
                assert not has_cycle, f"Correctness check failed: cycle reported in {graph_type} (V={v})"

                # 2. Kahn topological sort must succeed and verify
                kahn_order = topological_sort_kahn(graph)
                assert len(kahn_order) == num_v, f"Kahn order length mismatch in {graph_type} (V={v})"
                assert verify_topological_order(graph, kahn_order), f"Kahn verification failed in {graph_type} (V={v})"

                # 3. DFS topological sort must succeed and verify
                dfs_order = topological_sort_dfs(graph)
                assert len(dfs_order) == num_v, f"DFS order length mismatch in {graph_type} (V={v})"
                assert verify_topological_order(graph, dfs_order), f"DFS verification failed in {graph_type} (V={v})"

                # Timed algorithms
                t_kahn = benchmark_function(lambda: topological_sort_kahn(graph))
                t_dfs = benchmark_function(lambda: topological_sort_dfs(graph))
                t_detect = benchmark_function(lambda: detect_cycle_dfs(graph))
                t_verify = benchmark_function(lambda: verify_topological_order(graph, kahn_order))

                results.append({"type": graph_type, "V": num_v, "E": num_e, "algo": "Kahn Toposort", "time_ms": t_kahn, "status": "PASSED"})
                results.append({"type": graph_type, "V": num_v, "E": num_e, "algo": "DFS Toposort", "time_ms": t_dfs, "status": "PASSED"})
                results.append({"type": graph_type, "V": num_v, "E": num_e, "algo": "DFS Cycle Detect", "time_ms": t_detect, "status": "PASSED"})
                results.append({"type": graph_type, "V": num_v, "E": num_e, "algo": "Order Verification", "time_ms": t_verify, "status": "PASSED"})

            else:
                # For Cyclic Graph:
                # 1. Cycle detection must find cycle and valid path
                has_cycle, cycle_path = detect_cycle_dfs(graph)
                assert has_cycle, f"Correctness check failed: cycle not detected in cyclic graph (V={v})"
                assert len(cycle_path) >= 2, "Cycle path too short"
                assert cycle_path[0] == cycle_path[-1], "Cycle path does not close"

                # 2. Kahn must raise CycleError
                try:
                    topological_sort_kahn(graph)
                    assert False, "Kahn failed to raise CycleError on cyclic graph"
                except CycleError:
                    pass

                # 3. DFS must raise CycleError
                try:
                    topological_sort_dfs(graph)
                    assert False, "DFS failed to raise CycleError on cyclic graph"
                except CycleError:
                    pass

                # Timed algorithms for cyclic graph
                t_detect = benchmark_function(lambda: detect_cycle_dfs(graph))

                def kahn_catch_cycle():
                    try:
                        topological_sort_kahn(graph)
                    except CycleError:
                        pass

                def dfs_catch_cycle():
                    try:
                        topological_sort_dfs(graph)
                    except CycleError:
                        pass

                t_kahn = benchmark_function(kahn_catch_cycle)
                t_dfs = benchmark_function(dfs_catch_cycle)

                results.append({"type": graph_type, "V": num_v, "E": num_e, "algo": "DFS Cycle Detect", "time_ms": t_detect, "status": "PASSED (Cycle Found)"})
                results.append({"type": graph_type, "V": num_v, "E": num_e, "algo": "Kahn Toposort (Cycle)", "time_ms": t_kahn, "status": "PASSED (CycleError)"})
                results.append({"type": graph_type, "V": num_v, "E": num_e, "algo": "DFS Toposort (Cycle)", "time_ms": t_dfs, "status": "PASSED (CycleError)"})

    # -----------------------------------------------------------
    # Render Benchmark Report Table
    # -----------------------------------------------------------
    print("\n" + "=" * 90)
    print(f"{'Graph Type':<18} | {'|V|':>5} | {'|E|':>6} | {'Algorithm':<22} | {'Median (ms)':>12} | {'Correctness':<20}")
    print("-" * 90)
    for r in results:
        print(f"{r['type']:<18} | {r['V']:>5} | {r['E']:>6} | {r['algo']:<22} | {r['time_ms']:>12.4f} | {r['status']:<20}")
    print("=" * 90)

    return results


if __name__ == "__main__":
    run_benchmark_suite()
