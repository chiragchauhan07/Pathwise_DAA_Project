import { useId, useImperativeHandle, useMemo, useRef, useState, type FormEvent, type KeyboardEvent, type Ref } from 'react';
import { CURATED_COURSES, TRACK_PRESETS, type TrackPreset } from '../../data/coursesCatalog';
import { useRoadmap } from '../../hooks/useRoadmap';
import type { LearningPathRequest } from '../../types/roadmap';
import { splitCourseInput } from '../../utils/formatters';
import { Button } from '../common/Button';
import { Spinner } from '../common/Spinner';

const MAX_COURSES = 50;
export interface CourseFormHandle { focusInput: () => void; openOptions: () => void }

const norm = (s: string) => s.trim().toLowerCase();
const isKnown = (name: string) => {
  const q = norm(name);
  return CURATED_COURSES.some((c) => norm(c.name) === q || c.id === q || c.aliases.some((a) => norm(a) === q));
};

function distance(a: string, b: string): number {
  const dp = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)] as number[]);
  for (let j = 1; j <= b.length; j++) dp[0][j] = j;
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++)
      dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return dp[a.length][b.length];
}

/** Closest catalogue names for a name that isn't in the catalogue (spelling help only). */
function nearest(name: string): string[] {
  const q = norm(name);
  return CURATED_COURSES.map((c) => {
    const names = [c.name, ...c.aliases].map(norm);
    const d = Math.min(...names.map((n) => (n.includes(q) || q.includes(n) ? 0 : distance(q, n))));
    return { name: c.name, d };
  })
    .filter((x) => x.d <= Math.max(2, Math.floor(q.length * 0.35)))
    .sort((a, b) => a.d - b.d)
    .slice(0, 3)
    .map((x) => x.name);
}

function parseLimit(raw: string, label: string): { value: number | null; error?: string } {
  const t = raw.trim();
  if (!t) return { value: null };
  if (!/^\d+$/.test(t) || Number(t) < 1) return { value: null, error: `${label} must be a whole number of 1 or more.` };
  return { value: Number(t) };
}

export function CourseForm({ busy, onSubmit, handleRef }: { busy: boolean; onSubmit: (req: LearningPathRequest) => void; handleRef?: Ref<CourseFormHandle> }) {
  const { draft, setDraft } = useRoadmap();
  const { courses, goal, useAi, fallback, maxPerSemester, maxSemesters, optionsOpen } = draft;
  const id = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState('');
  const [note, setNote] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [tried, setTried] = useState(false);

  const patch = (p: Partial<typeof draft>) => setDraft((d) => ({ ...d, ...p }));
  useImperativeHandle(handleRef, () => ({ focusInput: () => inputRef.current?.focus(), openOptions: () => patch({ optionsOpen: true }) }));

  const suggestions = useMemo(() => {
    const q = norm(text);
    if (!q) return [];
    return CURATED_COURSES.filter(
      (c) => !courses.some((s) => norm(s) === norm(c.name)) && (norm(c.name).includes(q) || c.aliases.some((a) => norm(a).includes(q))),
    ).slice(0, 6);
  }, [text, courses]);

  const unknown = useMemo(() => courses.filter((c) => !isKnown(c)), [courses]);

  const add = (names: string[]) => {
    const next = [...courses];
    let msg: string | null = null;
    for (const raw of names) {
      const n = raw.trim();
      if (!n) continue;
      if (n.length > 100) { msg = 'Course names can be up to 100 characters.'; continue; }
      if (next.some((c) => norm(c) === norm(n))) { msg = `“${n}” is already in your list.`; continue; }
      if (next.length >= MAX_COURSES) { msg = `You can add up to ${MAX_COURSES} courses.`; break; }
      next.push(n);
    }
    patch({ courses: next });
    setNote(msg);
  };
  const commit = () => { const names = splitCourseInput(text); setText(''); setOpen(false); if (names.length) add(names); };
  const pick = (name: string) => { add([name]); setText(''); setOpen(false); setActive(0); inputRef.current?.focus(); };
  const replace = (from: string, to: string) => {
    if (courses.some((c) => norm(c) === norm(to))) patch({ courses: courses.filter((c) => c !== from) });
    else patch({ courses: courses.map((c) => (c === from ? to : c)) });
  };
  const edit = (name: string) => { patch({ courses: courses.filter((c) => c !== name) }); setText(name); inputRef.current?.focus(); };

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' && suggestions.length) { e.preventDefault(); setOpen(true); setActive((a) => (a + 1) % suggestions.length); }
    else if (e.key === 'ArrowUp' && suggestions.length) { e.preventDefault(); setActive((a) => (a - 1 + suggestions.length) % suggestions.length); }
    else if (e.key === 'Escape') setOpen(false);
    else if (e.key === 'Enter') { e.preventDefault(); if (open && suggestions[active]) pick(suggestions[active].name); else commit(); }
    else if (e.key === ',') { e.preventDefault(); commit(); }
    else if (e.key === 'Backspace' && !text && courses.length) patch({ courses: courses.slice(0, -1) });
  };

  const perSem = parseLimit(maxPerSemester, 'Courses per semester');
  const sems = parseLimit(maxSemesters, 'Semesters');

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setTried(true);
    const pending = splitCourseInput(text);
    const list = pending.length ? [...courses, ...pending.filter((p) => !courses.some((c) => norm(c) === norm(p)))] : courses;
    if (pending.length) { patch({ courses: list }); setText(''); }
    if (list.length === 0) { inputRef.current?.focus(); return; }
    if (perSem.error || sems.error) { patch({ optionsOpen: true }); return; }
    setNote(null);
    onSubmit({
      courses: list,
      learning_goal: goal.trim() || undefined,
      use_ai: useAi,
      fallback_on_ai_failure: fallback,
      max_courses_per_semester: perSem.value,
      max_semesters: sems.value,
    });
  };

  const showEmptyError = tried && courses.length === 0 && !text.trim();
  const listId = `${id}-list`;

  return (
    <form onSubmit={submit} noValidate aria-label="Learning path settings" className="card space-y-6 p-5 sm:p-6">
      <div>
        <label htmlFor={`${id}-course`} className="text-sm font-medium">Courses</label>
        <div className="relative mt-2">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              id={`${id}-course`}
              role="combobox"
              aria-expanded={open && suggestions.length > 0}
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={open && suggestions[active] ? `${id}-opt-${active}` : undefined}
              aria-describedby={`${id}-help`}
              aria-invalid={showEmptyError}
              className="field"
              value={text}
              disabled={busy}
              autoComplete="off"
              placeholder="Search or type a course name"
              onChange={(e) => { setText(e.target.value); setOpen(true); setActive(0); }}
              onFocus={() => setOpen(true)}
              onBlur={() => setOpen(false)}
              onKeyDown={onKey}
            />
            <Button onClick={commit} disabled={!text.trim() || busy} aria-label="Add course">Add</Button>
          </div>
          {open && suggestions.length > 0 && (
            <ul id={listId} role="listbox" aria-label="Matching courses" className="absolute left-0 right-0 z-20 mt-1 overflow-hidden rounded-xl border border-line bg-surface py-1 shadow-[var(--shadow-pop)]">
              {suggestions.map((s, i) => (
                <li key={s.id} id={`${id}-opt-${i}`} role="option" aria-selected={i === active}
                  onMouseDown={(e) => { e.preventDefault(); pick(s.name); }} onMouseEnter={() => setActive(i)}
                  className={`flex cursor-pointer items-baseline justify-between gap-3 px-3 py-2 ${i === active ? 'bg-info-bg' : ''}`}>
                  <span className="font-medium">{s.name}</span>
                  <span className="text-support shrink-0">{s.category}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <p id={`${id}-help`} className="mt-2 text-support" aria-live="polite">
          {showEmptyError ? <span className="font-medium text-error">Add at least one course.</span> : note ?? 'Press Enter to add. Separate several names with commas.'}
        </p>

        {courses.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2" aria-label="Selected courses">
            {courses.map((c) => {
              const ok = isKnown(c);
              return (
                <li key={norm(c)} className={`chip ${ok ? '' : 'chip-warn'}`}>
                  {!ok && (
                    <svg width="14" height="14" viewBox="0 0 20 20" className="mr-1.5 shrink-0" aria-hidden><path d="M10 3l8 14H2z" fill="none" stroke="var(--color-warning)" strokeWidth="1.8" strokeLinejoin="round" /><path d="M10 8.5v4M10 14.6v.01" stroke="var(--color-warning)" strokeWidth="1.8" strokeLinecap="round" /></svg>
                  )}
                  <span>{c}</span>
                  {!ok && <span className="sr-only"> (not recognized in the catalogue)</span>}
                  {!ok && <button type="button" className="icon-btn" disabled={busy} onClick={() => edit(c)} aria-label={`Edit ${c}`} title="Edit">
                    <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden><path d="M2 14l1-4 8-8 3 3-8 8z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /></svg></button>}
                  <button type="button" className="icon-btn" disabled={busy} onClick={() => patch({ courses: courses.filter((x) => x !== c) })} aria-label={`Remove ${c}`} title="Remove">
                    <svg width="11" height="11" viewBox="0 0 12 12" aria-hidden><path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {unknown.length > 0 && (
          <div className="mt-3 space-y-2 rounded-xl border border-[#ecd9a4] bg-warning-bg p-3 text-sm" role="note">
            <p className="font-medium text-warning">{unknown.length === 1 ? 'One name isn’t in the catalogue' : `${unknown.length} names aren’t in the catalogue`}</p>
            <p className="text-ink-2">Pathwise will still try to match {unknown.length === 1 ? 'it' : 'them'}, but nothing is assumed to be valid.</p>
            {unknown.slice(0, 3).map((u) => {
              const near = nearest(u);
              return (
                <p key={u} className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">“{u}”</span>
                  {near.length > 0 ? <><span className="text-ink-2">Did you mean</span>{near.map((n) => <Button key={n} small onClick={() => replace(u, n)}>{n}</Button>)}</> : <span className="text-ink-2">No close match. Check the spelling.</span>}
                </p>
              );
            })}
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-x-1 gap-y-0.5 text-sm">
          <span className="text-support w-full">Start from a track</span>
          {TRACK_PRESETS.map((t: TrackPreset) => (
            <button key={t.title} type="button" disabled={busy} className="rounded-md px-2 py-1 text-left font-medium text-accent hover:bg-info-bg disabled:text-disabled" onClick={() => { patch({ courses: t.courses, goal: t.goal }); setNote(null); }}>{t.title}</button>
          ))}
          {courses.length > 0 && <button type="button" disabled={busy} className="ml-auto rounded-md px-1.5 py-1 text-ink-2 hover:bg-subtle" onClick={() => patch({ courses: [] })}>Clear</button>}
        </div>
      </div>

      <div>
        <label htmlFor={`${id}-goal`} className="text-sm font-medium">Learning goal <span className="font-normal text-muted">(optional)</span></label>
        <input id={`${id}-goal`} className="field mt-2" value={goal} maxLength={200} disabled={busy} placeholder="e.g. Prepare for a machine learning engineering role" onChange={(e) => patch({ goal: e.target.value })} />
      </div>

      <div className="border-t border-divider pt-4">
        <button type="button" aria-expanded={optionsOpen} aria-controls={`${id}-options`} onClick={() => patch({ optionsOpen: !optionsOpen })} className="flex w-full items-center justify-between rounded-lg py-1 text-sm font-medium">
          Scheduling preferences
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden style={{ transform: optionsOpen ? 'rotate(180deg)' : 'none', transition: 'transform .15s' }}><path d="M2 5l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </button>
        {optionsOpen && (
          <div id={`${id}-options`} className="mt-4 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
              <div>
                <label htmlFor={`${id}-per`} className="text-sm">Max courses per semester</label>
                <input id={`${id}-per`} inputMode="numeric" className="field mt-1.5" placeholder="No limit" value={maxPerSemester} disabled={busy}
                  aria-invalid={Boolean(perSem.error)} aria-describedby={perSem.error ? `${id}-per-err` : undefined} onChange={(e) => patch({ maxPerSemester: e.target.value })} />
                {perSem.error && <p id={`${id}-per-err`} className="mt-1 text-sm text-error">{perSem.error}</p>}
              </div>
              <div>
                <label htmlFor={`${id}-sem`} className="text-sm">Max semesters</label>
                <input id={`${id}-sem`} inputMode="numeric" className="field mt-1.5" placeholder="No limit" value={maxSemesters} disabled={busy}
                  aria-invalid={Boolean(sems.error)} aria-describedby={sems.error ? `${id}-sem-err` : undefined} onChange={(e) => patch({ maxSemesters: e.target.value })} />
                {sems.error && <p id={`${id}-sem-err`} className="mt-1 text-sm text-error">{sems.error}</p>}
              </div>
            </div>
            <label className="flex items-start gap-3 text-sm">
              <input type="checkbox" className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]" checked={useAi} disabled={busy} onChange={(e) => patch({ useAi: e.target.checked })} />
              <span><span className="font-medium">Use AI to propose extra prerequisites</span><br /><span className="text-support">Proposals are validated and labelled. Off uses curated links only.</span></span>
            </label>
            {useAi && (
              <label className="flex items-start gap-3 text-sm">
                <input type="checkbox" className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]" checked={fallback} disabled={busy} onChange={(e) => patch({ fallback: e.target.checked })} />
                <span><span className="font-medium">Continue without AI if it fails</span><br /><span className="text-support">Otherwise an AI failure stops the request with an error.</span></span>
              </label>
            )}
          </div>
        )}
      </div>

      <div>
        <button type="submit" className="btn btn-primary w-full" disabled={busy} aria-busy={busy}>
          {busy ? (<><Spinner /> Generating…</>) : 'Generate learning path'}
        </button>
        {busy && <p role="status" className="mt-3 text-center text-support">Generating your learning path. This can take a few seconds, longer with AI.</p>}
      </div>
    </form>
  );
}
