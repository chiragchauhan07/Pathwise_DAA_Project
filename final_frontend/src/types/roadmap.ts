/**
 * Pathwise Types - Matches the backend contract in backend/core_engine/main.py.
 */

export type Difficulty = 'beginner' | 'intermediate' | 'advanced';
export type RelationshipType = 'required' | 'recommended' | 'optional';

export interface Course {
  course_id: string;
  name: string;
  aliases: string[];
  category: string;
  description: string;
  difficulty: Difficulty | string;
  source?: 'curated' | 'ai_inferred' | string;
  is_curated?: boolean;
  is_ai_inferred?: boolean;
  provenance?: 'expert_curated' | 'ai_inferred_candidate' | 'ai_disambiguated' | string;
}

export interface AISummary {
  requested: boolean;
  course_resolution_status: 'curated_only' | 'ai_inferred' | 'ai_disambiguated' | string;
  unknown_courses_evaluated: number;
  ambiguous_courses_evaluated: number;
  proposal_request_status: 'disabled' | 'skipped' | 'succeeded' | 'failed' | string;
  proposals_received: number;
  proposals_accepted: number;
  proposals_rejected: number;
  relationships_added: number;
  model?: string | null;
  message: string;
}

export interface Prerequisite {
  source_course_id: string;
  target_course_id: string;
  relationship_type: RelationshipType | string;
  explanation?: string | null;
  source?: 'curated' | 'ai_proposed' | string;
  is_ai_proposed?: boolean;
  confidence?: number | null;
  evidence_type?: string | null;
}

export interface SemesterGroup {
  semester_number: number;
  courses: Course[];
  course_count: number;
}

export interface LearningPathRequest {
  courses: string[];
  learning_goal?: string;
  use_ai?: boolean;
  fallback_on_ai_failure?: boolean;
  max_courses_per_semester?: number | null;
  max_semesters?: number | null;
}

export interface LearningPathResponse {
  learning_goal: string;
  selected_courses: Course[];
  ordered_courses: Course[];
  semesters: SemesterGroup[];
  prerequisites: Prerequisite[];
  ai_proposals_used: boolean;
  warnings: string[];
  ai_summary?: AISummary | null;
}

export type ApiErrorKind =
  | 'network'
  | 'timeout'
  | 'validation'
  | 'course_resolution'
  | 'cycle'
  | 'curricular_constraint'
  | 'ai_service'
  | 'server'
  | 'invalid_response'
  | 'bad_request';

/** A relationship attached to a course in the display model. */
export interface Relation {
  courseId: string;
  type: RelationshipType | string;
  explanation?: string | null;
  source?: string;
  isAiProposed?: boolean;
  confidence?: number | null;
  evidenceType?: string | null;
}

export interface RoadmapCourse extends Course {
  /** 1-based position in the backend's ordered_courses. Never recomputed in the frontend. */
  order: number;
  semester?: number;
  prerequisites: Relation[];
  unlocks: Relation[];
}

export interface RoadmapStats {
  selected: number;
  ordered: number;
  semesters: number;
  relationships: number;
  required: number;
  recommended: number;
  optional: number;
  curatedCount: number;
  aiCount: number;
  other: number;
}

export interface RoadmapModel {
  goal: string;
  courses: RoadmapCourse[];
  semesters: SemesterGroup[];
  edges: Prerequisite[];
  stats: RoadmapStats;
  aiProposalsUsed: boolean;
  warnings: string[];
  aiSummary?: AISummary | null;
  constraints?: {
    maxCoursesPerSemester?: number | null;
    maxSemesters?: number | null;
  };
}

export interface SavedRoadmap {
  id: string;
  savedAt: string;
  request: LearningPathRequest;
  response: LearningPathResponse;
}
