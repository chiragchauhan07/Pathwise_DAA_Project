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
      <section className="mt-10 space-y-4">
        <h2 className="text-xl font-bold tracking-tight text-ink border-b border-divider pb-2">
          1. Why Topological Sorting?
        </h2>
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
              Courses are vertices \(V\). A prerequisite requirement is a directed edge \(u \to v\), meaning <strong>course \(u\) must precede course \(v\)</strong>.
            </p>
          </div>
          <div className="card p-4 space-y-2">
            <h3 className="font-semibold text-ink text-sm">DAG Condition</h3>
            <p className="text-xs text-ink-2 leading-relaxed">
              A valid registration order exists <strong>if and only if</strong> the graph has no directed cycles. Cycles create deadlock dependencies where no course can be taken first.
            </p>
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
              Find all courses with in-degree = 0 (no prerequisites). Add them to the ready queue \(Q\).
            </p>
          </li>
          <li className="card p-4 space-y-1">
            <span className="font-mono text-xs font-bold text-accent">STEP 3</span>
            <h4 className="font-semibold text-ink text-sm">Process & Decrement</h4>
            <p className="text-xs text-ink-2">
              Dequeue vertex \(u\), append to output. For each neighbor \(v\), decrement in-degree. If in-degree becomes 0, enqueue \(v\).
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
          4. Step-by-Step Execution Table
        </h2>
        <p className="text-sm text-ink-2">
          Example trace for DAG: <code>A → C</code>, <code>B → C</code>, <code>B → D</code>, <code>C → E</code>, <code>D → F</code>, <code>E → F</code>.
          Initial in-degrees: A=0, B=0, C=2, D=1, E=1, F=2.
        </p>

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
              <strong>Why?</strong> With an adjacency-list graph representation, each vertex enters and leaves the queue exactly once (\(V\)), and every directed prerequisite edge is examined exactly once (\(E\)) when decrementing in-degrees.
            </p>
          </div>

          <div className="card p-5 space-y-2">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">Auxiliary Space</span>
            <div className="text-2xl font-bold text-accent font-mono">O(V)</div>
            <p className="text-xs text-ink-2 leading-relaxed">
              <strong>Why?</strong> Stores the in-degree array of size \(V\), the ready queue of at most \(V\) elements, and the output topological ordering list of size \(V\).
            </p>
          </div>
        </div>
      </section>
    </PageContainer>
  );
}
