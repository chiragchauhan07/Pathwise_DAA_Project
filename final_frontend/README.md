# Pathwise frontend

React 19 + TypeScript + Vite + Tailwind 4. Pages: Planner (form + results), Algorithms, AI.

- Design tokens: `src/styles/design-tokens.css` (palette, radii, fonts). Inter is bundled via `@fontsource-variable/inter`; no CDN.
- API: `POST /api/v1/learning-path` via `src/services/` (unchanged). Base URL: `VITE_API_BASE_URL`; dev/preview proxy `/api` to the backend.
- Results: `src/components/roadmap/` (Summary, CourseRoadmap, SemesterSchedule, RelationshipExplorer, RationalePanel). Graph: `src/components/graph/PrereqGraph.tsx` (custom SVG).
- Errors: `src/components/common/ErrorState.tsx` parses the backend message for unknown/ambiguous courses and suggestions.
- Scripts: `npm run dev`, `npm run build`, `npm run typecheck`, `npm test`.

---

Previous README:

# Pathwise — Frontend

React 19 + TypeScript + Vite frontend for **Pathwise: AI-Assisted, Prerequisite-Aware Course Learning Path Generator** (DAA project). It interfaces with the FastAPI backend (`backend/core_engine/main.py`) to render interactive 3D learning roadmaps, semester schedules, and educational algorithm explainers.

## Prerequisites
- Node.js 18+ (tested on Node 20 & 22) and npm
- The FastAPI backend running (Python 3.12+, `pip install -r requirements.txt`)

## Quick start
```bash
# 1. Start the backend (from the repository root)
uvicorn backend.core_engine.main:app --host 127.0.0.1 --port 8000 --reload

# 2. Start the frontend (from the frontend/ directory)
cd frontend
npm install
npm run dev              # http://localhost:5173
```
Other commands:
- `npm run build`: TypeScript strict check + production build into `dist/`.
- `npm test`: Run Vitest unit tests (9 tests).
- `npm run typecheck`: Run TypeScript compiler check without emitting files.
- `npm run preview`: Preview the production build locally on port 4173.

## Primary Navigation Structure (Three-Tab Application)
- **Home (`/`)**: Main interactive curriculum workspace featuring course selection chips, curated catalog autocomplete, learning goal inputs, AI assistance toggles, curricular constraints (`max_courses_per_semester`, `max_semesters`), and the primary results viewer (3D Roadmap, Semester Schedule, Course Sequence, and Prerequisites & Provenance). Saved roadmaps history is accessible directly via the top drawer.
- **DAA (`/daa`)**: Comprehensive algorithmic inspection page containing an interactive directed graph of the current learning path, relationship table, step-by-step Kahn algorithm demonstration, cycle detection examples, and formal time/space complexity analysis.
- **AI (`/ai`)**: In-depth architecture breakdown of the 10-stage processing pipeline, Knowledge Base schema specifications, Google Gemini proposal generation, proposal validation rules, and fail-safe fallback behaviors.

## API Connection
In local development, the browser sends requests to relative endpoints (`/api/v1/...`). The Vite server proxies `/api` to `VITE_DEV_PROXY_TARGET` (default: `http://127.0.0.1:8000`).

| Variable | Purpose | Default |
|---|---|---|
| `VITE_API_BASE_URL` | Absolute API origin (production without proxy) | empty |
| `VITE_DEV_PROXY_TARGET` | Where Vite forwards `/api` in development | `http://127.0.0.1:8000` |
| `VITE_API_TIMEOUT_MS` | API request timeout in milliseconds | `45000` |

## Verified Backend Contract
- **Endpoint:** `POST /api/v1/learning-path`
- **Request Body:**
  ```json
  {
    "courses": ["string"],
    "learning_goal": "string (optional)",
    "use_ai": true,
    "fallback_on_ai_failure": true,
    "max_courses_per_semester": 3,
    "max_semesters": 4
  }
  ```
- **Response Structure:**
  - `learning_goal`: string
  - `selected_courses`: Course[] (canonical details, difficulty, category)
  - `ordered_courses`: Course[] (Kahn topological order)
  - `semesters`: SemesterGroup[] (`semester_number`, `courses`, `course_count`)
  - `prerequisites`: PrerequisiteRecord[] (`source_course_id`, `target_course_id`, `relationship_type`, `explanation`, `source`, `is_ai_proposed`, `confidence`, `evidence_type`)
  - `ai_proposals_used`: boolean
  - `warnings`: string[]
- **Typed Error Handling:**
  - `400 {detail: {error: "course_resolution_error", message}}`
  - `400 {detail: {error: "cyclic_dependency_error", message, cycle_path: []}}`
  - `400 {detail: {error: "curricular_constraint_error", message, required_semesters, max_semesters}}`
  - `502 {detail: {error: "ai_service_error", message}}`
  - `422` FastAPI input validation errors
  - `500 {detail: {error: "internal_error", message}}`

## Design System
- Styled using Tailwind CSS v4 design tokens in `src/styles/design-tokens.css` with a scholarly, high-precision aesthetic.
- Color palette: Crisp warm-white background (`#fbfcfd`), pure white surface (`#ffffff`), deep slate ink typography (`#0f172a`), refined deep teal accent (`#0f766e`), and subtle neutral borders (`#e2e8f0`).
