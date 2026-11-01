# Pathwise API Reference

Pathwise provides a high-performance RESTful API built on FastAPI. It provides endpoints for course discovery, AI status telemetry, and topological prerequisite path generation.

**Base URLs:**
- Local Development: `http://localhost:8000`
- Production / Vercel Serverless: `/api/v1` (or direct origin URL)

---

## 1. System Health

### `GET /api/v1/health`
Verifies that the backend service is operational.

#### Response (200 OK)
```json
{
  "status": "healthy",
  "service": "Pathwise DAA Learning Path API",
  "version": "1.0.0"
}
```

---

## 2. Curated Courses Catalog

### `GET /api/v1/courses`
Returns all 70 expert-curated courses from the knowledge base, complete with canonical IDs, descriptions, credits, difficulty scores, categories, and direct prerequisites.

#### Response (200 OK)
```json
[
  {
    "course_id": "programming_fundamentals",
    "name": "Programming Fundamentals",
    "description": "Core concepts of procedural programming, variables, control flow, functions, and structured problem-solving.",
    "category": "core_cs",
    "difficulty": 1,
    "credits": 4,
    "prerequisites": []
  },
  {
    "course_id": "data_structures",
    "name": "Data Structures",
    "description": "Arrays, linked lists, stacks, queues, trees, hash tables, heaps, and algorithmic runtime complexity.",
    "category": "core_cs",
    "difficulty": 2,
    "credits": 4,
    "prerequisites": ["programming_fundamentals"]
  }
]
```

---

## 3. AI Engine Status

### `GET /api/v1/ai/status`
Reports the runtime configuration, model specification, and initialization readiness of the Google Gemini integration without exposing secret keys.

#### Response (200 OK)
```json
{
  "configured": true,
  "key_present": true,
  "key_empty": false,
  "key_source": "env:GEMINI_API_KEY",
  "model": "gemini-2.5-flash-lite",
  "timeout_seconds": 15.0,
  "max_retries": 2,
  "client_initializable": true,
  "error": null
}
```

---

## 4. Generate Learning Path

### `POST /api/v1/learning-path`
Accepts a list of courses and user learning goals, resolves canonical entities, detects cycles, runs Kahn's topological sort with min-heap tie-breaking, and schedules courses into semester buckets.

#### Request Body
```json
{
  "courses": [
    "Design and Analysis of Algorithms",
    "Machine Learning",
    "Programming Fundamentals"
  ],
  "learning_goal": "Master foundational CS and AI algorithms",
  "use_ai": true,
  "fallback_on_ai_failure": true,
  "max_courses_per_semester": 2,
  "max_semesters": 4
}
```

#### Request Parameters
| Field | Type | Required | Default | Description |
| :--- | :---: | :---: | :---: | :--- |
| `courses` | `List[str]` | Yes | — | Course names, canonical IDs, or fuzzy query strings. Min length: 1. |
| `learning_goal` | `str` | No | `"General Computer Science"` | Contextual objective used by Gemini to resolve ambiguous course names. |
| `use_ai` | `bool` | No | `true` | When true, queries Gemini 2.5 Flash Lite for prerequisite proposals and unknown course resolution. |
| `fallback_on_ai_failure` | `bool` | No | `true` | If true, falls back to the curated knowledge base if Gemini is unreachable or returns invalid data. |
| `max_courses_per_semester`| `int` | No | `null` | Maximum course workload permitted per semester (must be $\ge 1$). |
| `max_semesters` | `int` | No | `null` | Hard ceiling on allowed semesters (must be $\ge 1$). |

#### Success Response (200 OK)
```json
{
  "learning_goal": "Master foundational CS and AI algorithms",
  "selected_courses": [
    { "course_id": "programming_fundamentals", "name": "Programming Fundamentals" },
    { "course_id": "design_and_analysis_of_algorithms", "name": "Design and Analysis of Algorithms" },
    { "course_id": "machine_learning", "name": "Machine Learning" }
  ],
  "ordered_courses": [
    { "course_id": "programming_fundamentals", "name": "Programming Fundamentals" },
    { "course_id": "data_structures", "name": "Data Structures" },
    { "course_id": "design_and_analysis_of_algorithms", "name": "Design and Analysis of Algorithms" },
    { "course_id": "machine_learning", "name": "Machine Learning" }
  ],
  "semesters": [
    {
      "semester_number": 1,
      "course_count": 1,
      "courses": [
        { "course_id": "programming_fundamentals", "name": "Programming Fundamentals" }
      ]
    },
    {
      "semester_number": 2,
      "course_count": 1,
      "courses": [
        { "course_id": "data_structures", "name": "Data Structures" }
      ]
    },
    {
      "semester_number": 3,
      "course_count": 2,
      "courses": [
        { "course_id": "design_and_analysis_of_algorithms", "name": "Design and Analysis of Algorithms" },
        { "course_id": "machine_learning", "name": "Machine Learning" }
      ]
    }
  ],
  "prerequisites": [
    {
      "source_course_id": "programming_fundamentals",
      "target_course_id": "data_structures",
      "relationship_type": "hard_prerequisite",
      "explanation": "Core programming required before abstract structures.",
      "source": "curated",
      "is_ai_proposed": false,
      "confidence": 1.0,
      "evidence_type": "expert_curated"
    }
  ],
  "ai_proposals_used": false,
  "warnings": [],
  "ai_summary": {
    "requested": true,
    "course_resolution_status": "curated_only",
    "unknown_courses_evaluated": 0,
    "ambiguous_courses_evaluated": 0,
    "proposal_request_status": "succeeded",
    "proposals_received": 0,
    "proposals_accepted": 0,
    "proposals_rejected": 0,
    "relationships_added": 0,
    "model": "gemini-2.5-flash-lite",
    "message": "Curated knowledge base relationships used."
  }
}
```

---

## 5. Error Responses

Pathwise returns structured JSON error payloads with standard HTTP status codes:

### 400 Bad Request: Ambiguous / Unresolvable Course
```json
{
  "detail": {
    "error": "course_resolution_error",
    "message": "Course query 'English' is ambiguous. Please select a specific academic course.",
    "needs_clarification": true,
    "query": "English",
    "clarification": "The query could refer to multiple distinct subjects.",
    "candidates": ["Technical Writing", "Academic Composition", "Literature"]
  }
}
```

### 400 Bad Request: Circular Dependency Detected
```json
{
  "detail": {
    "error": "cyclic_dependency_error",
    "message": "Circular prerequisite dependency detected involving courses: Course A -> Course B -> Course A.",
    "cycle_path": ["course_a", "course_b", "course_a"]
  }
}
```

### 400 Bad Request: Curricular Constraint Violation
```json
{
  "detail": {
    "error": "curricular_constraint_error",
    "message": "Path requires 5 semesters to satisfy prerequisite chains, but max_semesters is set to 3.",
    "required_semesters": 5,
    "max_semesters": 3
  }
}
```

### 502 Bad Gateway: AI Service Error (When `fallback_on_ai_failure=false`)
```json
{
  "detail": {
    "error": "ai_service_error",
    "sub_error": "AIRateLimitError",
    "message": "Gemini API rate limit exceeded. Please retry shortly."
  }
}
```
