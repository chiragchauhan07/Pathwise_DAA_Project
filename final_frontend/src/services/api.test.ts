import { describe, expect, it } from 'vitest';
import { toApiError } from './api';

describe('toApiError mapper', () => {
  it('handles FastAPI 422 array of validation errors', () => {
    const err = toApiError(422, {
      detail: [{ loc: ['body', 'selected_courses'], msg: 'Field required' }],
    });
    expect(err.kind).toBe('validation');
    expect(err.message).toContain('Field required');
    expect(err.status).toBe(422);
  });

  it('handles course_resolution_error', () => {
    const err = toApiError(400, {
      detail: {
        error: 'course_resolution_error',
        message: 'Could not resolve course "Programming"',
      },
    });
    expect(err.kind).toBe('course_resolution');
    expect(err.message).toBe('Could not resolve course "Programming"');
    expect(err.needsClarification).toBeFalsy();
  });

  it('handles structured clarification error for ambiguous courses', () => {
    const err = toApiError(400, {
      detail: {
        error: 'course_resolution_error',
        message: "Course query 'English' is ambiguous: Choose Composition or Literature.",
        needs_clarification: true,
        query: 'English',
        clarification: 'Choose Composition or Literature.',
        candidates: ['English Composition', 'English Literature'],
      },
    });
    expect(err.kind).toBe('course_resolution');
    expect(err.needsClarification).toBe(true);
    expect(err.query).toBe('English');
    expect(err.clarification).toBe('Choose Composition or Literature.');
    expect(err.candidates).toEqual(['English Composition', 'English Literature']);
  });

  it('handles cyclic_dependency_error with cycle path', () => {
    const err = toApiError(400, {
      detail: {
        error: 'cyclic_dependency_error',
        message: 'Cycle detected',
        cycle_path: ['cs101', 'cs102', 'cs101'],
      },
    });
    expect(err.kind).toBe('cycle');
    expect(err.cyclePath).toEqual(['cs101', 'cs102', 'cs101']);
  });

  it('handles curricular_constraint_error with semester counts', () => {
    const err = toApiError(400, {
      detail: {
        error: 'curricular_constraint_error',
        message: 'Cannot schedule in 1 semester',
        required_semesters: 3,
        max_semesters: 1,
      },
    });
    expect(err.kind).toBe('curricular_constraint');
    expect(err.requiredSemesters).toBe(3);
    expect(err.maxSemesters).toBe(1);
  });

  it('maps AI-specific errors correctly', () => {
    const authErr = toApiError(500, {
      detail: {
        error: 'ai_authentication_error',
        message: 'API key invalid',
      },
    });
    expect(authErr.kind).toBe('ai_service');

    const timeoutErr = toApiError(504, {
      detail: {
        error: 'ai_timeout_error',
        message: 'AI request timed out',
      },
    });
    expect(timeoutErr.kind).toBe('timeout');

    const timeoutSubErr = toApiError(500, {
      detail: {
        error: 'ai_service_error',
        sub_error: 'AITimeoutError',
        message: 'Deadline exceeded',
      },
    });
    expect(timeoutSubErr.kind).toBe('timeout');
  });

  it('maps gateway 502/503/504 errors to network offline notice', () => {
    const err = toApiError(503, null);
    expect(err.kind).toBe('network');
    expect(err.message).toContain('offline or unreachable');
  });
});

