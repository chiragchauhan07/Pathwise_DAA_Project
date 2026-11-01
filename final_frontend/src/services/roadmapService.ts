import { ApiError, request } from './api';
import type { Course, LearningPathRequest, LearningPathResponse, Prerequisite, SemesterGroup } from '../types/roadmap';

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null;

function isCourse(v: unknown): v is Course {
  return isObj(v) && typeof v.course_id === 'string' && typeof v.name === 'string';
}

function isPrereq(v: unknown): v is Prerequisite {
  return (
    isObj(v) &&
    typeof v.source_course_id === 'string' &&
    typeof v.target_course_id === 'string' &&
    typeof v.relationship_type === 'string'
  );
}

function isSemesterGroup(v: unknown): v is SemesterGroup {
  return isObj(v) && typeof v.semester_number === 'number' && Array.isArray(v.courses);
}

/** Runtime check that the payload matches the documented contract; protects the UI from malformed data. */
export function parseLearningPathResponse(raw: unknown): LearningPathResponse {
  if (
    !isObj(raw) ||
    typeof raw.learning_goal !== 'string' ||
    !Array.isArray(raw.selected_courses) ||
    !raw.selected_courses.every(isCourse) ||
    !Array.isArray(raw.ordered_courses) ||
    !raw.ordered_courses.every(isCourse) ||
    !Array.isArray(raw.prerequisites) ||
    !raw.prerequisites.every(isPrereq)
  ) {
    throw new ApiError('invalid_response', 'The backend response did not match the expected learning-path format.');
  }

  const rawSemesters = Array.isArray(raw.semesters) ? raw.semesters : [];
  const semesters: SemesterGroup[] = rawSemesters
    .filter(isSemesterGroup)
    .map((s) => ({
      semester_number: s.semester_number,
      courses: Array.isArray(s.courses) ? (s.courses.filter(isCourse) as Course[]) : [],
      course_count: typeof s.course_count === 'number' ? s.course_count : (s.courses?.length ?? 0),
    }));

  const prerequisites: Prerequisite[] = raw.prerequisites.map((p) => {
    const rawP = p as unknown as Record<string, unknown>;
    return {
      source_course_id: String(rawP.source_course_id),
      target_course_id: String(rawP.target_course_id),
      relationship_type: String(rawP.relationship_type),
      explanation: typeof rawP.explanation === 'string' ? rawP.explanation : null,
      source: typeof rawP.source === 'string' ? rawP.source : (rawP.is_ai_proposed ? 'ai_proposed' : 'curated'),
      is_ai_proposed: Boolean(rawP.is_ai_proposed),
      confidence: typeof rawP.confidence === 'number' ? rawP.confidence : null,
      evidence_type: typeof rawP.evidence_type === 'string' ? rawP.evidence_type : null,
    };
  });

  const rawAiSummary = isObj(raw.ai_summary) ? (raw.ai_summary as Record<string, unknown>) : null;
  const aiSummary = rawAiSummary
    ? {
        requested: Boolean(rawAiSummary.requested),
        course_resolution_status: String(rawAiSummary.course_resolution_status ?? 'curated_only'),
        unknown_courses_evaluated: Number(rawAiSummary.unknown_courses_evaluated ?? 0),
        ambiguous_courses_evaluated: Number(rawAiSummary.ambiguous_courses_evaluated ?? 0),
        proposal_request_status: String(rawAiSummary.proposal_request_status ?? 'disabled'),
        proposals_received: Number(rawAiSummary.proposals_received ?? 0),
        proposals_accepted: Number(rawAiSummary.proposals_accepted ?? 0),
        proposals_rejected: Number(rawAiSummary.proposals_rejected ?? 0),
        relationships_added: Number(rawAiSummary.relationships_added ?? 0),
        model: typeof rawAiSummary.model === 'string' ? rawAiSummary.model : null,
        message: String(rawAiSummary.message ?? ''),
      }
    : null;

  return {
    learning_goal: raw.learning_goal,
    selected_courses: raw.selected_courses as Course[],
    ordered_courses: raw.ordered_courses as Course[],
    semesters,
    prerequisites,
    ai_proposals_used: raw.ai_proposals_used === true,
    warnings: Array.isArray(raw.warnings) ? raw.warnings.filter((w): w is string => typeof w === 'string') : [],
    ai_summary: aiSummary,
  };
}

export async function generateLearningPath(payload: LearningPathRequest): Promise<LearningPathResponse> {
  const raw = await request<unknown>('/api/v1/learning-path', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return parseLearningPathResponse(raw);
}

export interface Health {
  status: string;
  service: string;
  version: string;
}

export const checkHealth = () => request<Health>('/api/v1/health');

export interface BackendAiStatus {
  configured: boolean;
  key_present: boolean;
  key_empty: boolean;
  key_source: string;
  model: string;
  timeout_seconds: number;
  max_retries: number;
  client_initializable: boolean;
  error?: string | null;
}

export const checkAiStatus = () => request<BackendAiStatus>('/api/v1/ai/status');
