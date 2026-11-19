# Development Context: Dependency-Aware Course Registration Assistant

## 1. Current State
* **Status:** Finalized & Verified.
* **Architecture:** Pure DAA Graph Algorithm Engine + Fast React 19 Frontend.

## 2. Completed Architecture & Milestones
* **Curriculum Knowledge Base:** Expanded to 100 accredited courses and 136 validated prerequisite relationships across Semesters 1 through 8 directly from the official MRIIRS B.Tech Computer Science and Engineering syllabus scheme (`courses.json` and `coursesCatalog.ts`).
* **DAA Graph Logic Engine (`backend/daa_engine/`):**
  * `DirectedGraph` in `graph.py` with adjacency list and in-degree tracking.
  * Deterministic `topological_sort_kahn` using `heapq` priority min-heap ($\mathcal{O}(|E| + |V| \log |V|)$ time).
  * Iterative `detect_cycle_dfs` using 3-state vertex coloring (White, Gray, Black) ($\mathcal{O}(|V| + |E|)$ time) with explicit call stack preventing recursion depth exhaustion.
  * Precedence verification barrier (`verify_topological_order`).
  * Wave-based semester partitioning (`schedule_courses`).
* **API Service Layer (`backend/core_engine/`):**
  * Clean, minimal FastAPI service with endpoints: `GET /api/v1/health`, `GET /api/v1/courses`, `POST /api/v1/learning-path`.
  * Zero external API keys or cloud service dependencies.
* **Frontend (`final_frontend/`):**
  * Responsive road-style visualization with React 19, TypeScript, and Tailwind CSS v4.
  * Searchable and filterable Course Catalog with unified "Filter and Sort" (Semesters 1–8, categories, difficulty).
  * DAA Theory page with inline 6-node DAG SVG trace diagram, Kahn's algorithm demo, and educational analysis of reliable planning.
  * Results view with dedicated educational card on how topological ordering supports reliable academic planning.
* **Verification:** 118/118 automated pytest tests passing; TypeScript and Vite builds clean with 0 errors.
