import { Link } from 'react-router-dom';
import { KahnDemo } from '../components/concepts/KahnDemo';
import { DfsCycleDemo } from '../components/concepts/DfsCycleDemo';
import { SchedulerDemo } from '../components/concepts/SchedulerDemo';
import { CycleDiagram, GraphDiagram, SemesterDiagram, SortDiagram } from '../components/concepts/StepDiagrams';
import { PageContainer } from '../components/layout/PageContainer';
import { useRoadmap } from '../hooks/useRoadmap';

const STEPS = [
  {
    title: 'Adjacency-List Graph Construction',
    Diagram: GraphDiagram,
    text: 'Each course is a vertex \(V\). Each prerequisite is a directed edge \(E\) from prerequisite \(u\) to dependent \(v\).',
    detail: 'Stored via custom DirectedGraph with adjacency lists and edge registries preventing duplicate insertions. Construction is optimal at \(\mathcal{O}(V + E)\).',
  },
  {
    title: 'Iterative 3-State DFS Cycle Detection',
    Diagram: CycleDiagram,
    text: 'Cycles cause deadlock dependencies (A needs B, B needs A). An explicit iterative 3-state DFS identifies any back-edge and extracts the conflict path.',
    detail: 'Iterative DFS with states WHITE (unvisited), GRAY (active on stack), and BLACK (acyclic). \(\mathcal{O}(V \log V + E)\) time. Handles deep recursion chains >1,500 nodes without stack overflow.',
  },
  {
    title: 'Deterministic Kahn’s Topological Sort',
    Diagram: SortDiagram,
    text: 'A course is scheduled only when all its prerequisites have been fulfilled. Ties between ready courses are broken via min-heap for deterministic ordering.',
    detail: 'Kahn’s algorithm using Python heapq min-heap, \(\mathcal{O}(E + V \log V)\) time. Topological ordering is formally verified via bijection and edge direction validation.',
  },
  {
    title: 'Pedagogical Wave Scheduling & Capacity Optimization',
    Diagram: SemesterDiagram,
    text: 'The sorted DAG is partitioned into valid academic semesters using DAG longest-path wave layering or multi-priority list scheduling under capacity caps.',
    detail: 'Unconstrained: \(\mathcal{O}(V \log V + E)\). Constrained by workload cap \(K\): multi-priority list scheduling optimizing critical depth, soft links, and difficulty, \(\mathcal{O}(V^2 \log V + V \cdot E)\).',
  },
];

const COMPLEXITY_TABLE = [
  {
    operation: 'Graph Construction',
    algorithm: 'DirectedGraph (Adjacency List)',
    timeComplexity: 'O(V + E)',
    spaceComplexity: 'O(V + E)',
    description: 'Builds outgoing adjacency lists, in-degree dictionary, and edge deduplication registry.',
  },
  {
    operation: 'Cycle Detection',
    algorithm: 'Iterative 3-State DFS',
    timeComplexity: 'O(V log V + E)',
    spaceComplexity: 'O(V)',
    description: '3-color DFS using explicit stack; extracts exact directed cycle path upon detecting a back-edge.',
  },
  {
    operation: 'Topological Sort',
    algorithm: "Kahn's Algorithm (Min-Heap)",
    timeComplexity: 'O(E + V log V)',
    spaceComplexity: 'O(V + E)',
    description: 'Processes in-degree 0 courses; Python heapq min-heap guarantees deterministic tie-breaking across runs.',
  },
  {
    operation: 'Order Verification',
    algorithm: 'Strict Edge Verifier',
    timeComplexity: 'O(V log V + E)',
    spaceComplexity: 'O(V + E)',
    description: 'Asserts bijection and verifies pos[u] < pos[v] for every directed dependency edge in E.',
  },
  {
    operation: 'Unconstrained Scheduling',
    algorithm: 'DAG Longest-Path Wave Layering',
    timeComplexity: 'O(V log V + E)',
    spaceComplexity: 'O(V + E)',
    description: 'Computes earliest valid term wave using longest-path layering, difficulty, and min-heap ordering.',
  },
  {
    operation: 'Constrained Scheduling',
    algorithm: 'Multi-Priority List Scheduling',
    timeComplexity: 'O(V² log V + V·E)',
    spaceComplexity: 'O(V + E)',
    description: 'Enforces workload cap K per semester. Prioritizes critical depth, soft links, and difficulty.',
  },
  {
    operation: 'Schedule Verification',
    algorithm: 'Dual Constraint Verifier',
    timeComplexity: 'O(V + E)',
    spaceComplexity: 'O(V)',
    description: 'Asserts semester sequence consistency, capacity bounds, and strict prerequisite precedence.',
  },
];

export default function DAAPage() {
  const { roadmap } = useRoadmap();

  return (
    <PageContainer className="pt-10">
      <header className="max-w-2xl">
        <h1 className="h-page">Design & Analysis of Algorithms</h1>
        <p className="mt-3 text-base text-ink-2">
          Pathwise is built on formal graph theory and deterministic scheduling algorithms implemented in Python in the backend DAA engine.
        </p>
        {roadmap && (
          <p className="mt-3 text-sm">
            <Link to="/" className="font-medium text-accent hover:underline">
              Return to your latest learning path
            </Link>
          </p>
        )}
      </header>

      {/* 4 Pipeline Stages */}
      <section aria-labelledby="steps" className="mt-12">
        <h2 id="steps" className="h-section">Algorithmic Pipeline</h2>
        <p className="text-support mt-1">Four deterministic stages executed sequentially on the FastAPI backend.</p>
        <ol className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <li key={s.title} className="card flex flex-col p-4">
              <div className="rounded-lg bg-surface-2 p-2"><s.Diagram /></div>
              <h3 className="h-card mt-4">{i + 1}. {s.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-2">{s.text}</p>
              <details className="mt-3 text-sm">
                <summary className="cursor-pointer font-medium text-accent">Technical detail</summary>
                <p className="mt-2 text-ink-2">{s.detail}</p>
              </details>
            </li>
          ))}
        </ol>
      </section>

      {/* Interactive Demonstration 1: Kahn's Algorithm */}
      <section aria-labelledby="kahn" className="mt-12">
        <h2 id="kahn" className="h-section">1. Kahn’s Algorithm: Interactive Step-by-Step</h2>
        <p className="text-support mt-1">
          Observe how in-degrees change and courses are processed through the ready min-heap.
        </p>
        <div className="mt-5"><KahnDemo /></div>
      </section>

      {/* Interactive Demonstration 2: DFS Cycle Detection */}
      <section aria-labelledby="dfs" className="mt-12">
        <h2 id="dfs" className="h-section">2. DFS Cycle Detection: Acyclic vs. Cyclic Conflict</h2>
        <p className="text-support mt-1">
          Explore how 3-state DFS classifies nodes and traps back-edges that create deadlock dependencies.
        </p>
        <div className="mt-5"><DfsCycleDemo /></div>
      </section>

      {/* Interactive Demonstration 3: Pedagogical Scheduling */}
      <section aria-labelledby="scheduler" className="mt-12">
        <h2 id="scheduler" className="h-section">3. Pedagogical Semester Scheduling</h2>
        <p className="text-support mt-1">
          Compare unconstrained longest-path wave layering with capacity-constrained list scheduling.
        </p>
        <div className="mt-5"><SchedulerDemo /></div>
      </section>

      {/* Time & Space Complexity Table */}
      <section aria-labelledby="complexity" className="mt-12">
        <h2 id="complexity" className="h-section">Time & Space Complexity</h2>
        <p className="text-support mt-1">
          Formal asymptotic complexities verified across unit tests and empirical benchmarks up to \(V = 1000\) and \(E = 49,950\).
        </p>

        <div className="mt-5 overflow-x-auto rounded-xl border border-divider bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-divider bg-surface-2 text-xs font-semibold uppercase tracking-wider text-muted">
              <tr>
                <th className="px-4 py-3">Operation</th>
                <th className="px-4 py-3">Algorithm</th>
                <th className="px-4 py-3">Time Complexity</th>
                <th className="px-4 py-3">Auxiliary Space</th>
                <th className="px-4 py-3">Mechanics</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-divider font-mono text-xs text-ink">
              {COMPLEXITY_TABLE.map((row) => (
                <tr key={row.operation} className="hover:bg-subtle/50 transition-colors">
                  <td className="px-4 py-3 font-sans font-medium text-ink">{row.operation}</td>
                  <td className="px-4 py-3 font-sans text-ink-2">{row.algorithm}</td>
                  <td className="px-4 py-3 font-semibold text-accent">{row.timeComplexity}</td>
                  <td className="px-4 py-3 text-ink-2">{row.spaceComplexity}</td>
                  <td className="px-4 py-3 font-sans text-xs text-muted">{row.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Educational Walkthrough Disclosure */}
      <aside className="mt-10 rounded-xl border border-line bg-surface-2 p-4 text-xs text-muted" role="note">
        <p>
          <b>Educational Demonstration Disclosure:</b> The interactive visualizations on this page are educational walkthroughs designed to illustrate the algorithmic mechanics utilized by Pathwise. The actual sorting, cycle detection, and scheduling for your learning path are computed deterministically on the Python FastAPI backend using custom data structures without third-party graph libraries.
        </p>
      </aside>
    </PageContainer>
  );
}
