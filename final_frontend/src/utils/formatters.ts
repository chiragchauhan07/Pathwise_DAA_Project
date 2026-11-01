import type { RelationshipType } from '../types/roadmap';

export const RELATION_LABEL: Record<RelationshipType, string> = {
  required: 'Required',
  recommended: 'Recommended',
  optional: 'Optional',
};

export const RELATION_HELP: Record<RelationshipType, string> = {
  required: 'Generally necessary preparation',
  recommended: 'Makes the later course easier; varies by curriculum',
  optional: 'Useful background, not needed to begin',
};

export const relationLabel = (t: string) => RELATION_LABEL[t as RelationshipType] ?? t;

export const capitalize = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? 'Unknown date' : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

/** Splits "Python, ML ; Algorithms" style input into trimmed, non-empty names. */
export function splitCourseInput(raw: string): string[] {
  return raw.split(/[,;\n]/).map((s) => s.trim()).filter(Boolean);
}
