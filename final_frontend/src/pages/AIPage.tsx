import { useState } from 'react';
import { Link } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { RelationBadge, SourceBadge } from '../components/common/relations';
import { Button } from '../components/common/Button';
import { Spinner } from '../components/common/Spinner';
import { useRoadmap } from '../hooks/useRoadmap';
import { checkAiStatus, type BackendAiStatus } from '../services/roadmapService';
import { friendlyWarning } from '../utils/warnings';

const PIPELINE_STAGES = [
  {
    step: 1,
    title: 'Course Input & Normalization',
    role: 'Input Sanitization',
    isAi: false,
    text: 'User submits raw course queries, career learning goal, and optional semester capacity limits.',
  },
  {
    step: 2,
    title: 'Curated Knowledge Base Resolution',
    role: 'Catalog Lookup',
    isAi: false,
    text: 'Resolves exact course IDs, known aliases, and safe typos against 35 expert-curated computer science courses.',
  },
  {
    step: 3,
    title: 'Context-Aware AI Disambiguation',
    role: 'Google Gemini (AI)',
    isAi: true,
    text: 'When queries are unrecognized or ambiguous (e.g. “English”), Gemini evaluates them using the student’s learning goal and other courses to find canonical equivalents.',
  },
  {
    step: 4,
    title: 'Prerequisite Relationship Proposals',
    role: 'Google Gemini (AI)',
    isAi: true,
    text: 'Analyzes the full set of resolved courses to propose missing academic dependencies not already in the curated catalog.',
  },
  {
    step: 5,
    title: 'Strict Validation Barrier',
    role: 'Deterministic Validator',
    isAi: false,
    text: 'Validates proposals: rejects unknown course IDs, self-loops, duplicate edges, and invalid relationship types. Curated file is never mutated.',
  },
  {
    step: 6,
    title: 'Graph Cycle Detection & Topological Sort',
    role: 'DAA Engine',
    isAi: false,
    text: 'DirectedGraph combines edges in-memory; 3-state DFS checks for cycles; Kahn’s min-heap computes deterministic topological order.',
  },
  {
    step: 7,
    title: 'Pedagogical Semester Scheduling',
    role: 'DAA Scheduler',
    isAi: false,
    text: 'Partitions courses into semesters using DAG wave layering (unconstrained) or multi-priority list scheduling under capacity limits.',
  },
  {
    step: 8,
    title: 'Roadmap & Visualizer Rendering',
    role: 'Frontend Presentation',
    isAi: false,
    text: 'Renders the winding road journey, interactive graph, and workload distribution with complete provenance labelling.',
  },
];

export default function AIPage() {
  const { roadmap } = useRoadmap();
  const [diagLoading, setDiagLoading] = useState(false);
  const [diagResult, setDiagResult] = useState<BackendAiStatus | null>(null);
  const [diagError, setDiagError] = useState<string | null>(null);

  const aiSummary = roadmap?.aiSummary;
  const proposed = roadmap?.edges.filter((e) => e.is_ai_proposed || e.source === 'ai_proposed') ?? [];
  const names = new Map(roadmap?.courses.map((c) => [c.course_id, c.name]) ?? []);

  const runDiagnostic = async () => {
    setDiagLoading(true);
    setDiagError(null);
    try {
      const res = await checkAiStatus();
      setDiagResult(res);
    } catch (err) {
      setDiagError((err as Error).message || 'Failed to query /api/v1/ai/status');
    } finally {
      setDiagLoading(false);
    }
  };

  // Determine user-friendly badge status for latest run
  const getAiStatusBadge = () => {
    if (!roadmap) return { label: 'No Path Generated', color: 'badge-neutral' };
    if (!aiSummary?.requested) return { label: 'AI Disabled by User', color: 'badge-neutral' };
    if (aiSummary.proposal_request_status === 'skipped') return { label: 'AI Skipped (Single Course)', color: 'badge-neutral' };
    if (aiSummary.proposal_request_status === 'failed') return { label: 'AI Unavailable (Fallback Engaged)', color: 'border-error text-error bg-error-bg' };
    if (aiSummary.proposal_request_status === 'succeeded') {
      if (aiSummary.relationships_added > 0) return { label: `${aiSummary.relationships_added} AI Proposal(s) Accepted`, color: 'badge-ai' };
      if (aiSummary.proposals_rejected > 0 && aiSummary.proposals_accepted === 0) return { label: 'Proposals Rejected (Validation)', color: 'badge-warning' };
      return { label: 'AI Completed (0 Extra Required)', color: 'badge-neutral' };
    }
    return { label: roadmap.aiProposalsUsed ? 'AI Proposals Used' : 'Curated Links Only', color: 'badge-neutral' };
  };

  const statusBadge = getAiStatusBadge();

  return (
    <PageContainer className="pt-10">
      <header className="max-w-2xl">
        <h1 className="h-page">AI Pipeline & Governance</h1>
        <p className="mt-3 text-base text-ink-2">
          Pathwise uses Google Gemini strictly as an academic advisory model. Graph ordering, cycle detection, and scheduling are 100% computed by deterministic DAA algorithms.
        </p>
        {roadmap && (
          <p className="mt-3 text-sm">
            <Link to="/" className="font-medium text-accent hover:underline">
              Return to your latest learning path
            </Link>
          </p>
        )}
      </header>

      {/* Actual AI Execution Metadata for Latest Path */}
      <section aria-labelledby="latest-ai" className="mt-12">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="latest-ai" className="h-section">Execution Status: Latest Path</h2>
            <p className="text-support mt-0.5">Real execution metrics returned in the backend response metadata.</p>
          </div>
          <span className={`badge ${statusBadge.color}`}>{statusBadge.label}</span>
        </div>

        {!roadmap ? (
          <p className="card mt-4 p-5 text-ink-2">
            Generate a learning path in the <Link to="/" className="font-medium text-accent hover:underline">planner</Link> to inspect real-time AI execution metrics, proposal counts, and resolution provenance.
          </p>
        ) : (
          <div className="mt-5 space-y-4">
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <div className="card p-3.5">
                <dt className="text-support text-xs">AI Requested</dt>
                <dd className="mt-1 text-lg font-semibold">{aiSummary ? (aiSummary.requested ? 'Yes' : 'No') : (roadmap.aiProposalsUsed ? 'Yes' : 'No')}</dd>
              </div>
              <div className="card p-3.5">
                <dt className="text-support text-xs">Course Resolution</dt>
                <dd className="mt-1 text-sm font-semibold capitalize">{aiSummary?.course_resolution_status.replace(/_/g, ' ') || 'Curated'}</dd>
              </div>
              <div className="card p-3.5">
                <dt className="text-support text-xs">Evaluated via AI</dt>
                <dd className="mt-1 text-lg font-semibold">
                  {aiSummary ? aiSummary.unknown_courses_evaluated + aiSummary.ambiguous_courses_evaluated : '0'}
                </dd>
              </div>
              <div className="card p-3.5">
                <dt className="text-support text-xs">Proposals Received</dt>
                <dd className="mt-1 text-lg font-semibold">{aiSummary?.proposals_received ?? proposed.length}</dd>
              </div>
              <div className="card p-3.5">
                <dt className="text-support text-xs">Proposals Accepted</dt>
                <dd className="mt-1 text-lg font-semibold text-accent">{aiSummary?.proposals_accepted ?? proposed.length}</dd>
              </div>
              <div className="card p-3.5">
                <dt className="text-support text-xs">Configured Model</dt>
                <dd className="mt-1 font-mono text-xs font-semibold">{aiSummary?.model || 'gemini-3.5-flash-lite'}</dd>
              </div>
            </dl>

            {aiSummary?.message && (
              <div className="rounded-xl border border-divider bg-surface-2 p-4 text-sm">
                <p className="font-semibold text-ink">AI Pipeline Diagnostic Message:</p>
                <p className="mt-1 text-ink-2">{aiSummary.message}</p>
              </div>
            )}

            {roadmap.warnings.length > 0 && (
              <ul className="list-disc space-y-1 pl-5 text-sm text-ink-2">
                {roadmap.warnings.map((w, i) => (
                  <li key={i}>{friendlyWarning(w)}</li>
                ))}
              </ul>
            )}

            {/* Proposed Edges List */}
            {proposed.length > 0 && (
              <div className="space-y-3 pt-2">
                <h3 className="h-card">Incorporated AI Proposals</h3>
                <ul className="grid gap-3 md:grid-cols-2">
                  {proposed.map((e, i) => (
                    <li key={i} className="card p-4">
                      <p className="flex flex-wrap items-center gap-2 font-medium">
                        {names.get(e.source_course_id) ?? e.source_course_id} → {names.get(e.target_course_id) ?? e.target_course_id}
                        <RelationBadge type={e.relationship_type} />
                        <SourceBadge ai />
                      </p>
                      {e.explanation && <p className="mt-2 text-sm leading-relaxed text-ink-2">{e.explanation}</p>}
                      {(typeof e.confidence === 'number' || e.evidence_type) && (
                        <p className="text-support mt-2">
                          {[
                            typeof e.confidence === 'number' && `Confidence ${Math.round(e.confidence * 100)}%`,
                            e.evidence_type && e.evidence_type.replace(/_/g, ' '),
                          ]
                            .filter(Boolean)
                            .join(' · ')}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      {/* 8-Stage Architecture Pipeline */}
      <section aria-labelledby="pipeline" className="mt-14">
        <h2 id="pipeline" className="h-section">8-Stage Processing Pipeline</h2>
        <p className="text-support mt-1">Strict governance enforces that LLM output is always bounded and validated by deterministic algorithms.</p>
        <ol className="mt-6 grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          {PIPELINE_STAGES.map((s) => (
            <li
              key={s.step}
              className={`card flex flex-col justify-between p-4 ${
                s.isAi ? 'border-accent/40 bg-info-bg shadow-[var(--shadow-card)]' : ''
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-muted">STAGE 0{s.step}</span>
                  <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${s.isAi ? 'bg-accent text-white' : 'bg-subtle text-ink-2'}`}>
                    {s.role}
                  </span>
                </div>
                <h3 className="h-card mt-3 text-ink">{s.title}</h3>
                <p className="mt-2 text-xs leading-relaxed text-ink-2">{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Backend Diagnostic Testing Endpoint (/api/v1/ai/status) */}
      <section aria-labelledby="diag" className="mt-14">
        <h2 id="diag" className="h-section">Backend AI Configuration Diagnostic</h2>
        <p className="text-support mt-1">
          Queries <code>GET /api/v1/ai/status</code> to verify credentials, model selection, and client initialization without leaking secrets or consuming completion quota.
        </p>

        <div className="card mt-4 space-y-4 p-5">
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={runDiagnostic} disabled={diagLoading}>
              {diagLoading ? <><Spinner /> Checking…</> : 'Query Backend AI Status'}
            </Button>
            <span className="text-xs text-muted">
              Note: This inspects backend initialization status. It does not perform an unnecessary completion request.
            </span>
          </div>

          {diagError && (
            <p className="text-sm font-medium text-error">Diagnostic Error: {diagError}</p>
          )}

          {diagResult && (
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4 border-t border-divider pt-3 text-xs">
              <div>
                <dt className="text-support">Configured</dt>
                <dd className="mt-0.5 font-semibold text-ink">{diagResult.configured ? 'Yes (Valid Key)' : 'No'}</dd>
              </div>
              <div>
                <dt className="text-support">Key Source</dt>
                <dd className="mt-0.5 font-semibold text-ink">{diagResult.key_source}</dd>
              </div>
              <div>
                <dt className="text-support">Active Model</dt>
                <dd className="mt-0.5 font-mono font-semibold text-accent">{diagResult.model}</dd>
              </div>
              <div>
                <dt className="text-support">Client Initializable</dt>
                <dd className="mt-0.5 font-semibold text-ink">{diagResult.client_initializable ? 'Yes (google-genai)' : 'No'}</dd>
              </div>
            </dl>
          )}
        </div>
      </section>
    </PageContainer>
  );
}
