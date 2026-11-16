import { useState } from 'react';
import type { RoadmapModel } from '../../types/roadmap';
import { friendlyWarning } from '../../utils/warnings';
import { Alert } from '../common/ErrorState';
import { Tabs } from '../common/Tabs';
import { CourseRoadmap } from './CourseRoadmap';
import { RationalePanel } from './RationalePanel';
import { RelationshipExplorer } from './RelationshipExplorer';
import { SemesterSchedule } from './SemesterSchedule';
import { Summary } from './Summary';

export function RoadmapResults({ roadmap }: { roadmap: RoadmapModel }) {
  const [tab, setTab] = useState('journey');

  return (
    <div className="space-y-6">
      <div>
        <p className="text-support text-xs font-semibold uppercase tracking-wider">Topological Registration Schedule</p>
        <h2 className="h-section mt-0.5">Prerequisite-Aware Course Sequence</h2>
      </div>

      <Summary roadmap={roadmap} />

      {/* Educational Callout: How Topological Ordering Supports Reliable Planning */}
      <div className="card p-5 border-l-4 border-l-accent bg-accent/5 space-y-3">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-accent shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <h3 className="font-semibold text-ink text-sm">How Topological Ordering Guarantees Reliable Planning</h3>
        </div>
        <p className="text-xs text-ink-2 leading-relaxed">
          In university curricula, prerequisite relations define a directed graph <em>G = (V, E)</em>. Topological sorting provides the core mathematical guarantees that make degree planning reliable and conflict-free:
        </p>
        <div className="grid gap-2.5 sm:grid-cols-3 text-xs pt-1">
          <div className="bg-surface/80 rounded p-3 border border-divider space-y-1">
            <span className="font-bold text-accent">1. Prerequisite Precedence</span>
            <p className="text-support leading-relaxed">
              For every prerequisite edge <em>u → v</em>, course <em>u</em> is guaranteed to precede course <em>v</em> in the sequence. Students never face advanced coursework prematurely.
            </p>
          </div>
          <div className="bg-surface/80 rounded p-3 border border-divider space-y-1">
            <span className="font-bold text-accent">2. Circular Deadlock Prevention</span>
            <p className="text-support leading-relaxed">
              A topological order exists if and only if the graph is a DAG. 3-state DFS checks that zero circular dependencies (<em>A → B → A</em>) exist, preventing registration deadlocks.
            </p>
          </div>
          <div className="bg-surface/80 rounded p-3 border border-divider space-y-1">
            <span className="font-bold text-accent">3. Concurrent Semester Waves</span>
            <p className="text-support leading-relaxed">
              Courses with in-degree 0 at each wave are mutually independent. This enables institutions to safely schedule parallel course cohorts in the same semester.
            </p>
          </div>
        </div>
      </div>

      {roadmap.warnings.length > 0 && (
        <Alert
          tone="warning"
          role="note"
          title={roadmap.warnings.length === 1 ? 'Note about this path' : `${roadmap.warnings.length} notes about this path`}
        >
          <ul className="list-disc space-y-1 pl-4">
            {roadmap.warnings.map((w, i) => (
              <li key={i}>{friendlyWarning(w)}</li>
            ))}
          </ul>
        </Alert>
      )}

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: 'journey', label: 'Journey', content: <CourseRoadmap roadmap={roadmap} /> },
          { id: 'semesters', label: 'Semesters', content: <SemesterSchedule roadmap={roadmap} /> },
          { id: 'prerequisites', label: 'Prerequisites', content: <RelationshipExplorer roadmap={roadmap} /> },
          { id: 'explanations', label: 'Explanations', content: <RationalePanel roadmap={roadmap} /> },
        ]}
      />
    </div>
  );
}
