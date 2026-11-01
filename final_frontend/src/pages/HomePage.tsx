import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Alert, ErrorState } from '../components/common/ErrorState';
import { PageContainer } from '../components/layout/PageContainer';
import { CourseForm, type CourseFormHandle } from '../components/roadmap/CourseForm';
import { RoadmapResults } from '../components/roadmap/RoadmapResults';
import { SavedPaths } from '../components/roadmap/SavedPaths';
import { useRoadmap } from '../hooks/useRoadmap';

export default function HomePage() {
  const { status, roadmap, lastRequest, error, draft, setDraft, generate, clearError } = useRoadmap();
  const formRef = useRef<CourseFormHandle>(null);
  const outRef = useRef<HTMLDivElement>(null);
  const prev = useRef(status);
  const busy = status === 'loading';

  // On narrow screens the results sit below the form: bring them into view when a request finishes.
  useEffect(() => {
    if (prev.current === 'loading' && (status === 'success' || status === 'error') && window.matchMedia('(max-width: 1279px)').matches)
      outRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    prev.current = status;
  }, [status]);

  const edit = () => { clearError(); formRef.current?.focusInput(); };
  const replace = (query: string, name: string) => {
    const q = query.trim().toLowerCase();
    setDraft((d) => {
      const has = d.courses.some((c) => c.toLowerCase() === name.toLowerCase());
      const next = d.courses.flatMap((c) => (c.toLowerCase() === q ? (has ? [] : [name]) : [c]));
      return { ...d, courses: next };
    });
    clearError();
  };

  return (
    <PageContainer className="pt-10">
      <header className="max-w-2xl">
        <h1 className="h-page">Plan your learning path</h1>
        <p className="mt-3 text-base text-ink-2">Choose the courses you want to take. Pathwise orders them by prerequisites and groups them into semesters.</p>
      </header>

      <div className="mt-8 grid items-start gap-8 xl:grid-cols-[25rem_minmax(0,1fr)]">
        <div className="space-y-2 xl:sticky xl:top-6">
          <CourseForm busy={busy} onSubmit={generate} handleRef={formRef} />
          <div className="flex justify-end"><SavedPaths disabled={busy} /></div>
        </div>

        <div ref={outRef} className="min-w-0 scroll-mt-4" aria-live="polite">
          {status === 'error' && error && (
            <div className="mb-6">
              <ErrorState
                error={error}
                onReplace={replace}
                onEdit={edit}
                onRetry={lastRequest ? () => generate(lastRequest) : undefined}
                onRetryWithoutAi={lastRequest?.use_ai ? () => generate({ ...lastRequest, use_ai: false }) : undefined}
                onDismiss={clearError}
              />
            </div>
          )}
          {busy && <Alert tone="info" role="status" title="Generating your learning path">Resolving courses, checking prerequisites and scheduling semesters.</Alert>}
          {roadmap && <div className={busy ? 'opacity-50' : ''}><RoadmapResults roadmap={roadmap} /></div>}
          {!roadmap && !busy && status !== 'error' && (
            <div className="card px-6 py-14 text-center">
              <h2 className="h-card">Your learning path will appear here</h2>
              <p className="mx-auto mt-2 max-w-sm text-sm text-ink-2">Add at least one course, optionally describe your goal, then generate. {draft.courses.length > 0 ? 'You’re ready to go.' : 'You can start from one of the tracks.'}</p>
            </div>
          )}
          {roadmap && !busy && (
            <p className="mt-8 text-sm text-ink-2">See <Link className="font-medium text-accent hover:underline" to="/daa">how the order is computed</Link> or <Link className="font-medium text-accent hover:underline" to="/ai">what AI contributed</Link>.</p>
          )}
        </div>
      </div>
    </PageContainer>
  );
}
