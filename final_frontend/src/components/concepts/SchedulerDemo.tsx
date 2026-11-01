import { useState } from 'react';

interface SemesterGroupDemo {
  semesterNumber: number;
  courses: string[];
}

const UNCONSTRAINED_WAVES: SemesterGroupDemo[] = [
  { semesterNumber: 1, courses: ['Programming Fundamentals', 'Discrete Mathematics'] },
  { semesterNumber: 2, courses: ['Data Structures'] },
  { semesterNumber: 3, courses: ['Design & Analysis of Algorithms', 'Operating Systems'] },
];

const CONSTRAINED_SCHEDULE: SemesterGroupDemo[] = [
  { semesterNumber: 1, courses: ['Programming Fundamentals', 'Discrete Mathematics'] },
  { semesterNumber: 2, courses: ['Data Structures'] },
  { semesterNumber: 3, courses: ['Design & Analysis of Algorithms'] },
  { semesterNumber: 4, courses: ['Operating Systems'] },
];

export function SchedulerDemo() {
  const [mode, setMode] = useState<'unconstrained' | 'constrained'>('unconstrained');

  const groups = mode === 'unconstrained' ? UNCONSTRAINED_WAVES : CONSTRAINED_SCHEDULE;

  return (
    <div className="card space-y-4 p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-divider pb-4">
        <div>
          <h3 className="h-card">Pedagogical Semester Scheduling</h3>
          <p className="text-support mt-0.5">
            Partitions courses into semesters using DAG longest-path wave layering (unconstrained) or multi-priority list scheduling (constrained cap \(K\)).
          </p>
        </div>
        <div role="group" aria-label="Scheduling algorithm mode" className="inline-flex rounded-lg border border-line bg-subtle p-0.5">
          <button
            type="button"
            aria-pressed={mode === 'unconstrained'}
            onClick={() => setMode('unconstrained')}
            className={`min-h-8 rounded-md px-3 text-sm font-medium transition-all ${
              mode === 'unconstrained' ? 'bg-surface shadow-[var(--shadow-card)] text-ink' : 'text-ink-2'
            }`}
          >
            Wave Layering (Unconstrained)
          </button>
          <button
            type="button"
            aria-pressed={mode === 'constrained'}
            onClick={() => setMode('constrained')}
            className={`min-h-8 rounded-md px-3 text-sm font-medium transition-all ${
              mode === 'constrained' ? 'bg-surface shadow-[var(--shadow-card)] text-ink' : 'text-ink-2'
            }`}
          >
            List Scheduling (Max 1-2 per Term)
          </button>
        </div>
      </div>

      <div className="space-y-3">
        <p className="text-sm leading-relaxed text-ink-2">
          {mode === 'unconstrained' ? (
            <>
              <b>Wave Layering Algorithm:</b> Courses with in-degree 0 are placed in Semester 1. A dependent course is assigned to term max(term[u] for each prerequisite u) + 1. This computes the minimum possible academic semesters.
            </>
          ) : (
            <>
              <b>Multi-Priority List Scheduling:</b> When a student configures a workload limit (e.g. max 1 course per semester in upper years), candidates ready to schedule are ranked by:
              1) <i>Critical path depth</i> (longest remaining prerequisite chain), 2) <i>Soft prerequisite satisfaction</i>, 3) <i>Course difficulty</i>, 4) <i>ID tie-breaking</i>.
            </>
          )}
        </p>

        {/* Visual Semester Buckets */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {groups.map((group) => (
            <div key={group.semesterNumber} className="rounded-xl border border-divider bg-surface-2 p-3.5">
              <div className="flex items-center justify-between border-b border-divider pb-2 text-xs font-semibold uppercase tracking-wider text-muted">
                <span>Semester {group.semesterNumber}</span>
                <span className="badge badge-neutral">{group.courses.length} course{group.courses.length === 1 ? '' : 's'}</span>
              </div>
              <ul className="mt-2.5 space-y-1.5">
                {group.courses.map((courseName) => (
                  <li key={courseName} className="rounded-lg bg-surface p-2 text-xs font-medium text-ink shadow-[var(--shadow-card)]">
                    {courseName}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
