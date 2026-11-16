import { useMemo, useState } from 'react';
import type { RoadmapModel } from '../../types/roadmap';
import { GraphLegend, PrereqGraph } from '../graph/PrereqGraph';
import { RelationBadge, asStrength } from '../common/relations';

export function RelationshipExplorer({ roadmap }: { roadmap: RoadmapModel }) {
  const [view, setView] = useState<'diagram' | 'list'>('diagram');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const names = useMemo(() => new Map(roadmap.courses.map((c) => [c.course_id, c.name])), [roadmap]);
  const sel = roadmap.courses.find((c) => c.course_id === selectedId);

  if (roadmap.edges.length === 0)
    return <p className="card p-5 text-ink-2">None of the selected courses depend on each other, so there are no prerequisite relationships to show.</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <GraphLegend />
        <div role="group" aria-label="Relationship view" className="inline-flex rounded-lg border border-line bg-subtle p-0.5">
          {(['diagram', 'list'] as const).map((v) => (
            <button
              key={v}
              type="button"
              aria-pressed={view === v}
              onClick={() => setView(v)}
              className={`min-h-8 rounded-md px-3 text-sm font-medium ${view === v ? 'bg-surface shadow-[var(--shadow-card)]' : 'text-ink-2'}`}
            >
              {v === 'diagram' ? 'Graph Diagram' : 'Dependency List'}
            </button>
          ))}
        </div>
      </div>

      {view === 'diagram' ? (
        <>
          <p className="text-support text-xs">Directed edges point from prerequisite u to dependent v. Click a course vertex to highlight incident edges.</p>
          <PrereqGraph roadmap={roadmap} selectedId={selectedId} onSelect={setSelectedId} />
          <p className="min-h-5 text-sm text-ink-2" aria-live="polite">
            {sel ? (
              <>
                <b className="text-ink">{sel.name}</b>: requires {sel.prerequisites.length ? sel.prerequisites.map((p) => names.get(p.courseId) ?? p.courseId).join(', ') : 'none'}; unlocks {sel.unlocks.length ? sel.unlocks.map((p) => names.get(p.courseId) ?? p.courseId).join(', ') : 'none'}.
              </>
            ) : 'Select a course to inspect its incoming and outgoing dependencies.'}
          </p>
        </>
      ) : (
        <ul className="divide-y divide-divider overflow-hidden rounded-xl border border-divider bg-surface" aria-label="Relationships as text">
          {roadmap.courses.filter((c) => c.prerequisites.length > 0).map((c) => (
            <li key={c.course_id} className="p-4">
              <p className="font-medium text-ink">{c.name} <span className="text-support font-normal">requires:</span></p>
              <ul className="mt-2 space-y-1.5">
                {c.prerequisites.map((p) => (
                  <li key={p.courseId} className="flex flex-wrap items-center gap-2 text-sm text-ink-2">
                    <RelationBadge type={p.type} />
                    <span>{names.get(p.courseId) ?? p.courseId}</span>
                    <span className="badge badge-curated">Knowledge Base</span>
                    <span className="sr-only">{asStrength(p.type) ?? p.type}</span>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
