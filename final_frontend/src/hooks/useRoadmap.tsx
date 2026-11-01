import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react';
import { ApiError } from '../services/api';
import { saveRoadmap } from '../services/historyService';
import { generateLearningPath } from '../services/roadmapService';
import type { LearningPathRequest, LearningPathResponse, RoadmapModel } from '../types/roadmap';
import { buildRoadmap } from '../utils/roadmapTransform';

type Status = 'idle' | 'loading' | 'success' | 'error';

/** What the person has typed into the form. Lives here so it survives navigating to DAA / AI and back. */
export interface FormDraft {
  courses: string[];
  goal: string;
  useAi: boolean;
  fallback: boolean;
  maxPerSemester: string;
  maxSemesters: string;
  optionsOpen: boolean;
}

export const EMPTY_DRAFT: FormDraft = {
  courses: [],
  goal: '',
  useAi: true,
  fallback: true,
  maxPerSemester: '',
  maxSemesters: '',
  optionsOpen: false,
};

interface RoadmapContextValue {
  status: Status;
  roadmap: RoadmapModel | null;
  request: LearningPathRequest | null;
  /** The most recent request sent, successful or not. Used to offer a retry. */
  lastRequest: LearningPathRequest | null;
  error: ApiError | null;
  draft: FormDraft;
  setDraft: (next: FormDraft | ((prev: FormDraft) => FormDraft)) => void;
  generate: (req: LearningPathRequest) => Promise<void>;
  open: (req: Pick<LearningPathRequest, 'courses' | 'learning_goal' | 'use_ai'>, res: LearningPathResponse) => void;
  clearError: () => void;
}

const Ctx = createContext<RoadmapContextValue | null>(null);

export function RoadmapProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('idle');
  const [roadmap, setRoadmap] = useState<RoadmapModel | null>(null);
  const [request, setRequest] = useState<LearningPathRequest | null>(null);
  const [lastRequest, setLastRequest] = useState<LearningPathRequest | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [draft, setDraft] = useState<FormDraft>(EMPTY_DRAFT);
  const inFlight = useRef(false);

  const generate = useCallback(async (req: LearningPathRequest) => {
    if (inFlight.current) return; // prevent duplicate submissions
    inFlight.current = true;
    setLastRequest(req);
    setStatus('loading');
    setError(null);
    try {
      const res = await generateLearningPath(req);
      if (res.ordered_courses.length === 0) throw new ApiError('invalid_response', 'The backend returned an empty learning path.');
      setRoadmap(buildRoadmap(res, req));
      setRequest(req);
      saveRoadmap(req, res);
      setStatus('success');
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError('server', 'Something went wrong while generating the path.'));
      setStatus('error');
    } finally {
      inFlight.current = false;
    }
  }, []);

  const open = useCallback<RoadmapContextValue['open']>((req, res) => {
    const fullReq: LearningPathRequest = { fallback_on_ai_failure: true, ...req };
    setRoadmap(buildRoadmap(res, fullReq));
    setRequest(fullReq);
    setError(null);
    setStatus('success');
  }, []);

  const clearError = useCallback(() => {
    setError(null);
    setStatus((s) => (s === 'error' ? (roadmap ? 'success' : 'idle') : s));
  }, [roadmap]);

  const value = useMemo(
    () => ({ status, roadmap, request, lastRequest, error, draft, setDraft, generate, open, clearError }),
    [status, roadmap, request, lastRequest, error, draft, generate, open, clearError],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useRoadmap() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useRoadmap must be used inside <RoadmapProvider>');
  return v;
}
