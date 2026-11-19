# Course Registration Assistant — Frontend

React 19 + TypeScript + Vite + Tailwind CSS v4 frontend for the **Dependency-Aware Course Registration Assistant** (PBL DAA project). It interfaces with the FastAPI backend (`backend/core_engine/main.py`) to render interactive learning roadmaps, semester schedules, and educational algorithm explainers.

## Navigation Structure
- **Home (`/`)**: Main interactive curriculum registration planner. Allows students to select from 100 accredited catalog courses or choose from preset tracks (*CS Core*, *AI & ML*, *Software Systems*, *Core DAA Track*), computing and rendering the topological course sequence, semester waves, and the dedicated educational banner on reliable degree planning.
- **DAA Theory (`/daa`)**: Comprehensive algorithmic inspection page containing an interactive directed graph, 6-node DAG trace diagram with initial in-degrees, step-by-step Kahn algorithm demonstration, cycle detection examples, and formal time/space complexity analysis.
- **Course Catalog (`/curriculum`)**: Searchable and filterable catalog explorer containing all 100 courses and 136 prerequisite relationships, complete with unified "Filter and Sort" options (filtering by semester 1–8, category, and difficulty, and sorting alphabetically, by semester, or by difficulty).

## Prerequisites
- Node.js 18+ and npm
- FastAPI backend running (`python -m uvicorn backend.core_engine.main:app --port 8000`)

## Development Scripts
```bash
npm run dev              # Starts local Vite development server on http://localhost:5173
npm run build            # TypeScript check (tsc -b) + production build into dist/
npm run typecheck        # Runs TypeScript compiler check without emitting files
npm test                 # Runs frontend test suite
npm run preview          # Previews the production build locally on port 4173
```

## API Connection
In development, the browser sends requests to relative endpoints (`/api/v1/...`). The Vite server proxies `/api` to `VITE_DEV_PROXY_TARGET` (default: `http://127.0.0.1:8000`).

| Variable | Purpose | Default |
|---|---|---|
| `VITE_API_BASE_URL` | Absolute API origin (production without proxy) | empty |
| `VITE_DEV_PROXY_TARGET` | Where Vite forwards `/api` in development | `http://127.0.0.1:8000` |
| `VITE_API_TIMEOUT_MS` | API request timeout in milliseconds | `15000` |

## Verified Backend Contract
- **Endpoint:** `POST /api/v1/learning-path`
- **Request Body:**
  ```json
  {
    "courses": ["Programming Fundamentals", "Data Structures", "Design and Analysis of Algorithms"]
  }
  ```
- **Response Structure:**
  - `selected_courses`: Course[] (canonical IDs, names, difficulty, category)
  - `ordered_courses`: Course[] (Kahn topological order)
  - `semesters`: SemesterGroup[] (`semester_number`, `courses`, `course_count`)
  - `prerequisites`: PrerequisiteRecord[] (`source_course_id`, `target_course_id`, `relationship_type`, `explanation`, `confidence`)
  - `warnings`: string[]
- **Typed Error Handling:**
  - `400 {detail: {error: "course_resolution_error", message, query}}`
  - `400 {detail: {error: "cyclic_dependency_error", message, cycle_path: [...]}}`

## Design System
- Styled using Tailwind CSS v4 design tokens in `src/styles/design-tokens.css` with a scholarly, high-precision aesthetic.
- Color palette: Crisp warm-white background (`#fbfcfd`), pure white surface (`#ffffff`), deep slate ink typography (`#0f172a`), refined teal accent (`#0f766e`), and subtle neutral borders (`#e2e8f0`).
