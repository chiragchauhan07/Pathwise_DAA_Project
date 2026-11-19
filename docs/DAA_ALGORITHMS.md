# DAA Graph Algorithms & Mathematical Proofs

The core computational engine of the Dependency-Aware Course Registration Assistant is implemented in `backend/daa_engine/` using pure Python without external graph packages. This document details the mathematical formulation, algorithmic complexity, proofs of correctness, and the graph-theoretic foundations of reliable academic planning.

---

## 1. Problem Formulation

Let $G = (V, E)$ be a directed graph representing an academic curriculum:
- **Vertices ($V$):** The set of distinct academic courses $\{v_1, v_2, \dots, v_n\}$.
- **Edges ($E$):** Directed pairs $(u, v)$ such that $u \to v$ signifies that course $u$ is a prerequisite for course $v$.
- **Goal:**
  1. Determine if $G$ is a Directed Acyclic Graph (DAG) or contains circular prerequisite deadlocks.
  2. If acyclic, find a linear topological ordering $L = [v_{\pi(1)}, v_{\pi(2)}, \dots, v_{\pi(n)}]$ such that for every directed edge $(u, v) \in E$, $\pi^{-1}(u) < \pi^{-1}(v)$.
  3. Ensure deterministic tie-breaking across different systems and runs using a priority min-heap.
  4. Partition $L$ into concurrent semester waves $S_1, S_2, \dots, S_k$ based on in-degree zero synchronization barriers.

---

## 2. Graph Representation

* **Module:** `backend/daa_engine/graph.py` (`DirectedGraph`)
* **Adjacency Representation:**
  - Forward adjacency: $\text{Adj}[u] = \{v \in V \mid (u, v) \in E\}$ stored as `Dict[str, List[str]]`.
  - In-degree dictionary: $\text{in\_degree}[v] = |\{u \in V \mid (u, v) \in E\}|$ stored as `Dict[str, int]`.
  - Edge deduplication set: `Set[Tuple[str, str]]` preventing repeated edges from inflating in-degree counts.
* **Space Complexity:** $\mathcal{O}(|V| + |E|)$, optimal for curricular dependency graphs.

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
  4. If $|L| < |V|$, invoke `detect_cycle_dfs` to isolate cycle components and raise `CycleConflictError`.
* **Asymptotic Time Complexity:** $\mathcal{O}(|E| + |V| \log |V|)$. Initial heap construction takes $\mathcal{O}(|V|)$. Each vertex is pushed and popped from the min-heap at most once ($\mathcal{O}(|V| \log |V|)$), and every edge is traversed exactly once ($\mathcal{O}(|E|)$).
* **Auxiliary Space:** $\mathcal{O}(|V| + |E|)$ for in-degree copies, the min-heap, and the output sequence.

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
    - `0 (WHITE)`: Unvisited.
    - `1 (GRAY)`: Currently active on the DFS recursion stack.
    - `2 (BLACK)`: Fully explored and verified acyclic.
  - Iterates with an explicit call stack of tuples $(u, \text{neighbor\_index})$ instead of native Python recursion.
  - If a neighbor $v$ is encountered with state `GRAY`, a back-edge $(u, v)$ has been identified.
  - The cycle path is reconstructed by collecting vertices from the stack between $v$ and $u$, followed by $v$.
* **Asymptotic Time Complexity:** $\mathcal{O}(|V| + |E|)$.
* **Auxiliary Space:** $\mathcal{O}(|V|)$ for color state tracking and explicit stack.

---

### 3.3 Topological Order Verifier

* **Function:** `verify_topological_order(graph, order)`
* **Safety Contract:**
  1. Cardinality check: $|order| == |V|$.
  2. Set check: $\text{set}(order) == V$ (ensures no duplicates or missing courses).
  3. Precedence assertion: For every edge $(u, v) \in E$, $\text{pos}[u] < \text{pos}[v]$.
* **Asymptotic Time Complexity:** $\mathcal{O}(|V| + |E|)$.
* **Auxiliary Space:** $\mathcal{O}(|V|)$.

---

### 3.4 Level-Order Wave Semester Scheduling

* **Function:** `schedule_courses(graph)`
* **Grouping Logic:**
  1. Identifies the initial frontier of courses with $\text{in-degree} = 0$. These courses have no unfulfilled prerequisites and constitute **Semester 1**.
  2. Removes this frontier and decrements the in-degrees of their outgoing neighbors.
  3. The next set of courses whose in-degrees become 0 forms **Semester 2**, continuing until all courses are scheduled.
* **Guarantee:** Guarantees that any course scheduled in Semester $k$ has all its prerequisites scheduled in Semesters $1$ to $k-1$.

---

## 4. How Topological Ordering Supports Reliable Planning

In academic institutions, course registration without graph algorithms frequently fails due to human oversight and complex dependencies. Topological sorting provides four foundational guarantees that make planning reliable:

1. **Guaranteed Prerequisite Precedence (Elimination of Forward References):**
   Topological sorting mathematically guarantees:
   $$\forall (u, v) \in E \implies \text{index}(u) < \text{index}(v)$$
   Students can never enroll in advanced courses prematurely, ensuring foundational mastery before specialized studies.

2. **Circular Prerequisite Deadlock Immunity:**
   A valid schedule exists if and only if the curriculum graph is a DAG. Circular dependencies ($A \to B \to C \to A$) prevent any course from being taken first. 3-state DFS identifies back-edges in $\mathcal{O}(|V| + |E|)$ time and isolates the exact cycle path, preventing registration gridlock.

3. **Natural Concurrent Semester Waves:**
   At each decay step, all zero-in-degree vertices are mutually independent ($\nexists (u, w) \in E$ between any pair in the wave). This enables universities to safely schedule course cohorts into the same semester concurrently without timetable clashes.

4. **Deterministic and Fair Student Pathways:**
   By employing deterministic tie-breaking (min-heap ordering), the algorithm guarantees that identical curriculum requirements yield identical, optimal, and reproducible graduation pathways, eliminating advisor bias and scheduling inconsistencies.
