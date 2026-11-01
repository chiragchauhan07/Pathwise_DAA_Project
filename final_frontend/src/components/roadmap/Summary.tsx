import type { RoadmapModel } from '../../types/roadmap';

export function Summary({ roadmap }: { roadmap: RoadmapModel }) {
  const s = roadmap.stats;
  const aiSum = roadmap.aiSummary;

  let aiProposalsValue = roadmap.aiProposalsUsed ? 'Used' : 'Not used';
  let aiSub: string | undefined;

  if (aiSum) {
    if (aiSum.proposal_request_status === 'disabled') {
      aiProposalsValue = 'Disabled';
      aiSub = 'Curated links only';
    } else if (aiSum.proposal_request_status === 'skipped') {
      aiProposalsValue = 'Skipped';
      aiSub = '1 course selected';
    } else if (aiSum.proposal_request_status === 'failed') {
      aiProposalsValue = 'Unavailable';
      aiSub = 'Fallback to curated';
    } else if (aiSum.proposal_request_status === 'succeeded') {
      if (aiSum.relationships_added > 0) {
        aiProposalsValue = `${aiSum.relationships_added} accepted`;
        aiSub = `${aiSum.proposals_received} proposed by AI`;
      } else {
        aiProposalsValue = '0 added';
        aiSub = 'Curated graph complete';
      }
    }
  }

  const items = [
    { label: 'Courses', value: String(roadmap.courses.length), sub: `${roadmap.courses.filter(c => c.is_curated !== false).length} curated` },
    { label: 'Semesters', value: roadmap.semesters.length ? String(roadmap.semesters.length) : '—', sub: roadmap.constraints?.maxCoursesPerSemester ? `Max ${roadmap.constraints.maxCoursesPerSemester}/term` : undefined },
    { label: 'Prerequisites', value: String(s.relationships), sub: s.relationships ? `${s.curatedCount} curated · ${s.aiCount} AI` : 'None required' },
    { label: 'AI Assistance', value: aiProposalsValue, sub: aiSub },
  ];

  return (
    <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map((i) => (
        <div key={i.label} className="card px-4 py-3">
          <dt className="text-support">{i.label}</dt>
          <dd className="mt-0.5 text-xl font-semibold tracking-tight">{i.value}</dd>
          {i.sub && <dd className="text-support mt-0.5">{i.sub}</dd>}
        </div>
      ))}
    </dl>
  );
}
