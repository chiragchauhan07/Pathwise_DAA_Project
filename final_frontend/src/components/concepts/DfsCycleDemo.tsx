import { useState } from 'react';
import { Button } from '../common/Button';

type NodeState = 'WHITE' | 'GRAY' | 'BLACK';

interface DemoGraph {
  name: string;
  isCyclic: boolean;
  nodes: string[];
  labels: Record<string, string>;
  edges: [string, string][];
  positions: Record<string, { x: number; y: number }>;
  steps: {
    text: string;
    nodeStates: Record<string, NodeState>;
    activeEdge?: [string, string];
    cycleDetected?: string[];
  }[];
}

const ACYCLIC_GRAPH: DemoGraph = {
  name: 'Acyclic DAG (Valid Prerequisites)',
  isCyclic: false,
  nodes: ['prog', 'ds', 'algo'],
  labels: { prog: 'Programming', ds: 'Data Structures', algo: 'Algorithms' },
  edges: [['prog', 'ds'], ['ds', 'algo']],
  positions: { prog: { x: 80, y: 80 }, ds: { x: 260, y: 80 }, algo: { x: 440, y: 80 } },
  steps: [
    {
      text: 'Start: All nodes are initialized to WHITE (unvisited). Call stack is empty.',
      nodeStates: { prog: 'WHITE', ds: 'WHITE', algo: 'WHITE' },
    },
    {
      text: 'Visit Programming: State changes to GRAY (active on DFS path). Exploring outgoing edge to Data Structures.',
      nodeStates: { prog: 'GRAY', ds: 'WHITE', algo: 'WHITE' },
      activeEdge: ['prog', 'ds'],
    },
    {
      text: 'Visit Data Structures: State changes to GRAY. Exploring outgoing edge to Algorithms.',
      nodeStates: { prog: 'GRAY', ds: 'GRAY', algo: 'WHITE' },
      activeEdge: ['ds', 'algo'],
    },
    {
      text: 'Visit Algorithms: State changes to GRAY. No outgoing edges remain.',
      nodeStates: { prog: 'GRAY', ds: 'GRAY', algo: 'GRAY' },
    },
    {
      text: 'Finish Algorithms: Marked BLACK (fully explored, acyclic). Backtrack to Data Structures.',
      nodeStates: { prog: 'GRAY', ds: 'GRAY', algo: 'BLACK' },
    },
    {
      text: 'Finish Data Structures: Marked BLACK. Backtrack to Programming.',
      nodeStates: { prog: 'GRAY', ds: 'BLACK', algo: 'BLACK' },
    },
    {
      text: 'Finish Programming: Marked BLACK. Graph contains no back-edges. Verification SUCCESS: Acyclic DAG.',
      nodeStates: { prog: 'BLACK', ds: 'BLACK', algo: 'BLACK' },
    },
  ],
};

const CYCLIC_GRAPH: DemoGraph = {
  name: 'Cyclic Graph (Deadlock Dependency)',
  isCyclic: true,
  nodes: ['a', 'b', 'c'],
  labels: { a: 'Course A', b: 'Course B', c: 'Course C' },
  edges: [['a', 'b'], ['b', 'c'], ['c', 'a']],
  positions: { a: { x: 260, y: 40 }, b: { x: 420, y: 130 }, c: { x: 100, y: 130 } },
  steps: [
    {
      text: 'Start: All nodes are WHITE (unvisited). A cyclic relationship exists: A → B → C → A.',
      nodeStates: { a: 'WHITE', b: 'WHITE', c: 'WHITE' },
    },
    {
      text: 'Visit Course A: Marked GRAY (active on stack). Exploring edge A → B.',
      nodeStates: { a: 'GRAY', b: 'WHITE', c: 'WHITE' },
      activeEdge: ['a', 'b'],
    },
    {
      text: 'Visit Course B: Marked GRAY (active on stack). Exploring edge B → C.',
      nodeStates: { a: 'GRAY', b: 'GRAY', c: 'WHITE' },
      activeEdge: ['b', 'c'],
    },
    {
      text: 'Visit Course C: Marked GRAY (active on stack). Exploring edge C → A.',
      nodeStates: { a: 'GRAY', b: 'GRAY', c: 'GRAY' },
      activeEdge: ['c', 'a'],
    },
    {
      text: 'CONFLICT DETECTED! Edge C → A targets Course A which is currently GRAY (ancestor on DFS stack). This is a BACK-EDGE! Cycle extracted: A → B → C → A.',
      nodeStates: { a: 'GRAY', b: 'GRAY', c: 'GRAY' },
      activeEdge: ['c', 'a'],
      cycleDetected: ['Course A', 'Course B', 'Course C', 'Course A'],
    },
  ],
};

export function DfsCycleDemo() {
  const [mode, setMode] = useState<'acyclic' | 'cyclic'>('acyclic');
  const [stepIdx, setStepIdx] = useState(0);

  const graph = mode === 'acyclic' ? ACYCLIC_GRAPH : CYCLIC_GRAPH;
  const currentStep = graph.steps[Math.min(stepIdx, graph.steps.length - 1)];

  const switchMode = (m: 'acyclic' | 'cyclic') => {
    setMode(m);
    setStepIdx(0);
  };

  const stateColors: Record<NodeState, { bg: string; border: string; text: string }> = {
    WHITE: { bg: 'var(--color-surface)', border: 'var(--color-line)', text: 'var(--color-ink-2)' },
    GRAY: { bg: 'var(--color-warning-bg)', border: 'var(--color-warning)', text: 'var(--color-warning)' },
    BLACK: { bg: 'var(--color-subtle)', border: 'var(--color-ink)', text: 'var(--color-ink)' },
  };

  return (
    <div className="card space-y-4 p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-divider pb-4">
        <div>
          <h3 className="h-card">Iterative 3-State DFS Cycle Detection</h3>
          <p className="text-support mt-0.5">
            Detects back-edges pointing to active nodes on the DFS stack in \(\mathcal&#123;O&#125;(V \log V + E)\) time.
          </p>
        </div>
        <div role="group" aria-label="Graph cycle condition" className="inline-flex rounded-lg border border-line bg-subtle p-0.5">
          <button
            type="button"
            aria-pressed={mode === 'acyclic'}
            onClick={() => switchMode('acyclic')}
            className={`min-h-8 rounded-md px-3 text-sm font-medium transition-all ${
              mode === 'acyclic' ? 'bg-surface shadow-[var(--shadow-card)] text-ink' : 'text-ink-2'
            }`}
          >
            Acyclic DAG
          </button>
          <button
            type="button"
            aria-pressed={mode === 'cyclic'}
            onClick={() => switchMode('cyclic')}
            className={`min-h-8 rounded-md px-3 text-sm font-medium transition-all ${
              mode === 'cyclic' ? 'bg-surface shadow-[var(--shadow-card)] text-ink' : 'text-ink-2'
            }`}
          >
            Cyclic Graph (Cycle Conflict)
          </button>
        </div>
      </div>

      {/* SVG Canvas for DFS traversal */}
      <div className="grid items-center gap-6 lg:grid-cols-[minmax(0,34rem)_1fr]">
        <svg viewBox="0 0 520 200" className="w-full" role="img" aria-label={`DFS Cycle Detection on ${graph.name}, Step ${stepIdx + 1}`}>
          <defs>
            <marker id="dfs-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0 0L10 5 0 10z" fill="var(--color-ink)" />
            </marker>
            <marker id="dfs-arr-active" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0 0L10 5 0 10z" fill="var(--color-warning)" />
            </marker>
            <marker id="dfs-arr-error" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0 0L10 5 0 10z" fill="var(--color-error)" />
            </marker>
          </defs>

          {/* Edges */}
          {graph.edges.map(([u, v]) => {
            const p1 = graph.positions[u];
            const p2 = graph.positions[v];
            const isActive = currentStep.activeEdge && currentStep.activeEdge[0] === u && currentStep.activeEdge[1] === v;
            const isBackEdge = currentStep.cycleDetected && currentStep.activeEdge && currentStep.activeEdge[0] === u && currentStep.activeEdge[1] === v;

            // Direct line with offset to avoid clipping nodes
            const dx = p2.x - p1.x;
            const dy = p2.y - p1.y;
            const dist = Math.hypot(dx, dy) || 1;
            const offsetX = (dx / dist) * 45;
            const offsetY = (dy / dist) * 22;

            return (
              <line
                key={`${u}-${v}`}
                x1={p1.x + offsetX}
                y1={p1.y + offsetY}
                x2={p2.x - offsetX}
                y2={p2.y - offsetY}
                stroke={isBackEdge ? 'var(--color-error)' : isActive ? 'var(--color-warning)' : 'var(--color-line)'}
                strokeWidth={isBackEdge || isActive ? 2.5 : 1.5}
                strokeDasharray={isBackEdge ? '4 4' : 'none'}
                markerEnd={isBackEdge ? 'url(#dfs-arr-error)' : isActive ? 'url(#dfs-arr-active)' : 'url(#dfs-arr)'}
              />
            );
          })}

          {/* Nodes */}
          {graph.nodes.map((nodeId) => {
            const p = graph.positions[nodeId];
            const st = currentStep.nodeStates[nodeId] || 'WHITE';
            const colors = stateColors[st];

            return (
              <g key={nodeId} transform={`translate(${p.x - 60}, ${p.y - 20})`}>
                <rect
                  width="120"
                  height="40"
                  rx="10"
                  fill={colors.bg}
                  stroke={colors.border}
                  strokeWidth={st === 'GRAY' ? 2 : 1.2}
                />
                <text x="60" y="21" dy="0.35em" textAnchor="middle" fontSize="12" fontWeight="600" fill={colors.text}>
                  {graph.labels[nodeId]}
                </text>
                {/* State Tag badge */}
                <rect x="4" y="-8" width="46" height="15" rx="4" fill={colors.border} />
                <text x="27" y="0" textAnchor="middle" fontSize="9" fontWeight="700" fill="#ffffff">
                  {st}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Narrative & Controls */}
        <div className="space-y-3">
          <div className="rounded-xl bg-surface-2 p-3.5">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">
              Step {stepIdx + 1} of {graph.steps.length}
            </p>
            <p className="mt-1 min-h-[3.5rem] text-sm leading-relaxed text-ink" aria-live="polite">
              {currentStep.text}
            </p>
          </div>

          {currentStep.cycleDetected && (
            <div className="rounded-xl border border-[#f2c4c8] bg-error-bg p-3 text-sm">
              <p className="font-semibold text-error">Cycle Conflict Path Detected:</p>
              <p className="mt-1 font-mono text-xs text-ink">{currentStep.cycleDetected.join(' → ')}</p>
            </div>
          )}

          {/* State Legend */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-ink-2">
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full border border-line bg-surface" /> WHITE (Unvisited)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-warning" /> GRAY (Active on Stack)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-ink" /> BLACK (Acyclic Visited)
            </span>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <Button small disabled={stepIdx === 0} onClick={() => setStepIdx(stepIdx - 1)}>
              Previous
            </Button>
            <Button small disabled={stepIdx === graph.steps.length - 1} onClick={() => setStepIdx(stepIdx + 1)}>
              Next Step
            </Button>
            <Button small variant="quiet" onClick={() => setStepIdx(0)}>
              Reset
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

