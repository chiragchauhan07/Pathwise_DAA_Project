import type { RoadmapModel } from '../../types/roadmap';
import { RelationBadge } from '../common/relations';

/** Every prerequisite relationship with its curriculum rationale and evidence. */
export function RationalePanel({ roadmap }: { roadmap: RoadmapModel }) {
  const names = new Map(roadmap.courses.map((c) => [c.course_id, c.name]));
  const edges = roadmap.edges.filter((e) => e.explanation);

  return (
    <div className="space-y-5">
      <p className="text-sm text-ink-2">
        {roadmap.edges.length === 0 ? (
          'There are no prerequisite dependencies among the selected courses.'
        ) : (
          <>{roadmap.edges.length} {roadmap.edges.length === 1 ? 'prerequisite relationship' : 'prerequisite relationships'} retrieved from the Curated Knowledge Base.</>
        )}
      </p>

      {edges.length > 0 ? (
        <ul className="space-y-3">
          {edges.map((e, i) => (
            <li key={i} className="card p-4">
              <p className="flex flex-wrap items-center gap-2 font-medium text-ink">
                <span>{names.get(e.source_course_id) ?? e.source_course_id}</span>
                <span className="text-support">→</span>
                <span>{names.get(e.target_course_id) ?? e.target_course_id}</span>
                <RelationBadge type={e.relationship_type} />
                <span className="badge badge-curated">Knowledge Base</span>
              </p>
              <p className="mt-2 text-sm leading-relaxed text-ink-2">{e.explanation}</p>
              {e.evidence_type && (
                <p className="text-support mt-2 text-xs">Evidence: {e.evidence_type.replace(/_/g, ' ')}</p>
              )}
            </li>
          ))}
        </ul>
      ) : roadmap.edges.length > 0 ? (
        <p className="card p-5 text-ink-2">Standard curricular prerequisites without custom written notes.</p>
      ) : null}
    </div>
  );
}
