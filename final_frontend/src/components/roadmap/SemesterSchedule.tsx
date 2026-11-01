import { useMemo } from 'react';
import type { RoadmapModel } from '../../types/roadmap';

/** Renders the backend's semester groups exactly as returned. Nothing is recalculated here. */
export function SemesterSchedule({ roadmap }: { roadmap: RoadmapModel }) {
  const byId = useMemo(() => new Map(roadmap.courses.map((c) => [c.course_id, c])), [roadmap]);
  const names = useMemo(() => new Map(roadmap.courses.map((c) => [c.course_id, c.name])), [roadmap]);

  if (roadmap.semesters.length === 0)
    return <p className="card p-5 text-ink-2">The backend didn’t return a semester schedule for this path. The learning order is still valid.</p>;

  return (
    <ol className="grid gap-4 md:grid-cols-2">
      {roadmap.semesters.map((s) => (
        <li key={s.semester_number} className="card p-4 sm:p-5">
          <div className="flex items-baseline justify-between border-b border-divider pb-3">
            <h3 className="h-card">Semester {s.semester_number}</h3>
            <p className="text-support">{s.course_count} {s.course_count === 1 ? 'course' : 'courses'}</p>
          </div>
          <ul className="mt-3 space-y-3">
            {s.courses.map((c) => {
              const rc = byId.get(c.course_id);
              const needs = (rc?.prerequisites ?? []).filter((p) => p.type === 'required').map((p) => names.get(p.courseId) ?? p.courseId);
              return (
                <li key={c.course_id} className="flex gap-3">
                  <span className="mt-0.5 grid h-5 min-w-5 place-items-center rounded-full bg-subtle px-1 text-xs font-semibold text-ink-2">{rc?.order}</span>
                  <div className="min-w-0">
                    <p className="font-medium leading-snug">{c.name}</p>
                    {needs.length > 0 && <p className="text-support">Requires {needs.join(', ')}</p>}
                  </div>
                </li>
              );
            })}
          </ul>
        </li>
      ))}
    </ol>
  );
}
