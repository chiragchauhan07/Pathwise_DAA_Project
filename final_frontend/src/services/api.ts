import type { ApiErrorKind } from '../types/roadmap';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '');
const TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS) || 45000;

export class ApiError extends Error {
  kind: ApiErrorKind;
  status?: number;
  cyclePath?: string[];
  requiredSemesters?: number | null;
  maxSemesters?: number | null;
  needsClarification?: boolean;
  query?: string;
  clarification?: string;
  candidates?: string[];

  constructor(
    kind: ApiErrorKind,
    message: string,
    extra: {
      status?: number;
      cyclePath?: string[];
      requiredSemesters?: number | null;
      maxSemesters?: number | null;
      needsClarification?: boolean;
      query?: string;
      clarification?: string;
      candidates?: string[];
    } = {}
  ) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = extra.status;
    this.cyclePath = extra.cyclePath;
    this.requiredSemesters = extra.requiredSemesters;
    this.maxSemesters = extra.maxSemesters;
    this.needsClarification = extra.needsClarification;
    this.query = extra.query;
    this.clarification = extra.clarification;
    this.candidates = extra.candidates;
  }
}

/** Backend error bodies look like {detail:{error,message,cycle_path?,required_semesters?,max_semesters?,needs_clarification?,query?,clarification?,candidates?}} or FastAPI 422 {detail:[{msg,loc}]}. */
export function toApiError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (Array.isArray(detail)) {
    const msgs = detail.map((d) => (d as { msg?: string }).msg).filter(Boolean);
    return new ApiError(
      'validation',
      msgs.length ? `Invalid request: ${msgs.join('; ')}` : 'The request parameters were invalid.',
      { status }
    );
  }
  if (detail && typeof detail === 'object') {
    const d = detail as {
      error?: string;
      message?: string;
      cycle_path?: string[];
      required_semesters?: number | null;
      max_semesters?: number | null;
      needs_clarification?: boolean;
      query?: string;
      clarification?: string;
      candidates?: string[];
    };
    const message = d.message || 'The request could not be completed.';
    switch (d.error) {
      case 'course_resolution_error':
        return new ApiError('course_resolution', message, {
          status,
          needsClarification: Boolean(d.needs_clarification),
          query: d.query,
          clarification: d.clarification,
          candidates: Array.isArray(d.candidates) ? d.candidates : undefined,
        });
      case 'cyclic_dependency_error':
        return new ApiError('cycle', message, { status, cyclePath: d.cycle_path });
      case 'curricular_constraint_error':
        return new ApiError('curricular_constraint', message, {
          status,
          requiredSemesters: d.required_semesters,
          maxSemesters: d.max_semesters,
        });
      case 'ai_service_error':
      case 'ai_configuration_error':
      case 'ai_authentication_error':
      case 'ai_rate_limit_error':
      case 'ai_timeout_error': {
        const isTimeout = d.error === 'ai_timeout_error' || (d as Record<string, unknown>).sub_error === 'AITimeoutError';
        return new ApiError(isTimeout ? 'timeout' : 'ai_service', message, { status });
      }
      case 'learning_path_error':
        return new ApiError('bad_request', message, { status });
      default:
        return new ApiError(
          status >= 500 ? 'server' : 'bad_request',
          status >= 500 ? 'The server encountered an unexpected error.' : message,
          { status }
        );
    }
  }
  if (status === 502 || status === 503 || status === 504) {
    return new ApiError(
      'network',
      'The backend server is offline or unreachable at http://127.0.0.1:8000.',
      { status }
    );
  }
  return new ApiError(
    status >= 500 ? 'server' : 'bad_request',
    `The server responded with status ${status}.`,
    { status }
  );
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...(init.headers ?? {}) },
      signal: controller.signal,
    });
  } catch (err) {
    if ((err as Error).name === 'AbortError') {
      throw new ApiError(
        'timeout',
        `The request took longer than ${Math.round(TIMEOUT_MS / 1000)} seconds. Try again, or turn off AI assistance.`
      );
    }
    throw new ApiError(
      'network',
      'Cannot reach the backend. Check that the FastAPI server is running (e.g. uvicorn backend.core_engine.main:app --port 8000).'
    );
  } finally {
    clearTimeout(timer);
  }

  let body: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }
  if (!res.ok) {
    if (body === null && (res.status === 502 || res.status === 503 || res.status === 504 || res.status === 500)) {
      throw new ApiError(
        'network',
        'Cannot reach the backend service. Check that Uvicorn is active on port 8000.',
        { status: res.status }
      );
    }
    throw toApiError(res.status, body);
  }
  if (body === null) {
    throw new ApiError('invalid_response', 'The backend returned an empty or non-JSON response.', {
      status: res.status,
    });
  }
  return body as T;
}
