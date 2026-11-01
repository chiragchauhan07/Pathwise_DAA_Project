# DAA Algorithm Notes: Prerequisite Graph & Ordering Engine

## 1. Implementation Status
> [!NOTE]
> **Current Status: Verified & Hardened (Level 7 Completed).**
> The formal, decoupled **DAA Logic Engine** (`backend/daa_engine/`) provides custom graph construction, deterministic Kahn's topological sort with min-heap tie-breaking, iterative 3-state DFS cycle detection with path extraction, DFS topological sort, topological order verification, wave-based semester partitioning, and curricular constraint scheduling with workload limits and deadline feasibility validation.
> 
> Hardened against edge cases (single-vertex, disconnected components, deep linear chains up to 1500+ nodes, duplicate edges, capacity limits, and conflicting term deadlines). Benchmarked empirically across 5 structural topologies from $V=10$ to $V=1000$.

---

## 2. Problem Formulation
* **Vertices ($V$):** Distinct academic courses (identified by canonical `course_id`).
* **Edges ($E$):** Directed dependency pairs $(u, v)$ where edge $u \to v$ signifies that course $u$ is a prerequisite or recommended foundation before taking course $v$.
* **Goal:**
  1. Construct the directed graph $G = (V, E)$, supporting isolated vertices and deduplicating repeated edges.
  2. Determine whether $G$ is a Directed Acyclic Graph (DAG) or contains circular dependencies ($A \to B \to \dots \to A$).
  3. If acyclic, produce a valid linear ordering of vertices such that for every directed edge $u \to v$, $u$ strictly precedes $v$.
  4. Ensure deterministic tie-breaking when multiple courses are eligible simultaneously.
  5. Formally verify the resulting sequence against every edge in $G$.

---

## 3. Graph Representation
* **Module:** `backend/daa_engine/graph.py` (`DirectedGraph` class).
* **Adjacency Representation:**
  * Outgoing adjacency mapping: `_adjacency: Dict[str, List[str]]` where `_adjacency[u]` lists courses that depend on $u$.
  * In-degree mapping: `_in_degree: Dict[str, int]` where `_in_degree[v]` counts direct prerequisites of $v$.
  * Edge registry: `_edges: Set[Tuple[str, str]]` preventing duplicate edge insertion from corrupting in-degree counters.
* **Space Complexity:** $O(V + E)$ space, optimal for academic curriculum graphs where $|E| \ll |V|^2$.

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
* **Cycle Detection & Downstream Distinction:** If the output sequence length $< |V|$, a cycle prevents progress. Kahn's algorithm leverages `detect_cycle_dfs` to isolate the actual cycle vertices (`cycle_nodes`) from innocent downstream vertices blocked by the cycle (`unprocessed_nodes`), raising a clear `CycleError`.
* **Time Complexity:** $O(E + V \log V)$. Initial heapify takes $O(V)$, each of the $V$ vertices is pushed and popped at most once ($O(V \log V)$ total), and each of the $E$ edges is traversed once ($O(E)$). When a cycle occurs, the diagnostic DFS pass takes $O(V \log V + E)$.
* **Auxiliary Space Complexity:** $O(V + E)$ for in-degree copies, adjacency traversal, and heap storage.

### 4.2 Depth-First Search (DFS) Cycle Detection & Path Reconstruction
* **Function:** `detect_cycle_dfs(graph)`
* **Role in Application:** Safety validation run in `analysis_service.py` before ordering to abort cyclic requests and extract exact cycle paths.
* **Mechanism:**
  * Uses 3-state coloring:
    * `0: WHITE` (unvisited)
    * `1: GRAY` (currently active on the traversal stack)
    * `2: BLACK` (fully explored, all descendants visited)
  * Traverses vertices iteratively using an explicit call stack `[(u, next_neighbor_index)]` to prevent Python recursion limit issues on deep graphs (tested up to 1500+ vertices).
  * Encountering a `GRAY` neighbor flags a directed back-edge, confirming a cycle. Reconstructs the exact cycle path by tracing back along the active stack, closing the cycle ($v_0 \to \dots \to v_0$).
* **Time Complexity:** $O(V \log V + E)$. Initial lexicographical vertex sorting takes $O(V \log V)$. Each vertex enters and leaves the stack once ($O(V)$), and each edge is inspected once ($O(E)$).
* **Auxiliary Space Complexity:** $O(V)$ auxiliary space for state dictionary and traversal stack.

### 4.3 DFS-Based Topological Sort
* **Function:** `topological_sort_dfs(graph)`
* **Role in Application:** Secondary sorting algorithm used for cross-algorithm verification and benchmarks.
* **Mechanism:**
  * Traverses each component via 3-state iterative DFS.
  * When a vertex turns `BLACK` (all dependent branches processed), it is pushed to a post-order list.
  * If a back-edge is detected during traversal, raises `CycleError` immediately.
  * Reversing the post-order list yields a valid topological order where every prerequisite precedes its dependent course.
* **Time Complexity:** $O(V \log V + E)$ due to lexicographical sorting of vertices for deterministic traversal.
* **Auxiliary Space Complexity:** $O(V)$ auxiliary space for traversal state tracking, explicit call stack, and post-order sequence.

### 4.4 Order Verification
* **Function:** `verify_topological_order(graph, order)`
* **Role in Application:** Mathematical safety barrier asserting the correctness of computed orders before returning API responses.
* **Checks:**
  1. Cardinality check: `len(order) == graph.num_vertices`.
  2. Set equality check: `set(order) == set(graph.vertices)` (catches duplicate, missing, or unexpected vertices).
  3. Precedence check: For every edge $(u, v) \in E$, asserts $\text{pos}[u] < \text{pos}[v]$.
* **Time Complexity:** $O(V \log V + E)$. Accessing `graph.vertices` performs a lexicographical sort of the vertex set in $O(V \log V)$ time. Converting to sets and building the position map takes $O(V)$ time. Copying and iterating across `graph.edges` takes $O(E)$ time.
* **Peak Auxiliary Space Complexity:** $O(V + E)$ peak auxiliary space, accounting for temporary collection copies: $O(V)$ for the sorted vertex list and vertex set, $O(V)$ for the position index map, and $O(E)$ for the shallow copy of the edge set returned by the `graph.edges` property.

---

## 5. Algorithmic Complexity Summary Table

| Operation | Algorithm | Time Complexity | Auxiliary Space | Status |
| :--- | :--- | :--- | :--- | :--- |
| Graph Construction | `build_graph` / `build_graph_from_kb` | $O(V + E)$ | $O(V + E)$ | Hardened |
| Primary Toposort | Kahn's Algorithm (`topological_sort_kahn`) | $O(E + V \log V)$ | $O(V + E)$ | Hardened |
| Cycle Detection | 3-State Iterative DFS (`detect_cycle_dfs`) | $O(V \log V + E)$ | $O(V)$ | Hardened |
| Secondary Toposort | Iterative DFS Post-Order (`topological_sort_dfs`) | $O(V \log V + E)$ | $O(V)$ | Hardened |
| Order Verification | `verify_topological_order` | $O(V \log V + E)$ | $O(V + E)$ | Hardened |
| Semester Scheduling (Unconstrained) | Wave Layering (`schedule_courses`, unconstrained) | $O(V \log V + E)$ | $O(V + E)$ | Hardened |
| Semester Scheduling (Workload-Constrained) | Multi-Priority List Scheduling (`schedule_courses`, constrained) | $O(V^2 \log V + V \cdot E)$ | $O(V + E)$ | Hardened |
| Schedule Verification | Mathematical & Consistency Safety Gate (`verify_semester_schedule`) | $O(V + E)$ | $O(V)$ | Hardened |

---

## 6. Performance Benchmarks

### 6.1 Benchmark Methodology
- **Script:** `benchmarks/benchmark_daa.py`
- **Execution Command:** `python benchmarks/benchmark_daa.py`
- **Timer:** `time.perf_counter()` with 2 warm-up runs and 5 timed repetitions (reporting median execution time in ms).
- **Correctness Gate:** Every benchmarked graph is verified for mathematical correctness before timing.
- **Topologies Evaluated:**
  1. **Sparse DAG:** Acyclic graph with $E \approx 1.5 \times V$.
  2. **Dense DAG:** Genuinely dense acyclic graph targeting ~10% of all possible forward edges ($E = \lfloor 0.10 \times V(V - 1) / 2 \rfloor$, with small graph boundary safety; reaches $E=49,950$ at $V=1000$).
  3. **Linear Chain:** Deep chain $v_0 \to v_1 \to \dots \to v_{n-1}$ ($E = V - 1$).
  4. **Disconnected DAG:** 5 independent components, each an internal DAG.
  5. **Cyclic Graph:** Sparse graph with an embedded directed cycle.

### 6.2 Empirical Results (Measured Baseline)
*Environment: Windows 11, Python 3.12.4, AMD64*
*Complete results from reproducible execution (`python benchmarks/benchmark_daa.py`):*

| Graph Type | $|V|$ | $|E|$ | Algorithm | Median Time (ms) | Correctness Status |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Sparse DAG** | 10 | 15 | Kahn Toposort | 0.0185 | PASSED |
| Sparse DAG | 10 | 15 | DFS Toposort | 0.0125 | PASSED |
| Sparse DAG | 10 | 15 | DFS Cycle Detect | 0.0123 | PASSED |
| Sparse DAG | 10 | 15 | Order Verification | 0.0039 | PASSED |
| Sparse DAG | 100 | 150 | Kahn Toposort | 0.1041 | PASSED |
| Sparse DAG | 100 | 150 | DFS Toposort | 0.2215 | PASSED |
| Sparse DAG | 100 | 150 | DFS Cycle Detect | 0.2263 | PASSED |
| Sparse DAG | 100 | 150 | Order Verification | 0.0348 | PASSED |
| Sparse DAG | 500 | 750 | Kahn Toposort | 1.1450 | PASSED |
| Sparse DAG | 500 | 750 | DFS Toposort | 1.2929 | PASSED |
| Sparse DAG | 500 | 750 | DFS Cycle Detect | 0.8139 | PASSED |
| Sparse DAG | 500 | 750 | Order Verification | 0.3080 | PASSED |
| Sparse DAG | 1000 | 1500 | Kahn Toposort | 2.3780 | PASSED |
| Sparse DAG | 1000 | 1500 | DFS Toposort | 1.8064 | PASSED |
| Sparse DAG | 1000 | 1500 | DFS Cycle Detect | 2.2730 | PASSED |
| Sparse DAG | 1000 | 1500 | Order Verification | 0.8754 | PASSED |
| **Dense DAG** | 10 | 4 | Kahn Toposort | 0.0159 | PASSED |
| Dense DAG | 10 | 4 | DFS Toposort | 0.0178 | PASSED |
| Dense DAG | 10 | 4 | DFS Cycle Detect | 0.0169 | PASSED |
| Dense DAG | 10 | 4 | Order Verification | 0.0054 | PASSED |
| Dense DAG | 100 | 495 | Kahn Toposort | 0.2323 | PASSED |
| Dense DAG | 100 | 495 | DFS Toposort | 0.3342 | PASSED |
| Dense DAG | 100 | 495 | DFS Cycle Detect | 0.2254 | PASSED |
| Dense DAG | 100 | 495 | Order Verification | 0.1086 | PASSED |
| Dense DAG | 500 | 12475 | Kahn Toposort | 1.8618 | PASSED |
| Dense DAG | 500 | 12475 | DFS Toposort | 4.5658 | PASSED |
| Dense DAG | 500 | 12475 | DFS Cycle Detect | 4.7644 | PASSED |
| Dense DAG | 500 | 12475 | Order Verification | 2.0194 | PASSED |
| Dense DAG | 1000 | 49950 | Kahn Toposort | 7.3000 | PASSED |
| Dense DAG | 1000 | 49950 | DFS Toposort | 19.4312 | PASSED |
| Dense DAG | 1000 | 49950 | DFS Cycle Detect | 18.3703 | PASSED |
| Dense DAG | 1000 | 49950 | Order Verification | 11.1668 | PASSED |
| **Linear Chain** | 10 | 9 | Kahn Toposort | 0.0165 | PASSED |
| Linear Chain | 10 | 9 | DFS Toposort | 0.0198 | PASSED |
| Linear Chain | 10 | 9 | DFS Cycle Detect | 0.0193 | PASSED |
| Linear Chain | 10 | 9 | Order Verification | 0.0059 | PASSED |
| Linear Chain | 100 | 99 | Kahn Toposort | 0.1411 | PASSED |
| Linear Chain | 100 | 99 | DFS Toposort | 0.1839 | PASSED |
| Linear Chain | 100 | 99 | DFS Cycle Detect | 0.1566 | PASSED |
| Linear Chain | 100 | 99 | Order Verification | 0.0282 | PASSED |
| Linear Chain | 500 | 499 | Kahn Toposort | 0.8126 | PASSED |
| Linear Chain | 500 | 499 | DFS Toposort | 1.0696 | PASSED |
| Linear Chain | 500 | 499 | DFS Cycle Detect | 1.1631 | PASSED |
| Linear Chain | 500 | 499 | Order Verification | 0.3706 | PASSED |
| Linear Chain | 1000 | 999 | Kahn Toposort | 1.8822 | PASSED |
| Linear Chain | 1000 | 999 | DFS Toposort | 2.4569 | PASSED |
| Linear Chain | 1000 | 999 | DFS Cycle Detect | 2.4595 | PASSED |
| Linear Chain | 1000 | 999 | Order Verification | 0.6808 | PASSED |
| **Disconnected DAG** | 10 | 5 | Kahn Toposort | 0.0157 | PASSED |
| Disconnected DAG | 10 | 5 | DFS Toposort | 0.0175 | PASSED |
| Disconnected DAG | 10 | 5 | DFS Cycle Detect | 0.0161 | PASSED |
| Disconnected DAG | 10 | 5 | Order Verification | 0.0052 | PASSED |
| Disconnected DAG | 100 | 150 | Kahn Toposort | 0.1837 | PASSED |
| Disconnected DAG | 100 | 150 | DFS Toposort | 0.1914 | PASSED |
| Disconnected DAG | 100 | 150 | DFS Cycle Detect | 0.2005 | PASSED |
| Disconnected DAG | 100 | 150 | Order Verification | 0.0489 | PASSED |
| Disconnected DAG | 500 | 750 | Kahn Toposort | 1.2025 | PASSED |
| Disconnected DAG | 500 | 750 | DFS Toposort | 1.3048 | PASSED |
| Disconnected DAG | 500 | 750 | DFS Cycle Detect | 1.2366 | PASSED |
| Disconnected DAG | 500 | 750 | Order Verification | 0.3614 | PASSED |
| Disconnected DAG | 1000 | 1500 | Kahn Toposort | 1.4934 | PASSED |
| Disconnected DAG | 1000 | 1500 | DFS Toposort | 1.9653 | PASSED |
| Disconnected DAG | 1000 | 1500 | DFS Cycle Detect | 2.9284 | PASSED |
| Disconnected DAG | 1000 | 1500 | Order Verification | 0.6034 | PASSED |
| **Cyclic Graph** | 10 | 17 | DFS Cycle Detect | 0.0072 | PASSED (Cycle Found) |
| Cyclic Graph | 10 | 17 | Kahn Toposort (Cycle) | 0.0179 | PASSED (CycleError) |
| Cyclic Graph | 10 | 17 | DFS Toposort (Cycle) | 0.0084 | PASSED (CycleError) |
| Cyclic Graph | 100 | 153 | DFS Cycle Detect | 0.0685 | PASSED (Cycle Found) |
| Cyclic Graph | 100 | 153 | Kahn Toposort (Cycle) | 0.2307 | PASSED (CycleError) |
| Cyclic Graph | 100 | 153 | DFS Toposort (Cycle) | 0.0968 | PASSED (CycleError) |
| Cyclic Graph | 500 | 753 | DFS Cycle Detect | 0.3408 | PASSED (Cycle Found) |
| Cyclic Graph | 500 | 753 | Kahn Toposort (Cycle) | 2.6403 | PASSED (CycleError) |
| Cyclic Graph | 500 | 753 | DFS Toposort (Cycle) | 0.3497 | PASSED (CycleError) |
| Cyclic Graph | 1000 | 1503 | DFS Cycle Detect | 1.1502 | PASSED (Cycle Found) |
| Cyclic Graph | 1000 | 1503 | Kahn Toposort (Cycle) | 9.9454 | PASSED (CycleError) |
| Cyclic Graph | 1000 | 1503 | DFS Toposort (Cycle) | 0.9486 | PASSED (CycleError) |

*Key Takeaways:*
1. **Dense Graph Scaling ($|V|=1000, |E|=49,950$):** In a genuinely dense DAG possessing ~10% of all possible forward edges, Kahn's algorithm resolves in ~7.30 ms, outperforming DFS Toposort (~19.43 ms) and DFS Cycle Detection (~18.37 ms) due to the efficiency of in-degree tracking without repeated stack operations. Order Verification runs in ~11.17 ms for ~50k edges.
2. **Sparse Graph Performance ($|V|=1000, |E|=1500$):** All algorithms execute in sub-2.4 milliseconds.
3. **Cycle Handling:** On cyclic graphs, DFS cycle detection identifies cycles fast (~1.15 ms at $V=1000$). Kahn's algorithm intentionally performs a diagnostic cycle-isolation routine when aborted by a cycle, reflecting a measured ~9.95 ms at $V=1000$ to isolate cycle members from innocent downstream nodes.

---

## 7. Pedagogical Optimization & Curricular Constraints (Level 7)

### 7.1 Problem Formulation & Motivation
A purely linear topological ordering satisfies mathematical prerequisite precedence but fails to inform students how courses should be grouped into academic semesters or study waves. In educational curricula:
1. **Parallel Eligibility:** Courses with no mutual dependencies can be completed concurrently in the same academic term.
2. **Workload Caps:** Students cannot register for an unbounded number of courses in a single semester ($K = \text{max\_courses\_per\_semester}$).
3. **Degree Deadlines:** Academic programs require completion within a maximum number of terms ($M = \text{max\_semesters}$).
4. **Pedagogical Difficulty Smoothing:** Introductory/foundational courses should be introduced before intermediate and advanced courses within each eligible wave.
5. **Relationship Nuance:** Hard (`required`) prerequisites strictly mandate sequential semester completion, whereas soft (`recommended`/`optional`) foundations allow concurrent registration while guiding within-term precedence.

### 7.2 Core Algorithms & Scheduling Mechanics (`backend/daa_engine/scheduler.py`)

#### 1. Unified Wave Layering (Unconstrained Scheduling)
When `max_courses_per_semester` is unconstrained (`None`), the scheduler assigns each course $v \in V$ to its earliest valid completion term using DAG longest path layering:
$$\text{wave}[v] = \max\left(1, \max_{(u, v) \in E_{\text{req}}} (\text{wave}[u] + 1), \max_{(u, v) \in E_{\text{soft}}} \text{wave}[u]\right)$$
* **Required Edges ($E_{\text{req}}$):** Enforce strict semester progression ($\text{wave}[v] \ge \text{wave}[u] + 1$).
* **Soft Edges ($E_{\text{soft}}$):** Allow concurrent enrollment in the same wave ($\text{wave}[v] \ge \text{wave}[u]$), but forbid scheduling a dependent in a strictly earlier wave than its foundation.
* **Within-Wave Ordering:** Deterministically sorted using a min-heap topological pass weighted by difficulty (`beginner` < `intermediate` < `advanced`), followed by lexicographical course ID.

#### 2. Workload-Constrained List Scheduling
When `max_courses_per_semester = K` is specified, the scheduler executes multi-priority list scheduling across successive semesters $s = 1, 2, \dots$:
1. **Candidate Eligibility:** Course $v$ is eligible for semester $s$ if all its required prerequisites are completed in semesters $< s$.
2. **Multi-Criterion Pedagogical Priority Tuple:**
   $$\text{priority}(v) = (-\text{critical\_depth}[v], \; \text{unmet\_soft\_prereqs}[v], \; \text{difficulty\_rank}[v], \; v)$$
   * **Critical Path Depth ($-\text{depth}[v]$):** Prioritizes courses that unblock the longest downstream dependent chain to prevent curriculum stalls.
   * **Unmet Soft Prerequisites:** Prioritizes courses whose recommended foundations are already satisfied.
   * **Difficulty Rank:** Introduces beginner courses (rank 1) before intermediate (rank 2) and advanced (rank 3).
   * **Lexicographical Tie-Breaker:** Guarantees deterministic, reproducible results.
3. At most $K$ top-priority candidates are assigned to semester $s$, then ordered internally according to dependency edges.

#### 3. Mathematical Feasibility Bounds & Conflict Reporting
Before or during scheduling, the engine asserts curricular constraint compatibility:
* **Prerequisite Chain Bound:** If the longest chain in $E_{\text{req}}$ exceeds $M$, raises `CurricularConstraintError` with the exact conflicting path ($c_1 \to \dots \to c_m$).
* **Capacity Bound:** If $\lceil |V| / K \rceil > M$, raises `CurricularConstraintError` explaining that the workload cap prevents finishing within $M$ terms.

### 7.3 Mathematical & Structural Verification Gate (`verify_semester_schedule`)
Every computed schedule must pass formal verification before being returned:
1. **Structural Representation Consistency:**
   - Every semester group possesses sequential 1-indexed `semester_number` strictly matching its position ($1, 2, \dots, S$).
   - Each group's `course_count` strictly equals `len(sem["courses"])`.
   - Every course record's `semester` attribute matches its containing semester group.
   - The `course_to_semester` mapping is strictly identical to the containing semester group for every course.
   - Flattened `ordered_courses` sequence identically matches the concatenation of courses across semester groups in order.
   - Every course appears exactly once across semester groups, with no duplicate or omitted courses.
   - `total_semesters` strictly matches `len(semesters)`.
2. **Required Precedence:** For all $(u, v) \in E_{\text{req}}$, $\text{semester}[u] < \text{semester}[v]$.
3. **Soft Precedence:** For all $(u, v) \in E_{\text{soft}}$, $\text{semester}[u] \le \text{semester}[v]$, and if $\text{semester}[u] == \text{semester}[v]$, $\text{pos}[u] < \text{pos}[v]$ in the flattened sequence.
4. **Capacity Invariant:** No semester exceeds $K$ courses.
5. **Deadline Invariant:** Total semesters $\le M$.

### 7.4 Complexity Analysis

#### 1. Unconstrained Wave Scheduling (`max_courses_per_semester is None`)
* **Time Complexity:** $O(V \log V + E)$
  * **Graph Construction & Longest-Path Memoization:** $O(V + E)$ to extract required/soft subgraphs and memoize longest sink paths.
  * **Wave Layering DFS:** $O(V + E)$ memoized topological traversal computing $\text{wave}[v]$ from incoming edges.
  * **Within-Wave Min-Heap Ordering:** For wave $w$ with $V_w$ courses and $E_w$ internal edges, topological ordering with difficulty tie-breaking takes $O(V_w \log V_w + E_w)$. Summed across all waves $\sum_w (V_w \log V_w + E_w) \le O(V \log V + E)$.
  * **Overall Time:** $O(V \log V + E)$.
* **Auxiliary Space:** $O(V + E)$ for adjacency mappings, incoming prerequisite sets, memoization dictionaries, and wave buckets.

#### 2. Workload-Constrained List Scheduling (`max_courses_per_semester is not None`)
* **Time Complexity:** $O(V^2 \log V + V \cdot E)$ general worst-case bound (reaching $O(V^3)$ on dense graphs)
  * Exactly $V$ courses are selected slot-by-slot across at most $V$ semesters.
  * In each course-selection iteration (up to $V$ iterations):
    - Constructing `term_assigned_set = set(term_assigned)` and `completed_with_term = completed | term_assigned_set` once per iteration takes $O(V)$ time.
    - Scanning unassigned vertices to evaluate prerequisite subset satisfaction (`required_incoming[cid].issubset(completed)` and `soft_incoming[cid].issubset(completed_with_term)`) checks in-degrees $\text{deg}^-(cid)$, which sums to $\sum_{cid} \text{deg}^-(cid) \le E$ across all candidates. Over $V$ iterations, this evaluates candidate prerequisite sets in $O(V^2 + V \cdot E)$ time.
    - Sorting eligible candidates using the multi-criterion pedagogical priority tuple $(-\text{depth}, \text{len}(\text{soft} - \text{completed\_with\_term}), \text{difficulty}, \text{id})$ takes $O(V \log V)$ comparisons per iteration, summing to $O(V^2 \log V)$ across all $V$ selections.
    - Selecting the top candidate and appending it to `term_assigned` takes $O(1)$.
  * Within-semester topological ordering (`_order_within_wave`) across all semesters takes $\sum_s (V_s \log V_s + E_s) \le O(V \log V + E)$ total.
  * **General Bound:** $O(V^2 \log V + V \cdot E)$.
  * **Sparse-Graph Case ($E = O(V)$):** On typical academic curriculum graphs where degree is small and $E = O(V)$, $V \cdot E = O(V^2)$, so the bound is dominated by candidate sorting: $O(V^2 \log V)$.
  * **Dense-Graph Case ($E = \Theta(V^2)$):** In dense DAGs possessing quadratic edges, $V \cdot E = \Theta(V^3)$, so the runtime reaches $O(V^3)$.
* **Auxiliary Space:** $O(V + E)$ for incoming/outgoing dependency sets, completed/assigned tracking sets, depth memoization tables, and semester output structures.

#### 3. Schedule Verification (`verify_semester_schedule`)
* **Time Complexity:** $O(V + E)$
  * Traversing semester groups and validating 1-indexed sequential numbering, course counts, course attributes, and uniqueness takes $O(V)$ time.
  * Comparing group course sequences against flattened `ordered_courses` takes $O(V)$ time.
  * Validating bijective correspondence with `course_to_semester` takes $O(V)$ time.
  * Verifying dependency precedence across all $E$ relationships via $O(1)$ dictionary lookups in `course_to_sem` and `pos_map` takes $O(E)$ time.
  * **Overall Time:** $O(V + E)$.
* **Auxiliary Space:** $O(V)$ auxiliary space for group course ID lists, flattened ID list, and position mapping (all relationship edges are validated in-place from the input list).

### 7.5 Pedagogical Metadata Limitations
The current Knowledge Base contains curated course difficulty classifications (`beginner`, `intermediate`, `advanced`) but intentionally excludes arbitrary credit hours, institutional term offerings (Fall/Spring), or synthetic weekly hour metrics. The scheduler operates strictly on mathematically grounded dependency structures and user-specified workload caps without fabricating uncurated metadata.
