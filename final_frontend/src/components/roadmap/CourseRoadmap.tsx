import { useState } from 'react';
import type { RoadmapCourse, RoadmapModel } from '../../types/roadmap';
import { capitalize } from '../../utils/formatters';
import { byStrength, isAi, RelationBadge, SourceBadge, type Strength } from '../common/relations';
import { RoadmapCanvas } from './RoadmapCanvas';

const ORDER: Strength[] = ['required', 'recommended', 'optional'];

function CourseCard({
  c,
  total,
  names,
  isSelected,
  onSelect,
}: {
  c: RoadmapCourse;
  total: number;
  names: Map<string, string>;
  isSelected?: boolean;
  onSelect?: () => void;
}) {
  const incoming = [...c.prerequisites].sort(byStrength);
  const withWhy = incoming.filter((r) => r.explanation);
  const meta = [c.difficulty && capitalize(String(c.difficulty)), c.category].filter(Boolean);

  return (
    <li className="relative pl-12">
      <span aria-hidden className="absolute left-[0.9375rem] top-9 -bottom-4 w-px bg-divider" />
      <span
        className={`absolute left-0 top-4 grid h-[1.875rem] w-[1.875rem] place-items-center rounded-full border text-sm font-semibold transition-colors ${
          isSelected
            ? 'border-accent bg-accent text-white'
            : 'border-line bg-surface text-ink'
        }`}
        aria-hidden
      >
        {c.order}
      </span>
      <article
        onClick={onSelect}
        className={`card cursor-pointer p-4 transition-all sm:p-5 ${
          isSelected ? 'border-accent ring-2 ring-accent/20' : 'hover:border-line'
        }`}
        aria-label={`Step ${c.order} of ${total}: ${c.name}`}
      >
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
          <div className="flex items-center gap-2">
            <h3 className="h-card">
              <span className="sr-only">Step {c.order}: </span>
              {c.name}
            </h3>
            {c.is_ai_inferred && <span className="badge badge-ai">AI Inferred</span>}
            {c.provenance === 'ai_disambiguated' && (
              <span className="badge badge-ai">Disambiguated</span>
            )}
          </div>
          {c.semester ? <span className="badge badge-neutral">Semester {c.semester}</span> : null}
        </div>
        {meta.length > 0 && <p className="text-support mt-1">{meta.join(' · ')}</p>}
        {c.description && <p className="mt-2 text-sm leading-relaxed text-ink-2">{c.description}</p>}

        <div className="mt-3 border-t border-divider pt-3 text-sm">
          {incoming.length === 0 ? (
            <p className="text-ink-2">No prerequisites among your selected courses.</p>
          ) : (
            <ul className="space-y-1.5">
              {ORDER.map((s) => {
                const rel = incoming.filter((r) => r.type === s);
                if (!rel.length) return null;
                return (
                  <li key={s} className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <RelationBadge type={s} />
                    {rel.map((r, i) => (
                      <span key={r.courseId} className="inline-flex items-center gap-1.5">
                        <span className="font-medium">{names.get(r.courseId) ?? r.courseId}</span>
                        {isAi(r) && <SourceBadge ai />}
                        {i < rel.length - 1 && <span className="text-muted">,</span>}
                      </span>
                    ))}
                  </li>
                );
              })}
            </ul>
          )}
          {withWhy.length > 0 && (
            <details className="mt-3">
              <summary className="cursor-pointer text-sm font-medium text-accent">Why these prerequisites?</summary>
              <ul className="mt-2 space-y-2.5">
                {withWhy.map((r) => (
                  <li key={r.courseId} className="rounded-lg bg-surface-2 p-3">
                    <p className="flex flex-wrap items-center gap-2 font-medium">
                      {names.get(r.courseId) ?? r.courseId} → {c.name} <SourceBadge ai={isAi(r)} />
                    </p>
                    <p className="mt-1 text-ink-2">{r.explanation}</p>
                    {(typeof r.confidence === 'number' || r.evidenceType) && (
                      <p className="text-support mt-1">
                        {[
                          typeof r.confidence === 'number' && `Confidence ${Math.round(r.confidence * 100)}%`,
                          r.evidenceType && r.evidenceType.replace(/_/g, ' '),
                        ]
                          .filter(Boolean)
                          .join(' · ')}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      </article>
    </li>
  );
}

export function CourseRoadmap({ roadmap }: { roadmap: RoadmapModel }) {
  const [viewMode, setViewMode] = useState<'road' | 'list'>('road');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const names = new Map(roadmap.courses.map((c) => [c.course_id, c.name]));

  return (
    <div className="space-y-4">
      {/* View Switcher Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Learning Journey</h3>
          <p className="text-support">Topologically ordered study route based on prerequisite dependencies.</p>
        </div>
        <div
          role="group"
          aria-label="Roadmap display format"
          className="inline-flex rounded-lg border border-line bg-subtle p-0.5"
        >
          <button
            type="button"
            aria-pressed={viewMode === 'road'}
            onClick={() => setViewMode('road')}
            className={`min-h-8 rounded-md px-3 text-sm font-medium transition-all ${
              viewMode === 'road' ? 'bg-surface shadow-[var(--shadow-card)] text-ink' : 'text-ink-2'
            }`}
          >
            Road Journey
          </button>
          <button
            type="button"
            aria-pressed={viewMode === 'list'}
            onClick={() => setViewMode('list')}
            className={`min-h-8 rounded-md px-3 text-sm font-medium transition-all ${
              viewMode === 'list' ? 'bg-surface shadow-[var(--shadow-card)] text-ink' : 'text-ink-2'
            }`}
          >
            Order List
          </button>
        </div>
      </div>

      {/* Render selected view */}
      {viewMode === 'road' ? (
        <RoadmapCanvas
          roadmap={roadmap}
          selectedId={selectedId}
          onSelectCourse={setSelectedId}
        />
      ) : (
        <ol className="space-y-4" aria-label="Recommended learning order list">
          {roadmap.courses.map((c) => (
            <CourseCard
              key={c.course_id}
              c={c}
              total={roadmap.courses.length}
              names={names}
              isSelected={c.course_id === selectedId}
              onSelect={() => setSelectedId(selectedId === c.course_id ? null : c.course_id)}
            />
          ))}
        </ol>
      )}
    </div>
  );
}
