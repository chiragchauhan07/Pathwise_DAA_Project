import { useId, useImperativeHandle, useMemo, useRef, useState, type FormEvent, type KeyboardEvent, type Ref } from 'react';
import { CURATED_COURSES, TRACK_PRESETS, type TrackPreset } from '../../data/coursesCatalog';
import { useRoadmap } from '../../hooks/useRoadmap';
import type { LearningPathRequest } from '../../types/roadmap';
import { splitCourseInput } from '../../utils/formatters';
import { Button } from '../common/Button';
import { Spinner } from '../common/Spinner';

const MAX_COURSES = 50;
export interface CourseFormHandle { focusInput: () => void; openOptions?: () => void }

const norm = (s: string) => s.trim().toLowerCase();

const findCatalogCourse = (name: string) => {
  const q = norm(name);
  return CURATED_COURSES.find((c) => norm(c.name) === q || c.id === q || c.aliases.some((a) => norm(a) === q));
};

function distance(a: string, b: string): number {
  const dp = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)] as number[]);
  for (let j = 1; j <= b.length; j++) dp[0][j] = j;
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++)
      dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return dp[a.length][b.length];
}

/** Closest catalogue names for spelling help. */
function nearest(name: string): string[] {
  const q = norm(name);
  return CURATED_COURSES.map((c) => {
    const names = [c.name, ...c.aliases].map(norm);
    const d = Math.min(...names.map((n) => (n.includes(q) || q.includes(n) ? 0 : distance(q, n))));
    return { name: c.name, d };
  })
    .filter((x) => x.d <= Math.max(3, Math.floor(q.length * 0.4)))
    .sort((a, b) => a.d - b.d)
    .slice(0, 3)
    .map((x) => x.name);
}

export function CourseForm({ busy, onSubmit, handleRef }: { busy: boolean; onSubmit: (req: LearningPathRequest) => void; handleRef?: Ref<CourseFormHandle> }) {
  const { draft, setDraft } = useRoadmap();
  const { courses } = draft;
  const id = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState('');
  const [note, setNote] = useState<string | null>(null);
  const [unrecognizedPrompt, setUnrecognizedPrompt] = useState<{ query: string; suggestions: string[] } | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [tried, setTried] = useState(false);

  const patch = (p: Partial<typeof draft>) => setDraft((d) => ({ ...d, ...p }));
  useImperativeHandle(handleRef, () => ({ focusInput: () => inputRef.current?.focus(), openOptions: () => {} }));

  const suggestions = useMemo(() => {
    const q = norm(text);
    if (!q) return [];
    return CURATED_COURSES.filter(
      (c) => !courses.some((s) => norm(s) === norm(c.name)) && (norm(c.name).includes(q) || c.aliases.some((a) => norm(a).includes(q))),
    ).slice(0, 6);
  }, [text, courses]);

  const add = (names: string[]) => {
    const next = [...courses];
    let msg: string | null = null;
    let unrec: { query: string; suggestions: string[] } | null = null;

    for (const raw of names) {
      const n = raw.trim();
      if (!n) continue;
      if (n.length > 100) { msg = 'Course names can be up to 100 characters.'; continue; }

      // Check against Knowledge Base
      const catalogMatch = findCatalogCourse(n);
      if (!catalogMatch) {
        const closeOnes = nearest(n);
        unrec = { query: n, suggestions: closeOnes };
        msg = `“${n}” is not in the knowledge base catalog.`;
        continue;
      }

      const canonicalName = catalogMatch.name;
      if (next.some((c) => norm(c) === norm(canonicalName))) { msg = `“${canonicalName}” is already in your list.`; continue; }
      if (next.length >= MAX_COURSES) { msg = `You can add up to ${MAX_COURSES} courses.`; break; }
      next.push(canonicalName);
    }

    patch({ courses: next });
    setNote(msg);
    setUnrecognizedPrompt(unrec);
  };

  const commit = () => {
    const names = splitCourseInput(text);
    setText('');
    setOpen(false);
    if (names.length) add(names);
  };

  const pick = (name: string) => {
    add([name]);
    setText('');
    setOpen(false);
    setActive(0);
    setUnrecognizedPrompt(null);
    inputRef.current?.focus();
  };

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' && suggestions.length) { e.preventDefault(); setOpen(true); setActive((a) => (a + 1) % suggestions.length); }
    else if (e.key === 'ArrowUp' && suggestions.length) { e.preventDefault(); setActive((a) => (a - 1 + suggestions.length) % suggestions.length); }
    else if (e.key === 'Escape') setOpen(false);
    else if (e.key === 'Enter') { e.preventDefault(); if (open && suggestions[active]) pick(suggestions[active].name); else commit(); }
    else if (e.key === ',') { e.preventDefault(); commit(); }
    else if (e.key === 'Backspace' && !text && courses.length) patch({ courses: courses.slice(0, -1) });
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setTried(true);
    const pending = splitCourseInput(text);
    let list = courses;
    if (pending.length) {
      const validPending: string[] = [];
      for (const p of pending) {
        const match = findCatalogCourse(p);
        if (match && !courses.some((c) => norm(c) === norm(match.name))) {
          validPending.push(match.name);
        }
      }
      list = [...courses, ...validPending];
      patch({ courses: list });
      setText('');
    }
    if (list.length === 0) { inputRef.current?.focus(); return; }
    setNote(null);
    setUnrecognizedPrompt(null);
    onSubmit({
      courses: list,
      use_ai: false,
      fallback_on_ai_failure: false,
    });
  };

  const showEmptyError = tried && courses.length === 0 && !text.trim();
  const listId = `${id}-list`;

  return (
    <form onSubmit={submit} noValidate aria-label="Course registration settings" className="card space-y-6 p-5 sm:p-6">
      <div>
        <div className="flex items-baseline justify-between">
          <label htmlFor={`${id}-course`} className="text-sm font-semibold text-ink">Curriculum Courses</label>
          <span className="text-xs text-support font-mono">{courses.length} selected</span>
        </div>

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
              placeholder="Search or select from 100 catalog courses"
              onChange={(e) => { setText(e.target.value); setOpen(true); setActive(0); }}
              onFocus={() => setOpen(true)}
              onBlur={() => setTimeout(() => setOpen(false), 200)}
              onKeyDown={onKey}
            />
            <Button onClick={commit} disabled={!text.trim() || busy} aria-label="Add course">Add</Button>
          </div>

          {open && suggestions.length > 0 && (
            <ul id={listId} role="listbox" aria-label="Matching courses" className="absolute left-0 right-0 z-20 mt-1 overflow-hidden rounded-xl border border-line bg-surface py-1 shadow-[var(--shadow-pop)]">
              {suggestions.map((s, i) => (
                <li
                  key={s.id}
                  id={`${id}-opt-${i}`}
                  role="option"
                  aria-selected={i === active}
                  onMouseDown={(e) => { e.preventDefault(); pick(s.name); }}
                  onMouseEnter={() => setActive(i)}
                  className={`flex cursor-pointer items-baseline justify-between gap-3 px-3 py-2 ${i === active ? 'bg-info-bg' : ''}`}
                >
                  <span className="font-medium text-ink">{s.name}</span>
                  <span className="text-support shrink-0 text-xs font-mono">{s.category}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <p id={`${id}-help`} className="mt-2 text-support text-xs" aria-live="polite">
          {showEmptyError ? (
            <span className="font-medium text-error">Add at least one course to sequence.</span>
          ) : note ?? 'Type to search the Knowledge Base. Only curated catalog courses are sequenced.'}
        </p>

        {unrecognizedPrompt && (
          <div className="mt-3 rounded-xl border border-warning/40 bg-warning-bg p-3 text-xs space-y-2">
            <p className="font-semibold text-warning">
              “{unrecognizedPrompt.query}” is not in the knowledge base catalog.
            </p>
            {unrecognizedPrompt.suggestions.length > 0 ? (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-ink-2">Did you mean:</span>
                {unrecognizedPrompt.suggestions.map((s) => (
                  <Button key={s} small onClick={() => pick(s)}>
                    {s}
                  </Button>
                ))}
              </div>
            ) : (
              <p className="text-ink-2">Please select from the 100 catalog courses or click a preset track below.</p>
            )}
          </div>
        )}

        {courses.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2" aria-label="Selected courses">
            {courses.map((c) => (
              <li key={norm(c)} className="chip">
                <span>{c}</span>
                <button
                  type="button"
                  className="icon-btn ml-1"
                  disabled={busy}
                  onClick={() => patch({ courses: courses.filter((x) => x !== c) })}
                  aria-label={`Remove ${c}`}
                  title="Remove"
                >
                  <svg width="11" height="11" viewBox="0 0 12 12" aria-hidden>
                    <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-x-1 gap-y-0.5 text-xs">
          <span className="text-support w-full font-medium">Curricular benchmark presets:</span>
          {TRACK_PRESETS.map((t: TrackPreset) => (
            <button
              key={t.title}
              type="button"
              disabled={busy}
              className="rounded-md px-2 py-1 text-left font-medium text-accent hover:bg-info-bg disabled:text-disabled"
              onClick={() => { patch({ courses: t.courses }); setNote(null); setUnrecognizedPrompt(null); }}
            >
              {t.title}
            </button>
          ))}
          {courses.length > 0 && (
            <button
              type="button"
              disabled={busy}
              className="ml-auto rounded-md px-1.5 py-1 text-ink-2 hover:bg-subtle text-xs"
              onClick={() => { patch({ courses: [] }); setUnrecognizedPrompt(null); }}
            >
              Clear all
            </button>
          )}
        </div>
      </div>

      <div>
        <button type="submit" className="btn btn-primary w-full" disabled={busy} aria-busy={busy}>
          {busy ? (<><Spinner /> Computing Topological Schedule…</>) : 'Generate Registration Order'}
        </button>
        {busy && <p role="status" className="mt-3 text-center text-xs text-support">Running 3-state DFS cycle check and Kahn’s min-heap topological sort…</p>}
      </div>
    </form>
  );
}
