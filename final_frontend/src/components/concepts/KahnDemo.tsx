import { useMemo, useState } from 'react';
import { Button } from '../common/Button';

const NAMES: Record<string, string> = {
  prog: 'Programming',
  discrete: 'Discrete Math',
  ds: 'Data Structures',
  algo: 'Algorithms',
  os: 'Operating Systems',
};

const EDGES: [string, string][] = [
  ['prog', 'ds'],
  ['ds', 'algo'],
  ['discrete', 'algo'],
  ['ds', 'os'],
];

const POS: Record<string, { x: number; y: number }> = {
  prog: { x: 70, y: 40 },
  discrete: { x: 70, y: 140 },
  ds: { x: 250, y: 40 },
  algo: { x: 430, y: 120 },
  os: { x: 430, y: 40 },
};

interface Step {
  text: string;
  selectedCourse: string | null;
  indegrees: Record<string, number>;
  readyQueue: string[];
  processed: string[];
  activeEdges: [string, string][];
}

function computeKahnSteps(): Step[] {
  const ids = Object.keys(NAMES);
  const indeg: Record<string, number> = Object.fromEntries(ids.map((id) => [id, 0]));
  for (const [, tgt] of EDGES) indeg[tgt]++;

  const steps: Step[] = [];
  const processed: string[] = [];

  // Initial step
  let ready = ids.filter((id) => indeg[id] === 0).sort();
  steps.push({
    text: `Initial State: Compute in-degree for every course (number of incoming prerequisite arrows). Zero-in-degree courses [${ready.map((r) => NAMES[r]).join(', ')}] have no prerequisites and are added to the ready min-heap.`,
    selectedCourse: null,
    indegrees: { ...indeg },
    readyQueue: [...ready],
    processed: [],
    activeEdges: [],
  });

  while (ready.length > 0) {
    // Pop min-element from ready heap
    const current = ready.shift()!;
    processed.push(current);

    // Identify outgoing edges from current
    const outgoing = EDGES.filter(([src]) => src === current);
    const freed: string[] = [];

    // Decrement indegrees for target courses
    for (const [, tgt] of outgoing) {
      indeg[tgt]--;
      if (indeg[tgt] === 0) {
        ready.push(tgt);
        freed.push(tgt);
      }
    }
    ready.sort();

    steps.push({
      text: `Process "${NAMES[current]}": Popped from ready heap. Decrement in-degree for dependent courses.${
        freed.length > 0
          ? ` In-degree for ${freed.map((f) => `"${NAMES[f]}"`).join(', ')} reached 0, so it is pushed to the ready heap.`
          : ' No new courses reached in-degree 0 in this step.'
      }`,
      selectedCourse: current,
      indegrees: { ...indeg },
      readyQueue: [...ready],
      processed: [...processed],
      activeEdges: outgoing,
    });
  }

  steps.push({
    text: `Complete: Ready queue is empty. All ${processed.length} courses have been topologically ordered without cyclic conflict: ${processed.map((p) => NAMES[p]).join(' → ')}. Verification confirms all dependency edges point left-to-right.`,
    selectedCourse: null,
    indegrees: { ...indeg },
    readyQueue: [],
    processed: [...processed],
    activeEdges: [],
  });

  return steps;
}

export function KahnDemo() {
  const steps = useMemo(computeKahnSteps, []);
  const [stepIdx, setStepIdx] = useState(0);

  const step = steps[stepIdx];

  return (
    <div className="card space-y-5 p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-divider pb-4">
        <div>
          <h3 className="h-card">Kahn's Algorithm with Min-Heap Tie-Breaking</h3>
          <p className="text-support mt-0.5">
            Deterministic topological sorting in \(\mathcal&#123;O&#125;(E + V \log V)\) time. Invariant: A course is processed only after all its prerequisites are completed.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button small disabled={stepIdx === 0} onClick={() => setStepIdx(stepIdx - 1)}>
            Previous
          </Button>
          <Button small disabled={stepIdx === steps.length - 1} onClick={() => setStepIdx(stepIdx + 1)}>
            Next Step
          </Button>
          <Button small variant="quiet" onClick={() => setStepIdx(0)}>
            Reset
          </Button>
          <span className="text-support ml-2 text-xs">
            {stepIdx + 1} / {steps.length}
          </span>
        </div>
      </div>

      <div className="grid items-center gap-6 lg:grid-cols-[minmax(0,34rem)_1fr]">
        {/* SVG Visualization */}
        <svg
          viewBox="0 0 540 200"
          className="w-full"
          role="img"
          aria-label={`Kahn algorithm walkthrough, step ${stepIdx + 1}. Processed so far: ${
            step.processed.map((id) => NAMES[id]).join(', ') || 'none'
          }`}
        >
          <defs>
            <marker id="k-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0 0L10 5 0 10z" fill="var(--color-ink)" />
            </marker>
            <marker id="k-arr-active" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0 0L10 5 0 10z" fill="var(--color-accent)" />
            </marker>
          </defs>

          {/* Edges */}
          {EDGES.map(([u, v]) => {
            const p1 = POS[u];
            const p2 = POS[v];
            const isActive = step.activeEdges.some(([a, b]) => a === u && b === v);
            const isDone = step.processed.includes(u);

            return (
              <line
                key={`${u}-${v}`}
                x1={p1.x + 65}
                y1={p1.y + 20}
                x2={p2.x - 65}
                y2={p2.y + 20}
                stroke={isActive ? 'var(--color-accent)' : isDone ? 'var(--color-muted)' : 'var(--color-ink)'}
                strokeWidth={isActive ? 2.5 : 1.4}
                strokeDasharray={isDone && !isActive ? '3 3' : 'none'}
                markerEnd={isActive ? 'url(#k-arr-active)' : 'url(#k-arr)'}
                opacity={isDone && !isActive ? 0.35 : 1}
              />
            );
          })}

          {/* Nodes */}
          {Object.keys(NAMES).map((id) => {
            const isProcessed = step.processed.includes(id);
            const isCurrent = step.selectedCourse === id;
            const isReady = step.readyQueue.includes(id);
            const currentIndeg = step.indegrees[id];

            return (
              <g key={id} transform={`translate(${POS[id].x - 65}, ${POS[id].y})`}>
                <rect
                  width="130"
                  height="42"
                  rx="10"
                  fill={
                    isCurrent
                      ? 'var(--color-info-bg)'
                      : isProcessed
                      ? 'var(--color-subtle)'
                      : isReady
                      ? '#ffffff'
                      : 'var(--color-surface)'
                  }
                  stroke={
                    isCurrent
                      ? 'var(--color-accent)'
                      : isReady
                      ? '#248a3d'
                      : isProcessed
                      ? 'var(--color-line)'
                      : 'var(--color-line)'
                  }
                  strokeWidth={isCurrent || isReady ? 2 : 1}
                />
                <text
                  x="65"
                  y="22"
                  dy="0.35em"
                  textAnchor="middle"
                  fontSize="12"
                  fontWeight="600"
                  fill={isProcessed && !isCurrent ? 'var(--color-ink-2)' : 'var(--color-ink)'}
                >
                  {NAMES[id]}
                </text>

                {/* In-Degree Counter Badge */}
                <circle
                  cx="120"
                  cy="6"
                  r="9"
                  fill={currentIndeg === 0 ? '#248a3d' : 'var(--color-ink)'}
                />
                <text
                  x="120"
                  y="6"
                  dy="0.35em"
                  textAnchor="middle"
                  fontSize="10"
                  fontWeight="700"
                  fill="#ffffff"
                >
                  {currentIndeg}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Narrative & In-Degree Table */}
        <div className="space-y-3">
          <div className="rounded-xl bg-surface-2 p-3.5">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">Step Narrative</p>
            <p className="mt-1 min-h-[4rem] text-sm leading-relaxed text-ink" aria-live="polite">
              {step.text}
            </p>
          </div>

          {/* Current In-Degrees Table */}
          <div className="overflow-hidden rounded-xl border border-divider text-xs">
            <div className="grid grid-cols-5 border-b border-divider bg-surface-2 p-2 text-center font-medium text-ink-2">
              <span>Prog</span>
              <span>Discrete</span>
              <span>DS</span>
              <span>Algo</span>
              <span>OS</span>
            </div>
            <div className="grid grid-cols-5 p-2 text-center font-semibold text-ink">
              <span>{step.indegrees.prog}</span>
              <span>{step.indegrees.discrete}</span>
              <span>{step.indegrees.ds}</span>
              <span>{step.indegrees.algo}</span>
              <span>{step.indegrees.os}</span>
            </div>
          </div>

          <div className="space-y-1.5 text-xs">
            <p>
              <b className="text-ink">Ready Queue (In-Degree = 0):</b>{' '}
              <span className="font-mono text-accent">
                {step.readyQueue.map((r) => NAMES[r]).join(', ') || '(empty)'}
              </span>
            </p>
            <p>
              <b className="text-ink">Resulting Topological Order:</b>{' '}
              <span className="font-mono text-ink-2">
                {step.processed.map((p) => NAMES[p]).join(' → ') || '(waiting to start)'}
              </span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
