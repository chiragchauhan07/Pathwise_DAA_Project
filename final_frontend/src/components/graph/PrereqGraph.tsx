import { useMemo } from 'react';
import type { RoadmapModel } from '../../types/roadmap';
import { layerCourses } from '../../utils/roadmapTransform';
import { asStrength, EDGE_COLOR, EDGE_DASH, EDGE_WIDTH, LineSwatch, STRENGTH_LABEL, type Strength } from '../common/relations';

const NODE_W = 220;
const NODE_H = 52;
const COL_GAP = 80;
const ROW_GAP = 18;
const PAD = 20;

export function GraphLegend() {
  const kinds: Strength[] = ['required', 'recommended', 'optional'];
  return (
    <ul className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-ink-2" aria-label="Legend">
      {kinds.map((k) => (
        <li key={k} className="flex items-center gap-2">
          <svg width="34" height="10" viewBox="0 0 34 10" aria-hidden>
            <line x1="1" y1="5" x2="26" y2="5" stroke={EDGE_COLOR[k]} strokeWidth={EDGE_WIDTH[k]} strokeDasharray={EDGE_DASH[k]} strokeLinecap="round" />
            <path d="M24 1.5L32 5 24 8.5z" fill={EDGE_COLOR[k]} />
          </svg>
          <span className="font-medium text-ink">{STRENGTH_LABEL[k]}</span>
        </li>
      ))}
      <li className="flex items-center gap-1.5 font-mono text-[11px] text-support">
        <span>Directed Edge (u → v): u is prerequisite of v</span>
      </li>
    </ul>
  );
}

function nodeLines(name: string, max = 22): string[] {
  if (name.length <= max) return [name];
  const words = name.split(' ');
  let a = '';
  let i = 0;
  while (i < words.length && (a + ' ' + words[i]).trim().length <= max) a = (a + ' ' + words[i++]).trim();
  let b = words.slice(i).join(' ');
  if (!a) { a = name.slice(0, max); b = name.slice(max); }
  return [a, b.length > max ? `${b.slice(0, max - 1)}…` : b];
}

/**
 * Layered prerequisite graph.
 * Columns represent longest-path topological layers in DAG G = (V, E).
 */
export function PrereqGraph({ roadmap, selectedId, onSelect }: { roadmap: RoadmapModel; selectedId: string | null; onSelect: (id: string | null) => void }) {
  const g = useMemo(() => {
    const ids = roadmap.courses.map((c) => c.course_id);
    const layer = layerCourses(ids, roadmap.edges);
    const cols = new Map<number, string[]>();
    for (const id of ids) { const l = layer[id] ?? 0; cols.set(l, [...(cols.get(l) ?? []), id]); }
    const colCount = Math.max(...cols.keys()) + 1;
    const maxRows = Math.max(...[...cols.values()].map((v) => v.length));
    const height = PAD * 2 + maxRows * NODE_H + (maxRows - 1) * ROW_GAP;
    const pos = new Map<string, { x: number; y: number }>();
    for (const [l, list] of cols) {
      const colH = list.length * NODE_H + (list.length - 1) * ROW_GAP;
      const y0 = PAD + (height - PAD * 2 - colH) / 2;
      list.forEach((id, i) => pos.set(id, { x: PAD + l * (NODE_W + COL_GAP), y: y0 + i * (NODE_H + ROW_GAP) }));
    }
    return { pos, width: PAD * 2 + colCount * NODE_W + (colCount - 1) * COL_GAP, height };
  }, [roadmap]);

  const names = useMemo(() => new Map(roadmap.courses.map((c) => [c.course_id, c.name])), [roadmap]);
  const near = useMemo(() => {
    const s = new Set<string>();
    if (selectedId) {
      s.add(selectedId);
      for (const e of roadmap.edges) {
        if (e.source_course_id === selectedId) s.add(e.target_course_id);
        if (e.target_course_id === selectedId) s.add(e.source_course_id);
      }
    }
    return s;
  }, [roadmap, selectedId]);

  return (
    <div className="overflow-x-auto rounded-xl border border-divider bg-surface-2" tabIndex={0} role="region" aria-label="Prerequisite diagram. Scrolls sideways. A text version is under List.">
      <svg width={g.width} height={g.height} viewBox={`0 0 ${g.width} ${g.height}`} role="group" aria-label={`Prerequisite diagram: ${roadmap.courses.length} courses, ${roadmap.edges.length} relationships`} onClick={() => onSelect(null)}>
        <defs>
          {(['required', 'recommended', 'optional'] as Strength[]).map((k) => (
            <marker key={k} id={`arr-${k}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5 0 10z" fill={EDGE_COLOR[k]} /></marker>
          ))}
          <marker id="arr-hot" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5 0 10z" fill="var(--color-accent)" /></marker>
        </defs>
        {roadmap.edges.map((e, i) => {
          const a = g.pos.get(e.source_course_id);
          const b = g.pos.get(e.target_course_id);
          const kind = asStrength(e.relationship_type) ?? 'optional';
          if (!a || !b) return null;
          const hot = selectedId !== null && (e.source_course_id === selectedId || e.target_course_id === selectedId);
          const dim = selectedId !== null && !hot;
          const x1 = a.x + NODE_W, y1 = a.y + NODE_H / 2, x2 = b.x - 2, y2 = b.y + NODE_H / 2;
          const dx = Math.max(36, (x2 - x1) / 2);
          return (
            <path
              key={`${e.source_course_id}-${e.target_course_id}-${i}`}
              d={`M${x1} ${y1} C${x1 + dx} ${y1} ${x2 - dx} ${y2} ${x2} ${y2}`}
              fill="none"
              stroke={hot ? 'var(--color-accent)' : EDGE_COLOR[kind]}
              strokeWidth={EDGE_WIDTH[kind] + (hot ? 0.5 : 0)}
              strokeDasharray={EDGE_DASH[kind]}
              strokeLinecap="round"
              opacity={dim ? 0.12 : 1}
              markerEnd={hot ? 'url(#arr-hot)' : `url(#arr-${kind})`}
            >
              <title>{`${names.get(e.source_course_id)} → ${names.get(e.target_course_id)}: ${STRENGTH_LABEL[kind]}`}</title>
            </path>
          );
        })}
        {roadmap.courses.map((c) => {
          const p = g.pos.get(c.course_id)!;
          const sel = c.course_id === selectedId;
          const dim = selectedId !== null && !near.has(c.course_id);
          return (
            <g
              key={c.course_id}
              transform={`translate(${p.x} ${p.y})`}
              role="button"
              tabIndex={0}
              aria-pressed={sel}
              aria-label={`${c.name}, sequence step ${c.order}`}
              opacity={dim ? 0.4 : 1}
              style={{ cursor: 'pointer' }}
              onClick={(ev) => { ev.stopPropagation(); onSelect(sel ? null : c.course_id); }}
              onKeyDown={(ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); onSelect(sel ? null : c.course_id); } }}
            >
              <title>{c.name}</title>
              <rect width={NODE_W} height={NODE_H} rx="10" fill="var(--color-surface)" stroke={sel ? 'var(--color-accent)' : 'var(--color-line)'} strokeWidth={sel ? 2 : 1} />
              <circle cx="22" cy={NODE_H / 2} r="11" fill="var(--color-subtle)" />
              <text x="22" y={NODE_H / 2} dy="0.35em" textAnchor="middle" fontSize="12" fontWeight="600" fill="var(--color-ink-2)">{c.order}</text>
              <text x="42" fontSize="13" fontWeight="500" fill="var(--color-ink)">
                {nodeLines(c.name).map((ln, i, arr) => <tspan key={i} x="42" y={NODE_H / 2 + (i - (arr.length - 1) / 2) * 15} dy="0.35em">{ln}</tspan>)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export { LineSwatch };
