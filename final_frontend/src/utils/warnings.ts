/** Softens the backend's technical warning text. Unrecognised warnings are returned unchanged. */
export function friendlyWarning(w: string): string {
  if (w.startsWith('AI proposals were unavailable')) {
    const reason = /\((.*)\)\. Proceeding/s.exec(w)?.[1];
    return `AI suggestions were unavailable, so this path uses curated links only.${reason ? ` Reason: ${reason.replace(/\.$/, '')}.` : ''}`;
  }
  if (w.startsWith('AI assistance was disabled')) return 'AI was off, so this path uses curated links only.';
  if (w.startsWith('AI prerequisite analysis was skipped')) return 'AI was skipped because only one distinct course was selected.';
  if (w.startsWith('AI analysis completed successfully, but no additional')) return 'AI found no extra prerequisite links beyond the curated ones.';
  return w;
}
