# Pathwise DAA Algorithms & Mathematical Proofs

The core computational engine of Pathwise is implemented in `backend/daa_engine/` using pure Python without external graph libraries (such as NetworkX). This document details the mathematical formulation, algorithmic complexity, proofs of correctness, and empirical performance benchmarks.

---

## 1. Problem Formulation

Let $G = (V, E)$ be a directed graph representing an academic curriculum:
- **Vertices ($V$):** The set of distinct academic courses $\{v_1, v_2, \dots, v_n\}$.
- **Edges ($E$):** Directed pairs $(u, v)$ such that $u \to v$ signifies that course $u$ is a prerequisite for course $v$.
- **Goal:**
  1. Determine if $G$ is a Directed Acyclic Graph (DAG) or contains circular dependencies.
  2. If acyclic, find a linear ordering $L = [v_{\pi(1)}, v_{\pi(2)}, \dots, v_{\pi(n)}]$ such that for every directed edge $(u, v) \in E$, $\pi^{-1}(u) < \pi^{-1}(v)$.
  3. Ensure deterministic tie-breaking across different systems and runs.
  4. Partition $L$ into semesters $S_1, S_2, \dots, S_k$ satisfying capacity and difficulty bounds.

---

## 2. Graph Representation

* **Module:** `backend/daa_engine/graph.py` (`DirectedGraph`)
* **Adjacency Representation:**
  - Forward adjacency: $\text{Adj}[u] = \{v \in V \mid (u, v) \in E\}$ stored as `Dict[str, List[str]]`.
  - In-degree dictionary: $\text{in\_degree}[v] = |\{u \in V \mid (u, v) \in E\}|$ stored as `Dict[str, int]`.
  - Edge deduplication set: `Set[Tuple[str, str]]` preventing repeated edges from inflating in-degree counts.
* **Space Complexity:** $\mathcal{O}(V + E)$, optimal for sparse and dense curricular dependency graphs.

---

## 3. Algorithm Specifications & Complexities

### 3.1 Deterministic Kahn's Algorithm with Min-Heap Tie-Breaking

* **Function:** `topological_sort_kahn(graph)`
* **Algorithm Mechanism:**
  1. Calculate initial in-degrees for all $v \in V$.
  2. Insert all vertices with $\text{in\_degree}[v] = 0$ into a min-heap $Q$.
  3. While $Q \neq \emptyset$:
     - Pop the minimum element $u \leftarrow \text{heappop}(Q)$ (deterministic lexicographical tie-breaking).
     - Append $u$ to output sequence $L$.
     - For each neighbor $v \in \text{Adj}[u]$:
       - $\text{in\_degree}[v] \leftarrow \text{in\_degree}[v] - 1$.
       - If $\text{in\_degree}[v] = 0$, push $v$ into $Q$.
  4. If $|L| < |V|$, invoke `detect_cycle_dfs` to isolate cycle components and raise `CycleError`.
* **Asymptotic Time Complexity:** $\mathcal{O}(E + V \log V)$. Initial heap construction takes $\mathcal{O}(V)$. Each vertex is pushed and popped from the min-heap at most once ($\mathcal{O}(V \log V)$), and every edge is traversed exactly once ($\mathcal{O}(E)$).
* **Auxiliary Space:** $\mathcal{O}(V + E)$ for in-degree copies, the min-heap, and the output sequence.

#### Proof of Correctness (Induction on Sequence Length)
> **Theorem:** If $G$ is a DAG, Kahn's algorithm outputs a valid topological ordering.
> 
> **Proof:**
> 1. *Base Case ($k=1$):* The first vertex $u_1$ popped has $\text{in\_degree}[u_1] = 0$. Hence, no vertex in $V$ is a prerequisite for $u_1$. It can safely appear first.
> 2. *Inductive Step:* Assume the sequence $L_{k} = [u_1, u_2, \dots, u_k]$ is a valid topological prefix. At step $k+1$, a vertex $w$ is added only when its in-degree reaches $0$. Its in-degree reaches $0$ if and only if all edges $(x, w) \in E$ originate from vertices $x \in L_k$. Thus, all prerequisites of $w$ precede $w$ in $L$, preserving the invariant for $L_{k+1}$.
> 3. *Termination & Acyclicity:* If $G$ is acyclic, every non-empty induced subgraph has at least one vertex with in-degree 0. Thus, all $|V|$ vertices will eventually have their in-degree reduced to 0 and be added to $L$.

---

### 3.2 Iterative 3-State DFS Cycle Detection & Path Reconstruction

* **Function:** `detect_cycle_dfs(graph)`
* **Algorithm Mechanism:**
  - Maintains state for each vertex:
    - `0 (WHITE)`: Unvisited
    - `1 (GRAY)`: Currently being visited (on active recursion stack)
    - `2 (BLACK)`: Fully explored
  - Iterates with an explicit call stack of tuples $(u, \text{neighbor\_index})$ instead of native Python recursion.
  - If a neighbor $v$ is encountered with state `GRAY`, a back-edge $(u, v)$ has been identified.
  - The cycle path is reconstructed by collecting vertices from the stack between $v$ and $u$, followed by $v$.
* **Asymptotic Time Complexity:** $\mathcal{O}(V \log V + E)$ where sorting the vertex keys upfront provides determinism.
* **Auxiliary Space:** $\mathcal{O}(V)$ for color state tracking and explicit stack.

---

### 3.3 Topological Order Verifier

* **Function:** `verify_topological_order(graph, order)`
* **Safety Contract:**
  1. Cardinality check: $|order| == |V|$.
  2. Set check: $\text{set}(order) == V$ (ensures no duplicates or missing courses).
  3. Precedence assertion: For every edge $(u, v) \in E$, $\text{pos}[u] < \text{pos}[v]$.
* **Asymptotic Time Complexity:** $\mathcal{O}(V \log V + E)$ (accounting for vertex sorting and edge validation).
* **Auxiliary Space:** $\mathcal{O}(V + E)$.

---

### 3.4 Multi-Priority Pedagogical Semester Scheduler

* **Function:** `schedule_courses(graph, max_courses_per_semester, max_difficulty_per_semester)`
* **Constraints Enforced:**
  1. **Prerequisite Ordering:** A course cannot be scheduled in semester $S_j$ unless all its prerequisites were completed in strictly earlier semesters $S_i$ ($i < j$).
  2. **Semester Course Capacity:** $|S_j| \le \text{max\_courses\_per\_semester}$ for all semesters $j$.
  3. **Workload Ceiling:** $\sum_{c \in S_j} \text{difficulty}(c) \le \text{max\_difficulty\_per\_semester}$.
  4. **Critical-Path Prioritization:** Ties among eligible courses are prioritized by their remaining longest dependency chain length to downstream courses.
* **Safety Verification:** `verify_semester_schedule(graph, semesters)` checks all constraints deterministically before returning.

---

## 4. Empirical Performance Benchmarks

Benchmarks executed on standard development hardware (Windows 11, AMD64, Python 3.12.4):

| Topology | $|V|$ | $|E|$ | Algorithm | Median Latency (ms) | Result |
| :--- | :---: | :---: | :--- | :---: | :---: |
| **Sparse DAG** | 10 | 15 | Kahn Toposort | 0.0078 ms | PASSED |
| Sparse DAG | 100 | 150 | Kahn Toposort | 0.0791 ms | PASSED |
| Sparse DAG | 500 | 750 | Kahn Toposort | 0.5054 ms | PASSED |
| Sparse DAG | 1000 | 1500 | Kahn Toposort | 1.1341 ms | PASSED |
| **Dense DAG** | 10 | 4 | Kahn Toposort | 0.0066 ms | PASSED |
| Dense DAG | 100 | 495 | Kahn Toposort | 0.1010 ms | PASSED |
| Dense DAG | 500 | 12,475 | Kahn Toposort | 1.3967 ms | PASSED |
| Dense DAG | 1000 | 49,950 | Kahn Toposort | 4.9258 ms | PASSED |
| **Linear Chain** | 10 | 9 | Kahn Toposort | 0.0096 ms | PASSED |
| Linear Chain | 100 | 99 | Kahn Toposort | 0.0591 ms | PASSED |
| Linear Chain | 500 | 499 | Kahn Toposort | 0.3485 ms | PASSED |
| Linear Chain | 1000 | 999 | Kahn Toposort | 0.7907 ms | PASSED |
| **Disconnected DAG** | 10 | 5 | Kahn Toposort | 0.0065 ms | PASSED |
| Disconnected DAG | 100 | 150 | Kahn Toposort | 0.0757 ms | PASSED |
| Disconnected DAG | 500 | 750 | Kahn Toposort | 0.6386 ms | PASSED |
| Disconnected DAG | 1000 | 1500 | Kahn Toposort | 1.1606 ms | PASSED |
| **Cyclic Graph** | 10 | 17 | DFS Cycle Detection | 0.0054 ms | Cycle Identified |
| Cyclic Graph | 100 | 153 | DFS Cycle Detection | 0.0583 ms | Cycle Identified |
| Cyclic Graph | 500 | 753 | DFS Cycle Detection | 0.2628 ms | Cycle Identified |
| Cyclic Graph | 1000 | 1503 | DFS Cycle Detection | 0.7081 ms | Cycle Identified |

### Scalability Findings
- Even on dense graphs with **$|V| = 1000$ and $|E| = 49,950$ edges**, Kahn's algorithm completes in under **5.0 milliseconds**.
- Cycle detection on 1000-vertex cyclic graphs completes in **0.70 milliseconds**.
- The explicit call stack in DFS eliminates recursion limits, supporting arbitrarily deep prerequisite chains.

