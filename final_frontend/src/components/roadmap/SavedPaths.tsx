import { useEffect, useRef, useState } from 'react';
import { useRoadmap } from '../../hooks/useRoadmap';
import { deleteRoadmap, loadHistory } from '../../services/historyService';
import { formatDate } from '../../utils/formatters';
import { Button } from '../common/Button';

/** Browser-local saved paths. The backend has no persistence, so these are plain localStorage entries. */
export function SavedPaths({ disabled }: { disabled?: boolean }) {
  const { open } = useRoadmap();
  const [shown, setShown] = useState(false);
  const [items, setItems] = useState(loadHistory);
  const closeRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!shown) return;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setShown(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [shown]);
  const close = () => { setShown(false); triggerRef.current?.focus(); };

  return (
    <>
      <Button ref={triggerRef} small variant="quiet" disabled={disabled} onClick={() => { setItems(loadHistory()); setShown(true); }}>Saved paths ({items.length})</Button>
      {shown && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onMouseDown={(e) => e.target === e.currentTarget && close()}>
          <div role="dialog" aria-modal="true" aria-labelledby="saved-title" className="flex h-full w-full max-w-sm flex-col overflow-y-auto bg-surface p-5 shadow-[var(--shadow-pop)]">
            <div className="flex items-center justify-between">
              <h2 id="saved-title" className="h-section">Saved paths</h2>
              <Button ref={closeRef} small onClick={close}>Close</Button>
            </div>
            <p className="text-support mt-1">Stored in this browser only.</p>
            {items.length === 0 ? <p className="mt-8 text-ink-2">Nothing saved yet. Each path you generate is saved here automatically.</p> : (
              <ul className="mt-5 space-y-3">
                {items.map((h) => (
                  <li key={h.id} className="card p-4">
                    <p className="text-support">{formatDate(h.savedAt)}</p>
                    <p className="mt-1 font-medium leading-snug">{h.response.learning_goal}</p>
                    <p className="mt-1 line-clamp-2 text-sm text-ink-2">{h.response.ordered_courses.map((c) => c.name).join(', ')}</p>
                    <p className="text-support mt-2">{h.response.ordered_courses.length} courses{h.response.semesters.length > 0 && ` · ${h.response.semesters.length} semesters`}</p>
                    <div className="mt-3 flex gap-2">
                      <Button small onClick={() => { open(h.request, h.response); close(); }}>Open</Button>
                      <Button small variant="quiet" onClick={() => { deleteRoadmap(h.id); setItems(loadHistory()); }} aria-label={`Delete saved path: ${h.response.learning_goal}`}>Delete</Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </>
  );
}
