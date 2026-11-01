import { useId, useRef, type ReactNode } from 'react';

export interface TabDef { id: string; label: string; content: ReactNode }

export function Tabs({ tabs, active, onChange }: { tabs: TabDef[]; active: string; onChange: (id: string) => void }) {
  const base = useId();
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const move = (i: number) => { const t = tabs[(i + tabs.length) % tabs.length]; onChange(t.id); refs.current[t.id]?.focus(); };
  const idx = tabs.findIndex((t) => t.id === active);
  return (
    <div>
      <div role="tablist" aria-label="Results" className="flex gap-1 overflow-x-auto border-b border-divider">
        {tabs.map((t) => (
          <button
            key={t.id}
            ref={(el) => { refs.current[t.id] = el; }}
            role="tab"
            id={`${base}-t-${t.id}`}
            aria-selected={t.id === active}
            aria-controls={`${base}-p-${t.id}`}
            tabIndex={t.id === active ? 0 : -1}
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowRight') { e.preventDefault(); move(idx + 1); }
              else if (e.key === 'ArrowLeft') { e.preventDefault(); move(idx - 1); }
              else if (e.key === 'Home') { e.preventDefault(); move(0); }
              else if (e.key === 'End') { e.preventDefault(); move(tabs.length - 1); }
            }}
            className={`-mb-px min-h-11 shrink-0 border-b-2 px-3 text-sm sm:px-4 font-medium transition-colors ${t.id === active ? 'border-ink text-ink' : 'border-transparent text-ink-2 hover:text-ink'}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tabs.map((t) => (
        <div key={t.id} role="tabpanel" id={`${base}-p-${t.id}`} aria-labelledby={`${base}-t-${t.id}`} hidden={t.id !== active} className="pt-6">
          {t.id === active && t.content}
        </div>
      ))}
    </div>
  );
}
