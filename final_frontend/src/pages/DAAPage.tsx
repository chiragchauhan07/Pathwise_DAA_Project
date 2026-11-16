import { Link } from 'react-router-dom';
import { KahnDemo } from '../components/concepts/KahnDemo';
import { PageContainer } from '../components/layout/PageContainer';
import { useRoadmap } from '../hooks/useRoadmap';

export default function DAAPage() {
  const { roadmap } = useRoadmap();

  return (
    <PageContainer className="pt-10 pb-20">
      <header className="max-w-2xl">
        <span className="badge badge-curated text-xs font-mono">Unit 4: Graph Theory</span>
        <h1 className="h-page mt-2">Topological Sorting & Kahn's Algorithm</h1>
        <p className="mt-3 text-base text-ink-2 leading-relaxed">
          Course prerequisite planning is a textbook application of <strong>Directed Acyclic Graphs (DAGs)</strong> and <strong>Topological Sorting</strong>. This page outlines the core algorithm, step-by-step trace, and complexity analysis from our DAA curriculum.
        </p>
        {roadmap && (
          <p className="mt-3 text-sm">
            <Link to="/" className="font-medium text-accent hover:underline">
              ← Return to your course registration plan
            </Link>
          </p>
        )}
      </header>

      {/* 1. Core Problem & Mathematical Formulation */}
      <section className="mt-10 space-y-6">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-ink border-b border-divider pb-2">
            1. Why Topological Sorting? The Core DAA Principle
          </h2>
          <p className="mt-2 text-sm text-ink-2 leading-relaxed">
            In academic degree systems, course enrollment is not a random collection of subjects—it is a formal dependency network. A valid schedule must satisfy all pedagogical dependencies before higher-level topics are undertaken.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="card p-4 space-y-2">
            <h3 className="font-semibold text-ink text-sm">The Motivation</h3>
            <p className="text-xs text-ink-2 leading-relaxed">
              A student cannot take <em>Advanced Algorithms</em> before completing <em>Data Structures</em>. Every prerequisite must appear earlier than the course that depends on it.
            </p>
          </div>
          <div className="card p-4 space-y-2">
            <h3 className="font-semibold text-ink text-sm">Graph Representation</h3>
            <p className="text-xs text-ink-2 leading-relaxed">
              Courses are vertices <strong>V</strong>. A prerequisite requirement is a directed edge <strong>u → v</strong>, meaning <strong>course u must precede course v</strong>.
            </p>
          </div>
          <div className="card p-4 space-y-2">
            <h3 className="font-semibold text-ink text-sm">DAG Condition</h3>
            <p className="text-xs text-ink-2 leading-relaxed">
              A valid registration order exists <strong>if and only if</strong> the graph has no directed cycles. Cycles create deadlock dependencies where no course can be taken first.
            </p>
          </div>
        </div>

        {/* Detailed Educational Breakdown: Reliable vs Unreliable Planning */}
        <div className="card p-5 border border-accent/20 bg-accent/5 space-y-4">
          <h3 className="font-semibold text-ink text-base flex items-center gap-2">
            <svg className="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            How Topological Ordering Supports Reliable Planning
          </h3>
          <p className="text-xs text-ink-2 leading-relaxed">
            Topological ordering is the mathematical backbone of reliable curriculum planning. Without graph-theoretic scheduling, university enrollment suffers from severe logistical failure modes:
          </p>

          <div className="grid gap-3 sm:grid-cols-2 text-xs">
            <div className="card p-4 bg-surface border-divider space-y-2">
              <div className="font-semibold text-error flex items-center gap-1.5">
                <span>✕</span> Unreliable (Ad-Hoc / Intuitive) Planning
              </div>
              <ul className="list-disc pl-4 space-y-1 text-ink-2 text-[11px] leading-relaxed">
                <li><strong>Prerequisite Inversion:</strong> Students enroll in advanced subjects without foundational courses, resulting in high dropout and failure rates.</li>
                <li><strong>Undetected Deadlocks:</strong> Circular prerequisites (e.g. Course A requires B, B requires C, C requires A) freeze graduation paths indefinitely.</li>
                <li><strong>Unbalanced Term Loads:</strong> Ad-hoc sequencing clusters heavy dependent courses into single semesters, causing severe cognitive overload.</li>
                <li><strong>Administrative Bottlenecks:</strong> Manual advisor checks are slow, inconsistent, and prone to human oversight.</li>
              </ul>
            </div>

            <div className="card p-4 bg-surface border-divider space-y-2">
              <div className="font-semibold text-success flex items-center gap-1.5">
                <span>✓</span> Reliable (Topological Sorting) Planning
              </div>
              <ul className="list-disc pl-4 space-y-1 text-ink-2 text-[11px] leading-relaxed">
                <li><strong>Strict Precedence Invariant:</strong> For all edges (u, v), pos(u) &lt; pos(v). Zero forward-dependency violations are mathematically possible.</li>
                <li><strong>Provable Cycle Immunity:</strong> 3-state DFS identifies directed cycles in O(V + E) time, flagging conflicting prerequisites before registration opens.</li>
                <li><strong>Natural Concurrent Waves:</strong> All courses with in-degree 0 at step t are mutually independent and can be safely taken in parallel in the same semester.</li>
                <li><strong>Deterministic &amp; Reproducible:</strong> Consistent min-heap tie-breaking guarantees fair, identical schedules for thousands of students simultaneously.</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Kahn's Algorithm Steps */}
      <section className="mt-12 space-y-4">
        <h2 className="text-xl font-bold tracking-tight text-ink border-b border-divider pb-2">
          2. Kahn’s Algorithm (In-Degree + Queue)
        </h2>
        <p className="text-sm text-ink-2">
          Kahn's algorithm is an iterative, BFS-based approach that generates a valid topological order by maintaining the in-degree of each vertex.
        </p>

        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mt-4">
          <li className="card p-4 space-y-1">
            <span className="font-mono text-xs font-bold text-accent">STEP 1</span>
            <h4 className="font-semibold text-ink text-sm">Calculate In-Degrees</h4>
            <p className="text-xs text-ink-2">
              Count incoming edges for every vertex. In-degree represents the number of unfulfilled prerequisites.
            </p>
          </li>
          <li className="card p-4 space-y-1">
            <span className="font-mono text-xs font-bold text-accent">STEP 2</span>
            <h4 className="font-semibold text-ink text-sm">Enqueue Zero In-Degree</h4>
            <p className="text-xs text-ink-2">
              Find all courses with in-degree = 0 (no prerequisites). Add them to the ready queue Q.
            </p>
          </li>
          <li className="card p-4 space-y-1">
            <span className="font-mono text-xs font-bold text-accent">STEP 3</span>
            <h4 className="font-semibold text-ink text-sm">Process &amp; Decrement</h4>
            <p className="text-xs text-ink-2">
              Dequeue vertex u, append to output. For each neighbor v, decrement in-degree. If in-degree becomes 0, enqueue v.
            </p>
          </li>
          <li className="card p-4 space-y-1">
            <span className="font-mono text-xs font-bold text-accent">STEP 4</span>
            <h4 className="font-semibold text-ink text-sm">Cycle Verification</h4>
            <p className="text-xs text-ink-2">
              If output count = |V|, ordering is valid. If output count &lt; |V|, a circular dependency cycle exists!
            </p>
          </li>
        </ol>
      </section>

      {/* 3. Interactive Demonstration */}
      <section className="mt-12 space-y-4">
        <h2 className="text-xl font-bold tracking-tight text-ink border-b border-divider pb-2">
          3. Interactive Execution Trace
        </h2>
        <p className="text-sm text-ink-2">
          Step through Kahn's algorithm on a sample curriculum. Observe how in-degrees decrement and courses enter the queue as their prerequisites are completed.
        </p>
        <div className="mt-4">
          <KahnDemo />
        </div>
      </section>

      {/* 4. Classroom Trace Example Table */}
      <section className="mt-12 space-y-4">
        <h2 className="text-xl font-bold tracking-tight text-ink border-b border-divider pb-2">
          4. Prerequisite DAG &amp; Step-by-Step Execution Trace
        </h2>
        <p className="text-sm text-ink-2">
          The directed graph below illustrates the textbook prerequisite structure <em>G = (V, E)</em> with 6 courses and 6 directed edges. Initial in-degrees are shown below each vertex.
        </p>

        {/* Visual DAG Diagram */}
        <div className="card p-5 bg-surface border border-divider">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-divider pb-3 mb-4">
            <h3 className="font-semibold text-sm text-ink">Sample Curriculum Directed Acyclic Graph (DAG)</h3>
            <div className="flex items-center gap-4 text-xs text-ink-2 font-mono">
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-full border-2 border-accent bg-accent/10"></span>
                In-degree = 0 (Start)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-full border-2 border-divider bg-surface-2"></span>
                In-degree &gt; 0 (Dependent)
              </span>
            </div>
          </div>

          <div className="overflow-x-auto py-2">
            <svg viewBox="0 0 700 240" className="w-full max-w-[700px] mx-auto text-ink" aria-label="DAG Course Dependency Graph">
              <defs>
                <marker
                  id="dag-arrow"
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="currentColor" opacity="0.75" />
                </marker>
              </defs>

              {/* Edges */}
              {/* A -> C */}
              <line x1="112" y1="65" x2="258" y2="65" stroke="currentColor" strokeWidth="2" opacity="0.45" markerEnd="url(#dag-arrow)" />
              {/* B -> C */}
              <line x1="110" y1="155" x2="260" y2="75" stroke="currentColor" strokeWidth="2" opacity="0.45" markerEnd="url(#dag-arrow)" />
              {/* B -> D */}
              <line x1="112" y1="165" x2="258" y2="165" stroke="currentColor" strokeWidth="2" opacity="0.45" markerEnd="url(#dag-arrow)" />
              {/* C -> E */}
              <line x1="302" y1="65" x2="448" y2="65" stroke="currentColor" strokeWidth="2" opacity="0.45" markerEnd="url(#dag-arrow)" />
              {/* D -> F */}
              <line x1="302" y1="162" x2="588" y2="118" stroke="currentColor" strokeWidth="2" opacity="0.45" markerEnd="url(#dag-arrow)" />
              {/* E -> F */}
              <line x1="491" y1="72" x2="589" y2="108" stroke="currentColor" strokeWidth="2" opacity="0.45" markerEnd="url(#dag-arrow)" />

              {/* Node A (in-degree: 0) */}
              <g transform="translate(90, 65)">
                <circle r="22" className="fill-accent/15 stroke-accent" strokeWidth="2.5" />
                <text y="5" textAnchor="middle" className="font-mono font-bold text-base fill-accent">A</text>
                <text y="36" textAnchor="middle" className="font-mono text-[11px] fill-ink-2 font-medium">in-deg: 0</text>
              </g>

              {/* Node B (in-degree: 0) */}
              <g transform="translate(90, 165)">
                <circle r="22" className="fill-accent/15 stroke-accent" strokeWidth="2.5" />
                <text y="5" textAnchor="middle" className="font-mono font-bold text-base fill-accent">B</text>
                <text y="36" textAnchor="middle" className="font-mono text-[11px] fill-ink-2 font-medium">in-deg: 0</text>
              </g>

              {/* Node C (in-degree: 2) */}
              <g transform="translate(280, 65)">
                <circle r="22" className="fill-surface stroke-divider" strokeWidth="2" />
                <text y="5" textAnchor="middle" className="font-mono font-bold text-base fill-ink">C</text>
                <text y="36" textAnchor="middle" className="font-mono text-[11px] fill-ink-2 font-medium">in-deg: 2</text>
              </g>

              {/* Node D (in-degree: 1) */}
              <g transform="translate(280, 165)">
                <circle r="22" className="fill-surface stroke-divider" strokeWidth="2" />
                <text y="5" textAnchor="middle" className="font-mono font-bold text-base fill-ink">D</text>
                <text y="36" textAnchor="middle" className="font-mono text-[11px] fill-ink-2 font-medium">in-deg: 1</text>
              </g>

              {/* Node E (in-degree: 1) */}
              <g transform="translate(470, 65)">
                <circle r="22" className="fill-surface stroke-divider" strokeWidth="2" />
                <text y="5" textAnchor="middle" className="font-mono font-bold text-base fill-ink">E</text>
                <text y="36" textAnchor="middle" className="font-mono text-[11px] fill-ink-2 font-medium">in-deg: 1</text>
              </g>

              {/* Node F (in-degree: 2) */}
              <g transform="translate(610, 115)">
                <circle r="22" className="fill-surface stroke-divider" strokeWidth="2" />
                <text y="5" textAnchor="middle" className="font-mono font-bold text-base fill-ink">F</text>
                <text y="36" textAnchor="middle" className="font-mono text-[11px] fill-ink-2 font-medium">in-deg: 2</text>
              </g>
            </svg>
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-divider bg-surface mt-3">
          <table className="w-full text-left text-xs font-mono">
            <thead className="border-b border-divider bg-surface-2 text-muted uppercase tracking-wider font-sans">
              <tr>
                <th className="px-4 py-2.5">Step</th>
                <th className="px-4 py-2.5">Queue (front → rear)</th>
                <th className="px-4 py-2.5">Vertex Removed (u)</th>
                <th className="px-4 py-2.5">Updated In-degree</th>
                <th className="px-4 py-2.5">Topological Order</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-divider text-ink">
              <tr>
                <td className="px-4 py-2 text-muted">0</td>
                <td className="px-4 py-2">[A, B]</td>
                <td className="px-4 py-2 text-muted">—</td>
                <td className="px-4 py-2 text-muted">Initial state</td>
                <td className="px-4 py-2">[]</td>
              </tr>
              <tr>
                <td className="px-4 py-2 text-muted">1</td>
                <td className="px-4 py-2">[B]</td>
                <td className="px-4 py-2 font-bold text-accent">A</td>
                <td className="px-4 py-2">C: 2 → 1</td>
                <td className="px-4 py-2">[A]</td>
              </tr>
              <tr>
                <td className="px-4 py-2 text-muted">2</td>
                <td className="px-4 py-2">[C, D]</td>
                <td className="px-4 py-2 font-bold text-accent">B</td>
                <td className="px-4 py-2">C: 1 → 0 (enqueue C), D: 1 → 0 (enqueue D)</td>
                <td className="px-4 py-2">[A, B]</td>
              </tr>
              <tr>
                <td className="px-4 py-2 text-muted">3</td>
                <td className="px-4 py-2">[D, E]</td>
                <td className="px-4 py-2 font-bold text-accent">C</td>
                <td className="px-4 py-2">E: 1 → 0 (enqueue E)</td>
                <td className="px-4 py-2">[A, B, C]</td>
              </tr>
              <tr>
                <td className="px-4 py-2 text-muted">4</td>
                <td className="px-4 py-2">[E]</td>
                <td className="px-4 py-2 font-bold text-accent">D</td>
                <td className="px-4 py-2">F: 2 → 1</td>
                <td className="px-4 py-2">[A, B, C, D]</td>
              </tr>
              <tr>
                <td className="px-4 py-2 text-muted">5</td>
                <td className="px-4 py-2">[F]</td>
                <td className="px-4 py-2 font-bold text-accent">E</td>
                <td className="px-4 py-2">F: 1 → 0 (enqueue F)</td>
                <td className="px-4 py-2">[A, B, C, D, E]</td>
              </tr>
              <tr>
                <td className="px-4 py-2 text-muted">6</td>
                <td className="px-4 py-2">[]</td>
                <td className="px-4 py-2 font-bold text-accent">F</td>
                <td className="px-4 py-2 text-muted">—</td>
                <td className="px-4 py-2 font-bold text-success">[A, B, C, D, E, F]</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* 5. Complexity Analysis */}
      <section className="mt-12 space-y-4">
        <h2 className="text-xl font-bold tracking-tight text-ink border-b border-divider pb-2">
          5. Asymptotic Complexity Analysis
        </h2>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="card p-5 space-y-2">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">Time Complexity</span>
            <div className="text-2xl font-bold text-accent font-mono">O(V + E)</div>
            <p className="text-xs text-ink-2 leading-relaxed">
              <strong>Why?</strong> With an adjacency-list graph representation, each vertex enters and leaves the queue exactly once (|V|), and every directed prerequisite edge is examined exactly once (|E|) when decrementing in-degrees.
            </p>
          </div>

          <div className="card p-5 space-y-2">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">Auxiliary Space</span>
            <div className="text-2xl font-bold text-accent font-mono">O(V)</div>
            <p className="text-xs text-ink-2 leading-relaxed">
              <strong>Why?</strong> Stores the in-degree array of size |V|, the ready queue of at most |V| elements, and the output topological ordering list of size |V|.
            </p>
          </div>
        </div>
      </section>
    </PageContainer>
  );
}
