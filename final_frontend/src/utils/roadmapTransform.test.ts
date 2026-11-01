import { describe, expect, it } from 'vitest';
import { buildRoadmap, layerCourses } from './roadmapTransform';
import { parseLearningPathResponse } from '../services/roadmapService';
import type { Course, LearningPathResponse } from '../types/roadmap';

const c = (id: string): Course => ({
  course_id: id,
  name: id.toUpperCase(),
  aliases: [],
  category: 'Test Category',
  description: 'Test description',
  difficulty: 'beginner',
});

const res: LearningPathResponse = {
  learning_goal: 'Test Goal',
  selected_courses: [c('b'), c('a'), c('d')],
  ordered_courses: [c('a'), c('b'), c('d')],
  semesters: [
    { semester_number: 1, courses: [c('a')], course_count: 1 },
    { semester_number: 2, courses: [c('b'), c('d')], course_count: 2 },
  ],
  prerequisites: [
    {
      source_course_id: 'a',
      target_course_id: 'b',
      relationship_type: 'required',
      explanation: 'e',
      source: 'curated',
      is_ai_proposed: false,
      confidence: 0.95,
      evidence_type: 'expert_curated',
    },
    {
      source_course_id: 'zz',
      target_course_id: 'b',
      relationship_type: 'optional',
    },
  ],
  ai_proposals_used: false,
  warnings: [],
};

describe('buildRoadmap', () => {
  const m = buildRoadmap(res);

  it('preserves deterministic backend order', () => {
    expect(m.courses.map((x) => x.course_id)).toEqual(['a', 'b', 'd']);
  });

  it('drops edges with unregistered endpoints and tallies relationship stats', () => {
    expect(m.edges).toHaveLength(1);
    expect(m.stats).toMatchObject({
      relationships: 1,
      required: 1,
      optional: 0,
      curatedCount: 1,
      aiCount: 0,
    });
  });

  it('maps assigned semester numbers correctly to courses', () => {
    expect(m.courses[0].semester).toBe(1);
    expect(m.courses[1].semester).toBe(2);
    expect(m.courses[2].semester).toBe(2);
  });

  it('attaches prerequisites, unlocks, and provenance data', () => {
    expect(m.courses[1].prerequisites[0].courseId).toBe('a');
    expect(m.courses[1].prerequisites[0].source).toBe('curated');
    expect(m.courses[1].prerequisites[0].confidence).toBe(0.95);
    expect(m.courses[0].unlocks[0].courseId).toBe('b');
  });

  it('preserves and maps ai_summary metadata in model', () => {
    const withAiSummary = buildRoadmap({
      ...res,
      ai_summary: {
        requested: true,
        course_resolution_status: 'ai_disambiguated',
        unknown_courses_evaluated: 1,
        ambiguous_courses_evaluated: 0,
        proposal_request_status: 'succeeded',
        proposals_received: 2,
        proposals_accepted: 1,
        proposals_rejected: 1,
        relationships_added: 1,
        model: 'gemini-3.5-flash-lite',
        message: 'AI completed successfully.',
      },
    });
    expect(withAiSummary.aiSummary).toBeDefined();
    expect(withAiSummary.aiSummary?.relationships_added).toBe(1);
    expect(withAiSummary.aiSummary?.course_resolution_status).toBe('ai_disambiguated');
    expect(withAiSummary.aiSummary?.model).toBe('gemini-3.5-flash-lite');
  });

  it('supports single course with no edges', () => {
    const single = buildRoadmap({
      learning_goal: 'Solo',
      selected_courses: [c('only')],
      ordered_courses: [c('only')],
      semesters: [{ semester_number: 1, courses: [c('only')], course_count: 1 }],
      prerequisites: [],
      ai_proposals_used: false,
      warnings: [],
    });
    expect(single.courses).toHaveLength(1);
    expect(single.edges).toHaveLength(0);
    expect(single.stats.selected).toBe(1);
    expect(single.stats.ordered).toBe(1);
    expect(single.stats.relationships).toBe(0);
  });
});

describe('layerCourses', () => {
  it('layers by longest prerequisite chain for graph visualization', () => {
    const l = layerCourses(
      ['a', 'b', 'c'],
      [
        { source_course_id: 'a', target_course_id: 'b', relationship_type: 'required' },
        { source_course_id: 'b', target_course_id: 'c', relationship_type: 'required' },
        { source_course_id: 'a', target_course_id: 'c', relationship_type: 'required' },
      ]
    );
    expect(l).toEqual({ a: 0, b: 1, c: 2 });
  });

  it('safely caps iterations on cyclic input', () => {
    const l = layerCourses(
      ['a', 'b'],
      [
        { source_course_id: 'a', target_course_id: 'b', relationship_type: 'required' },
        { source_course_id: 'b', target_course_id: 'a', relationship_type: 'required' },
      ]
    );
    expect(Object.keys(l)).toHaveLength(2);
  });
});

describe('parseLearningPathResponse', () => {
  it('accepts and parses valid backend response contract including semesters and provenance', () => {
    const parsed = parseLearningPathResponse(res);
    expect(parsed.ordered_courses).toHaveLength(3);
    expect(parsed.semesters).toHaveLength(2);
    expect(parsed.prerequisites[0].confidence).toBe(0.95);
  });

  it('rejects malformed payloads', () => {
    expect(() => parseLearningPathResponse({ learning_goal: 'x' })).toThrow();
    expect(() => parseLearningPathResponse(null)).toThrow();
  });
});
