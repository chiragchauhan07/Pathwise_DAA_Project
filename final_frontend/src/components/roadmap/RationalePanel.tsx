import type { RoadmapModel } from '../../types/roadmap';
import { RelationBadge, SourceBadge } from '../common/relations';

/** Every relationship that comes with a backend explanation, with its provenance. */
export function RationalePanel({ roadmap }: { roadmap: RoadmapModel }) {
  const names = new Map(roadmap.courses.map((c) => [c.course_id, c.name]));
  const edges = roadmap.edges.filter((e) => e.explanation);
  const ai = roadmap.edges.filter((e) => e.is_ai_proposed || e.source === 'ai_proposed').length;
  return (
    <div className="space-y-5">
      <p className="text-sm text-ink-2">
        {roadmap.edges.length === 0 ? 'There are no prerequisite links in this path.' : <>{roadmap.edges.length - ai} curated and {ai} AI-proposed {roadmap.edges.length === 1 ? 'relationship' : 'relationships'}. AI proposals passed validation but are not expert-verified.</>}
      </p>
      {edges.length > 0 ? (
        <ul className="space-y-3">
          {edges.map((e, i) => (
            <li key={i} className="card p-4">
              <p className="flex flex-wrap items-center gap-2 font-medium">
                {names.get(e.source_course_id)} → {names.get(e.target_course_id)}
                <RelationBadge type={e.relationship_type} /> <SourceBadge ai={Boolean(e.is_ai_proposed) || e.source === 'ai_proposed'} />
              </p>
              <p className="mt-2 text-sm leading-relaxed text-ink-2">{e.explanation}</p>
              {(typeof e.confidence === 'number' || e.evidence_type) && (
                <p className="text-support mt-2">{[typeof e.confidence === 'number' && `Confidence ${Math.round(e.confidence * 100)}%`, e.evidence_type && e.evidence_type.replace(/_/g, ' ')].filter(Boolean).join(' · ')}</p>
              )}
            </li>
          ))}
        </ul>
      ) : roadmap.edges.length > 0 ? <p className="card p-5 text-ink-2">The backend didn’t include written explanations for these relationships.</p> : null}
    </div>
  );
}
