import type { ApiError } from '../../services/api';
import { Button } from './Button';

type Tone = 'error' | 'warning' | 'info';
const TONE: Record<Tone, string> = {
  error: 'border-[#f2c4c8] bg-error-bg',
  warning: 'border-[#ecd9a4] bg-warning-bg',
  info: 'border-[#cfe1f7] bg-info-bg',
};
const ICON_COLOR: Record<Tone, string> = { error: 'var(--color-error)', warning: 'var(--color-warning)', info: 'var(--color-accent)' };

export function Alert({ tone, title, children, actions, role = 'alert' }: { tone: Tone; title: string; children?: React.ReactNode; actions?: React.ReactNode; role?: 'alert' | 'status' | 'note' }) {
  return (
    <div role={role} className={`flex gap-3 rounded-xl border p-4 ${TONE[tone]}`}>
      <svg width="18" height="18" viewBox="0 0 20 20" className="mt-0.5 shrink-0" aria-hidden>
        <circle cx="10" cy="10" r="9" fill="none" stroke={ICON_COLOR[tone]} strokeWidth="1.8" />
        <path d={tone === 'info' ? 'M10 9v5M10 6v.01' : 'M10 5.5v5.5M10 14v.01'} stroke={ICON_COLOR[tone]} strokeWidth="2" strokeLinecap="round" />
      </svg>
      <div className="min-w-0 flex-1">
        <p className="font-medium">{title}</p>
        {children && <div className="mt-1 text-sm leading-relaxed text-ink-2">{children}</div>}
        {actions && <div className="mt-3 flex flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  );
}

/** Pulls structured detail out of the backend's course-resolution message text. Unparseable text is shown as-is. */
export interface ResolutionIssue { query: string; kind: 'unknown' | 'ambiguous'; options: string[] }

export function parseResolution(message: string): { issues: ResolutionIssue[]; aiNote: string | null; rest: string } {
  const body = message.replace(/^Course resolution failed:\s*/i, '');
  const issues: ResolutionIssue[] = [];
  const leftovers: string[] = [];
  let aiNote: string | null = null;
  for (const part of body.split(/;\s+(?=Course)/)) {
    const amb = /Course query '(.+?)' is ambiguous and matches multiple courses:\s*(.+?)\.?$/s.exec(part);
    const unk = /Course '(.+?)' is not recognized in the knowledge base\.?(?:\s*Did you mean:\s*(.+?)\?)?/s.exec(part);
    if (amb) issues.push({ query: amb[1], kind: 'ambiguous', options: amb[2].split(/,\s*/).map((s) => s.trim()).filter(Boolean) });
    else if (unk) {
      issues.push({ query: unk[1], kind: 'unknown', options: (unk[2]?.match(/'([^']+)'/g) ?? []).map((s) => s.slice(1, -1)) });
      const tail = part.slice((unk.index ?? 0) + unk[0].length);
      if (/(Gemini|AI assistance|API key)/i.test(tail)) aiNote = tail.replace(/^[\s,.]*(and\s+)?/i, '').trim();
    } else if (/(Gemini|AI assistance|API key)/i.test(part)) aiNote = part.trim();
    else leftovers.push(part.trim());
  }
  const m = /(and )?AI assistance is currently unavailable[^.]*\.?/i.exec(body);
  if (m && !aiNote) aiNote = m[0].replace(/^and /i, '');
  return { issues, aiNote, rest: leftovers.join(' ') };
}

export function ErrorState({
  error, onReplace, onEdit, onRetryWithoutAi, onRetry, onDismiss,
}: {
  error: ApiError;
  onReplace?: (query: string, name: string) => void;
  onEdit?: () => void;
  onRetryWithoutAi?: () => void;
  onRetry?: () => void;
  onDismiss?: () => void;
}) {
  const dismiss = onDismiss && <Button small variant="quiet" onClick={onDismiss}>Dismiss</Button>;

  // 1. Structured Clarification Error from Backend AI Course Disambiguation
  if (error.kind === 'course_resolution' && error.needsClarification) {
    const q = error.query || 'course';
    const hasCandidates = error.candidates && error.candidates.length > 0;
    return (
      <div className="space-y-3">
        <Alert
          tone="warning"
          title={`Clarification required for “${q}”`}
          actions={
            <>
              {hasCandidates && error.candidates?.map((cand) => (
                <Button key={cand} small onClick={() => onReplace?.(q, cand)}>
                  Use {cand}
                </Button>
              ))}
              {onEdit && <Button small variant="quiet" onClick={onEdit}>Edit my courses</Button>}
              {dismiss}
            </>
          }
        >
          <p className="leading-relaxed text-ink">{error.clarification || error.message}</p>
          {hasCandidates ? (
            <p className="mt-2 text-xs text-ink-2">
              Choose one of the recommended candidate subjects above to automatically update your list.
            </p>
          ) : (
            <p className="mt-2 text-xs text-ink-2">
              Tip: Provide a more specific academic title (such as English Composition, Technical Writing, or Linguistics), or provide a specific Learning Goal in the form so Gemini can infer the appropriate context.
            </p>
          )}
        </Alert>
      </div>
    );
  }

  // 2. Regular Course Resolution Error
  if (error.kind === 'course_resolution') {
    const { issues, aiNote, rest } = parseResolution(error.message);
    return (
      <div className="space-y-3">
        {issues.length > 0 ? issues.map((i) => (
          <Alert key={i.query} tone="warning" title={i.kind === 'ambiguous' ? `“${i.query}” matches more than one course` : `“${i.query}” isn’t in the knowledge base`}
            actions={<>
              {i.options.map((o) => <Button key={o} small onClick={() => onReplace?.(i.query, o)}>Use {o}</Button>)}
              {onEdit && <Button small variant="quiet" onClick={onEdit}>Edit my courses</Button>}
            </>}>
            {i.kind === 'ambiguous' ? 'Choose the course you meant.' : i.options.length ? 'Did you mean one of these?' : 'Check the spelling, or pick from the suggestions in the course field.'}
          </Alert>
        )) : (
          <Alert tone="warning" title="Some courses couldn’t be matched" actions={onEdit && <Button small variant="quiet" onClick={onEdit}>Edit my courses</Button>}>{rest || error.message}</Alert>
        )}
        {aiNote && <Alert tone="info" role="status" title="AI assistance is unavailable">{aiNote} This is a separate service issue; it doesn’t change whether your course names are valid.</Alert>}
        {dismiss}
      </div>
    );
  }

  if (error.kind === 'ai_service')
    return <Alert tone="warning" title="AI suggestions are unavailable" actions={<>{onRetryWithoutAi && <Button small onClick={onRetryWithoutAi}>Generate without AI</Button>}{dismiss}</>}>{error.message} Your course list is unchanged, and curated prerequisites alone still produce a valid path.</Alert>;

  if (error.kind === 'network' || error.kind === 'server' || error.kind === 'invalid_response')
    return <Alert tone="error" title={error.kind === 'network' ? 'Can’t reach the backend' : 'The backend returned a problem'} actions={<>{onRetry && <Button small onClick={onRetry}>Try again</Button>}{dismiss}</>}>{error.message}{error.kind === 'network' && ' Check that the FastAPI server is running, then try again.'}</Alert>;

  if (error.kind === 'timeout')
    return <Alert tone="warning" title="The request timed out" actions={<>{onRetry && <Button small onClick={onRetry}>Try again</Button>}{onRetryWithoutAi && <Button small onClick={onRetryWithoutAi}>Generate without AI</Button>}{dismiss}</>}>{error.message}</Alert>;

  if (error.kind === 'cycle')
    return (
      <Alert tone="error" title="These prerequisites form a loop" actions={<>{onEdit && <Button small onClick={onEdit}>Edit my courses</Button>}{dismiss}</>}>
        <p>{error.message}</p>
        {error.cyclePath && error.cyclePath.length > 0 && <p className="mt-2 font-medium text-ink">{error.cyclePath.map((id) => id.replace(/_/g, ' ')).join(' → ')}</p>}
        <p className="mt-2">Remove one of these courses, or turn AI suggestions off if one of its links created the loop.</p>
      </Alert>
    );

  if (error.kind === 'curricular_constraint')
    return (
      <Alert tone="warning" title="Your scheduling limits don’t fit" actions={<>{onEdit && <Button small onClick={onEdit}>Adjust limits</Button>}{dismiss}</>}>
        <p>{error.message}</p>
        {error.requiredSemesters != null && <p className="mt-2">Needs at least {error.requiredSemesters} semesters{error.maxSemesters != null ? `; your limit is ${error.maxSemesters}` : ''}.</p>}
      </Alert>
    );

  return <Alert tone="error" title={error.kind === 'validation' ? 'Check your entries' : 'The request couldn’t be completed'} actions={<>{onEdit && <Button small onClick={onEdit}>Edit</Button>}{dismiss}</>}>{error.message}</Alert>;
}
