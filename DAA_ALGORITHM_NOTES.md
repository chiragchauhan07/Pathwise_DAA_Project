# DAA Algorithm Notes: Prerequisite Graph & Ordering Engine

## 1. Implementation Status
> [!NOTE]
> **Current Status: Verified & Hardened.**
> The formal **DAA Logic Engine** (`backend/daa_engine/`) provides custom graph construction, deterministic Kahn's topological sort with min-heap tie-breaking, iterative 3-state DFS cycle detection with path extraction, DFS topological sort, order verification, and wave-based semester partitioning.
> 
> Hardened against edge cases (single-vertex, disconnected components, deep linear chains, and conflicting circular dependencies). Fully verified on the 100-course MRIIRS B.Tech Computer Science curriculum with 118 automated pytest test cases.

---

## 2. Problem Formulation
* **Vertices ($V$):** Distinct academic courses (identified by canonical `course_id`).
* **Edges ($E$):** Directed dependency pairs $(u, v)$ where edge $u \to v$ signifies that course $u$ is a prerequisite before taking course $v$.
* **Goal:**
  1. Construct the directed graph $G = (V, E)$, supporting isolated vertices and deduplicating repeated edges.
  2. Determine whether $G$ is a Directed Acyclic Graph (DAG) or contains circular dependencies ($A \to B \to \dots \to A$).
  3. If acyclic, produce a valid linear ordering of vertices such that for every directed edge $u \to v$, $u$ strictly precedes $v$.
  4. Ensure deterministic tie-breaking when multiple courses are eligible simultaneously using a priority min-heap.
  5. Formally verify the resulting sequence against every edge in $G$ and partition into concurrent semester waves.

---

## 3. Graph Representation
* **Module:** `backend/daa_engine/graph.py` (`DirectedGraph` class).
* **Adjacency Representation:**
  * Outgoing adjacency mapping: `_adjacency: Dict[str, List[str]]` where `_adjacency[u]` lists courses that depend on $u$.
  * In-degree mapping: `_in_degree: Dict[str, int]` where `_in_degree[v]` counts direct prerequisites of $v$.
  * Edge registry: `_edges: Set[Tuple[str, str]]` preventing duplicate edge insertion from corrupting in-degree counters.
* **Space Complexity:** $\mathcal{O}(|V| + |E|)$ space, optimal for academic curriculum graphs where $|E| \ll |V|^2$.

---

## 4. Implemented Algorithms & Verified Complexities

### 4.1 Kahn's Algorithm with Deterministic Min-Heap
* **Function:** `topological_sort_kahn(graph)`
* **Role in Application:** Primary production topological sorting algorithm in `analysis_service.py`.
* **Mechanism:**
  1. Initialize min-heap (`heapq`) with all vertices having in-degree 0.
  2. Pop the lexicographically smallest vertex $u$ to guarantee deterministic tie-breaking across runs and platforms.
  3. Append $u$ to the topological order.
  4. For each outgoing neighbor $v \in \text{Adj}[u]$, decrement its in-degree. When in-degree reaches 0, push $v$ into the min-heap.
  5. Repeat until heap is empty.
* **Cycle Detection & Downstream Distinction:** If the output sequence length $< |V|$, a cycle prevents progress. Kahn's algorithm leverages `detect_cycle_dfs` to isolate the actual cycle vertices (`cycle_nodes`) from innocent downstream vertices blocked by the cycle, raising a `CycleConflictError`.
* **Time Complexity:** $\mathcal{O}(|E| + |V| \log |V|)$. Initial heapify takes $\mathcal{O}(|V|)$, each of the $|V|$ vertices is pushed and popped at most once ($\mathcal{O}(|V| \log |V|)$ total), and each of the $|E|$ edges is traversed once ($\mathcal{O}(|E|)$).
* **Auxiliary Space Complexity:** $\mathcal{O}(|V| + |E|)$ for in-degree copies, adjacency traversal, and heap storage.

### 4.2 Depth-First Search (DFS) Cycle Detection & Path Reconstruction
* **Function:** `detect_cycle_dfs(graph)`
* **Role in Application:** Safety validation run in `analysis_service.py` before ordering to abort cyclic requests and extract exact cycle paths.
* **Mechanism:**
  * Uses 3-state coloring:
    * `0: WHITE` (unvisited)
    * `1: GRAY` (currently active on the traversal stack)
    * `2: BLACK` (fully explored, all descendants visited)
  * Traverses vertices iteratively using an explicit call stack `[(u, next_neighbor_index)]` to prevent Python recursion limit issues on deep graphs.
  * Encountering a `GRAY` neighbor flags a directed back-edge, confirming a cycle. Reconstructs the exact cycle path by tracing back along the active stack, closing the cycle ($v_0 \to \dots \to v_0$).
* **Time Complexity:** $\mathcal{O}(|V| + |E|)$. Initial lexicographical vertex sorting takes $\mathcal{O}(|V| \log |V|)$ for determinism.
* **Auxiliary Space Complexity:** $\mathcal{O}(|V|)$ auxiliary space for state dictionary and traversal stack.

### 4.3 DFS-Based Topological Sort
* **Function:** `topological_sort_dfs(graph)`
* **Role in Application:** Secondary sorting algorithm used for cross-algorithm verification.
* **Mechanism:**
  * Traverses each component via 3-state iterative DFS.
  * When a vertex turns `BLACK` (all dependent branches processed), it is pushed to a post-order list.
  * If a back-edge is detected during traversal, raises `CycleConflictError` immediately.
  * Reversing the post-order list yields a valid topological order where every prerequisite precedes its dependent course.
* **Time Complexity:** $\mathcal{O}(|V| \log |V| + |E|)$ due to lexicographical sorting of vertices for deterministic traversal.
* **Auxiliary Space Complexity:** $\mathcal{O}(|V|)$ auxiliary space for traversal state tracking, explicit call stack, and post-order sequence.

### 4.4 Order Verification
* **Function:** `verify_topological_order(graph, order)`
* **Role in Application:** Mathematical safety barrier asserting the correctness of computed orders before returning API responses.
* **Checks:**
  1. Cardinality check: `len(order) == graph.num_vertices`.
  2. Set equality check: `set(order) == set(graph.vertices)` (catches duplicate, missing, or unexpected vertices).
  3. Precedence check: For every edge $(u, v) \in E$, asserts $\text{pos}[u] < \text{pos}[v]$.
* **Time Complexity:** $\mathcal{O}(|V| + |E|)$.
* **Peak Auxiliary Space Complexity:** $\mathcal{O}(|V| + |E|)$.

---

## 5. Algorithmic Complexity Summary Table

| Operation | Algorithm | Time Complexity | Auxiliary Space | Status |
| :--- | :--- | :--- | :--- | :--- |
| Graph Construction | `build_graph` / `build_graph_from_kb` | $\mathcal{O}(|V| + |E|)$ | $\mathcal{O}(|V| + |E|)$ | Verified |
| Primary Toposort | Kahn's Algorithm (`topological_sort_kahn`) | $\mathcal{O}(|E| + |V| \log |V|)$ | $\mathcal{O}(|V| + |E|)$ | Verified |
| Cycle Detection | 3-State Iterative DFS (`detect_cycle_dfs`) | $\mathcal{O}(|V| + |E|)$ | $\mathcal{O}(|V|)$ | Verified |
| Secondary Toposort | Iterative DFS Post-Order (`topological_sort_dfs`) | $\mathcal{O}(|V| \log |V| + |E|)$ | $\mathcal{O}(|V|)$ | Verified |
| Order Verification | `verify_topological_order` | $\mathcal{O}(|V| + |E|)$ | $\mathcal{O}(|V|)$ | Verified |
| Semester Wave Partitioning | Level-Order BFS Frontier (`schedule_courses`) | $\mathcal{O}(|V| + |E|)$ | $\mathcal{O}(|V| + |E|)$ | Verified |
| Schedule Verification | Invariant Check (`verify_semester_schedule`) | $\mathcal{O}(|V| + |E|)$ | $\mathcal{O}(|V|)$ | Verified |

---

## 6. How Topological Ordering Supports Reliable Planning

In university degree curricula, topological sorting provides fundamental operational guarantees:

1. **Precedence Guarantee (No Forward Inversion):**
   $$\forall (u, v) \in E \implies \text{pos}[u] < \text{pos}[v]$$
   Guarantees that no student enrolls in advanced subjects before foundational courses are completed.

2. **Cycle Deadlock Immunity:**
   A topological ordering exists if and only if $G$ is a DAG. By coupling Kahn's algorithm with 3-state DFS cycle detection, any circular prerequisite deadlock ($A \to B \to A$) is detected in linear time, and the exact cycle path is isolated to prevent student registration gridlock.

3. **Level-Order Concurrent Wave Scheduling:**
   All courses with in-degree 0 at step $t$ are mutually independent. This mathematical property allows colleges to batch independent courses into concurrent semester cohorts without prerequisite conflicts.

4. **Deterministic Reproducibility:**
   Deterministic tie-breaking via priority min-heaps ensures that identical student course selections yield identical, optimal, and reproducible graduation plans, eliminating administrative advising bottlenecks.
