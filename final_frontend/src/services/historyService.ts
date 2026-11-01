import type { LearningPathRequest, LearningPathResponse, SavedRoadmap } from '../types/roadmap';
import { parseLearningPathResponse } from './roadmapService';

/** Browser-local history. The backend has no persistence endpoints. Stores only request inputs + the response. */
const KEY = 'daa-learning-path:history:v1';
const MAX = 30;

export function loadHistory(): SavedRoadmap[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    if (!Array.isArray(parsed)) return [];
    const out: SavedRoadmap[] = [];
    for (const item of parsed) {
      try {
        if (typeof item?.id !== 'string' || typeof item?.savedAt !== 'string') continue;
        out.push({ id: item.id, savedAt: item.savedAt, request: item.request, response: parseLearningPathResponse(item.response) });
      } catch {
        // outdated or corrupted entry: skip it
      }
    }
    return out;
  } catch {
    return [];
  }
}

function write(list: SavedRoadmap[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX)));
  } catch {
    // storage full or unavailable: history is best-effort
  }
}

export function saveRoadmap(request: LearningPathRequest, response: LearningPathResponse): SavedRoadmap {
  const entry: SavedRoadmap = {
    id: crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    savedAt: new Date().toISOString(),
    request: { courses: request.courses, learning_goal: request.learning_goal, use_ai: request.use_ai },
    response,
  };
  write([entry, ...loadHistory()]);
  return entry;
}

export function deleteRoadmap(id: string) {
  write(loadHistory().filter((h) => h.id !== id));
}
