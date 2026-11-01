import type { Relation, RoadmapCourse } from '../../types/roadmap';

export type Strength = 'required' | 'recommended' | 'optional';

export const STRENGTH_LABEL: Record<Strength, string> = { required: 'Required', recommended: 'Recommended', optional: 'Optional' };
export const STRENGTH_HELP: Record<Strength, string> = {
  required: 'Needed before this course.',
  recommended: 'Makes this course easier.',
  optional: 'Useful background only.',
};

const RANK: Record<string, number> = { required: 3, recommended: 2, optional: 1 };
export const asStrength = (t: string): Strength | null => (t in RANK ? (t as Strength) : null);
export const byStrength = (a: Relation, b: Relation) => (RANK[b.type] ?? 0) - (RANK[a.type] ?? 0);

export const isAi = (r: { isAiProposed?: boolean; source?: string }) => Boolean(r.isAiProposed) || r.source === 'ai_proposed';

export function strongestIncoming(c: Pick<RoadmapCourse, 'prerequisites'>): Strength | null {
  let best: Strength | null = null;
  for (const p of c.prerequisites) {
    const s = asStrength(p.type);
    if (s && (!best || RANK[s] > RANK[best])) best = s;
  }
  return best;
}

const BADGE: Record<Strength, string> = { required: 'badge badge-req', recommended: 'badge badge-rec', optional: 'badge badge-opt' };

/** Text label plus a line-style swatch, so the type never depends on colour alone. */
export function RelationBadge({ type }: { type: string }) {
  const s = asStrength(type);
  if (!s) return <span className="badge badge-neutral">{type}</span>;
  return (
    <span className={BADGE[s]} title={`${STRENGTH_LABEL[s]}: ${STRENGTH_HELP[s]}`}>
      <LineSwatch type={s} light={s === 'required'} />
      {STRENGTH_LABEL[s]}
    </span>
  );
}

export function SourceBadge({ ai }: { ai: boolean }) {
  return ai ? (
    <span className="badge badge-ai" title="Proposed by AI and passed validation. Not expert-verified.">AI-proposed</span>
  ) : (
    <span className="badge badge-curated" title="From the curated knowledge base.">Curated</span>
  );
}

export const EDGE_COLOR: Record<Strength, string> = {
  required: 'var(--color-rel-required)',
  recommended: 'var(--color-rel-recommended-line)',
  optional: 'var(--color-rel-optional-line)',
};
export const EDGE_DASH: Record<Strength, string | undefined> = { required: undefined, recommended: '6 4', optional: '1.5 4' };
export const EDGE_WIDTH: Record<Strength, number> = { required: 2, recommended: 2, optional: 2 };

export function LineSwatch({ type, light }: { type: Strength; light?: boolean }) {
  return (
    <svg width="16" height="8" viewBox="0 0 16 8" aria-hidden focusable="false">
      <line x1="1" y1="4" x2="15" y2="4" stroke={light ? '#fff' : EDGE_COLOR[type]} strokeWidth="2" strokeDasharray={EDGE_DASH[type]} strokeLinecap="round" />
    </svg>
  );
}
