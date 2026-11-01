import type { LearningPathRequest, LearningPathResponse, Prerequisite, RoadmapModel, RoadmapStats } from '../types/roadmap';

/**
 * Converts the backend response into a display model.
 * - Order is exactly ordered_courses (never re-sorted in React).
 * - Semesters are exactly the returned semester groups from backend DAA scheduler.
 * - Edges preserve relationship provenance (curated vs ai_proposed) and confidence.
 */
export function buildRoadmap(res: LearningPathResponse, req?: LearningPathRequest): RoadmapModel {
  const ids = new Set(res.ordered_courses.map((c) => c.course_id));
  const edges = res.prerequisites.filter((e) => ids.has(e.source_course_id) && ids.has(e.target_course_id));

  // Build mapping from course_id to its assigned semester number
  const courseToSemester = new Map<string, number>();
  if (res.semesters && res.semesters.length > 0) {
    for (const sem of res.semesters) {
      for (const c of sem.courses) {
        courseToSemester.set(c.course_id, sem.semester_number);
      }
    }
  }

  const courses = res.ordered_courses.map((c, i) => ({
    ...c,
    order: i + 1,
    semester: courseToSemester.get(c.course_id),
    prerequisites: edges
      .filter((e) => e.target_course_id === c.course_id)
      .map((e) => ({
        courseId: e.source_course_id,
        type: e.relationship_type,
        explanation: e.explanation,
        source: e.source,
        isAiProposed: e.is_ai_proposed,
        confidence: e.confidence,
        evidenceType: e.evidence_type,
      })),
    unlocks: edges
      .filter((e) => e.source_course_id === c.course_id)
      .map((e) => ({
        courseId: e.target_course_id,
        type: e.relationship_type,
        explanation: e.explanation,
        source: e.source,
        isAiProposed: e.is_ai_proposed,
        confidence: e.confidence,
        evidenceType: e.evidence_type,
      })),
  }));

  return {
    goal: res.learning_goal,
    courses,
    semesters: res.semesters || [],
    edges,
    stats: computeStats(res, edges),
    aiProposalsUsed: res.ai_proposals_used,
    warnings: res.warnings,
    aiSummary: res.ai_summary,
    constraints: req
      ? {
          maxCoursesPerSemester: req.max_courses_per_semester,
          maxSemesters: req.max_semesters,
        }
      : undefined,
  };
}

export function computeStats(res: LearningPathResponse, edges: Prerequisite[]): RoadmapStats {
  const countType = (t: string) => edges.filter((e) => e.relationship_type === t).length;
  const required = countType('required');
  const recommended = countType('recommended');
  const optional = countType('optional');
  const curatedCount = edges.filter((e) => !e.is_ai_proposed).length;
  const aiCount = edges.filter((e) => e.is_ai_proposed).length;

  return {
    selected: res.selected_courses.length,
    ordered: res.ordered_courses.length,
    semesters: res.semesters?.length || 0,
    relationships: edges.length,
    required,
    recommended,
    optional,
    curatedCount,
    aiCount,
    other: edges.length - required - recommended - optional,
  };
}

/**
 * Layout helper for the graph view only: column = length of the longest prerequisite chain ending at the course.
 * Drawing aid only; topological sequence is strictly computed by Kahn's algorithm on the backend.
 */
export function layerCourses(ids: string[], edges: Prerequisite[]): Record<string, number> {
  const layer: Record<string, number> = Object.fromEntries(ids.map((id) => [id, 0]));
  for (let pass = 0; pass < ids.length; pass++) {
    let changed = false;
    for (const e of edges) {
      const next = (layer[e.source_course_id] ?? 0) + 1;
      if (next > (layer[e.target_course_id] ?? 0) && next < ids.length) {
        layer[e.target_course_id] = next;
        changed = true;
      }
    }
    if (!changed) break;
  }
  return layer;
}
