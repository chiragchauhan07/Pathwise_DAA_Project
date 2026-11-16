import type { RoadmapModel } from '../../types/roadmap';

export function Summary({ roadmap }: { roadmap: RoadmapModel }) {
  const s = roadmap.stats;

  const items = [
    {
      label: 'Selected Courses',
      value: String(roadmap.courses.length),
      sub: `${roadmap.courses.length} from Knowledge Base`,
    },
    {
      label: 'Scheduled Semesters',
      value: roadmap.semesters.length ? String(roadmap.semesters.length) : '—',
      sub: roadmap.constraints?.maxCoursesPerSemester
        ? `Workload cap: ≤${roadmap.constraints.maxCoursesPerSemester}/term`
        : 'Unconstrained DAG waves',
    },
    {
      label: 'Prerequisite Edges',
      value: String(s.relationships),
      sub: s.relationships === 1 ? '1 curated dependency' : `${s.relationships} curated dependencies`,
    },
    {
      label: 'Topological Engine',
      value: "Kahn's Sort",
      sub: '3-State DFS Cycle Detection',
    },
  ];

  return (
    <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map((i) => (
        <div key={i.label} className="card px-4 py-3">
          <dt className="text-support text-xs font-medium">{i.label}</dt>
          <dd className="mt-0.5 text-xl font-semibold tracking-tight text-ink">{i.value}</dd>
          {i.sub && <dd className="text-support mt-0.5 text-xs">{i.sub}</dd>}
        </div>
      ))}
    </dl>
  );
}
