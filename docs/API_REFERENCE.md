# Course Registration Assistant API Reference

The Course Registration Assistant provides a high-performance RESTful API built on FastAPI. It provides endpoints for curriculum catalog discovery, health status, cycle detection, and topological prerequisite path generation.

**Base URLs:**
- Local Development: `http://127.0.0.1:8000`
- API Base Path: `/api/v1`

---

## 1. System Health

### `GET /api/v1/health`
Verifies that the backend service and knowledge base are operational.

#### Response (200 OK)
```json
{
  "status": "healthy",
  "service": "daa-course-registration-api",
  "version": "2.0.0"
}
```

---

## 2. Curriculum Courses Catalog

### `GET /api/v1/courses`
Returns all 100 accredited courses from the curriculum knowledge base, complete with canonical IDs, titles, descriptions, difficulty levels, academic semester (1–8), and aliases.

#### Response (200 OK)
```json
[
  {
    "course_id": "programming_fundamentals",
    "name": "Programming Fundamentals",
    "aliases": ["Intro to Programming", "Introduction to Programming"],
    "category": "Programming Fundamentals",
    "difficulty": "beginner",
    "description": "Language-independent basics of programming: variables, control flow, functions, simple data types, and basic problem decomposition.",
    "semester": 1
  },
  {
    "course_id": "data_structures",
    "name": "Data Structures",
    "aliases": ["DSA", "Data Structures & Algorithms I"],
    "category": "Core Computer Science",
    "difficulty": "intermediate",
    "description": "Abstract data types, linear and non-linear data structures: arrays, linked lists, stacks, queues, trees, heaps, and hash tables.",
    "semester": 3
  }
]
```

---

## 3. Generate Course Registration Order

### `POST /api/v1/learning-path`
Accepts a list of selected courses, resolves canonical catalog entities, constructs the induced prerequisite subgraph $G=(V, E)$, runs 3-state DFS cycle detection, and executes Kahn's topological sorting with min-heap tie-breaking.

#### Request Body
```json
{
  "courses": [
    "Design and Analysis of Algorithms",
    "Data Structures",
    "Programming Fundamentals"
  ]
}
```

#### Request Parameters
| Field | Type | Required | Description |
| :--- | :---: | :---: | :--- |
| `courses` | `List[str]` | Yes | Course names, canonical IDs, or alias strings. Min length: 1. |

#### Success Response (200 OK)
```json
{
  "selected_courses": [
    { "course_id": "programming_fundamentals", "name": "Programming Fundamentals" },
    { "course_id": "data_structures", "name": "Data Structures" },
    { "course_id": "design_and_analysis_of_algorithms", "name": "Design and Analysis of Algorithms" }
  ],
  "ordered_courses": [
    { "course_id": "programming_fundamentals", "name": "Programming Fundamentals" },
    { "course_id": "data_structures", "name": "Data Structures" },
    { "course_id": "design_and_analysis_of_algorithms", "name": "Design and Analysis of Algorithms" }
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
      "course_count": 1,
      "courses": [
        { "course_id": "design_and_analysis_of_algorithms", "name": "Design and Analysis of Algorithms" }
      ]
    }
  ],
  "prerequisites": [
    {
      "source_course_id": "programming_fundamentals",
      "target_course_id": "data_structures",
      "relationship_type": "required",
      "explanation": "Programming fundamentals provide syntax and logic needed for data structure implementations.",
      "confidence": 1.0,
      "evidence_type": "expert_curated"
    },
    {
      "source_course_id": "data_structures",
      "target_course_id": "design_and_analysis_of_algorithms",
      "relationship_type": "required",
      "explanation": "Data structures are the foundational primitives required for algorithm design and asymptotic analysis.",
      "confidence": 1.0,
      "evidence_type": "expert_curated"
    }
  ],
  "warnings": []
}
```

---

## 4. Error Responses

Structured JSON error payloads with standard HTTP status codes:

### 400 Bad Request: Unrecognized Course
```json
{
  "detail": {
    "error": "course_resolution_error",
    "message": "'Quantum Baking' is not in the knowledge base catalog. Please choose from the 100 catalog courses.",
    "needs_clarification": false,
    "query": "Quantum Baking",
    "candidates": []
  }
}
```

### 400 Bad Request: Circular Dependency Deadlock Detected
When a circular dependency exists in the selected prerequisites, the 3-state DFS engine isolates the exact cycle path:
```json
{
  "detail": {
    "error": "cyclic_dependency_error",
    "message": "Circular prerequisite dependency detected involving courses: Course A -> Course B -> Course A.",
    "cycle_path": ["course_a", "course_b", "course_a"]
  }
}
```
