# Project Context: AI-Assisted, Prerequisite-Aware Course Learning Path Generator

## 1. Project Objective
The project builds an intelligent course learning path generator for a college Design and Analysis of Algorithms (DAA) project. Students input a list of courses and an optional learning goal (e.g., AI Engineer, Data Scientist). The system determines prerequisite relationships, combines curated knowledge with AI recommendations, builds a directed graph, validates structural constraints, detects cycles, and computes an explainable, topologically sorted learning sequence.

## 2. Core Architectural Principles
* **Separation of Concerns:** Algorithmic validation and ordering are strictly isolated from AI inference and data storage.
* **DAA Logic Integrity:** Graph construction, cycle detection, and topological sorting are explicitly implemented in Python (without third-party graph frameworks like NetworkX) inside the DAA Logic Engine.
* **AI Engine Role:** Google Gemini proposes potential prerequisite relationships and provides educational justifications; it is never an authoritative source of graph order or final sequencing.
* **Knowledge Base Role:** Serves reviewed curricular dependencies and alias mappings from curated JSON files (`courses.json`).
* **Explainability & Provenance:** The system differentiates between required prerequisites and recommended/optional courses, exposes relationship provenance (`curated` vs `ai_proposed`), and flags structural cycles rather than silently dropping edges.

## 3. Architectural Boundaries
1. **Core Backend Engine (`backend/core_engine/`):** FastAPI initialization, routing, request/response schemas, end-to-end learning path orchestration (`analysis_service.py`), and error handling.
2. **AI Engine (`backend/ai_engine/`):** Google Gemini SDK (`google-genai`), timeout converter (seconds to SDK milliseconds), prompt engineering, structured schema validation, timeout enforcement, rate-limit handling, and graceful fallback. Default model: `gemini-3.8-flash`.
3. **DAA Logic Engine (`backend/daa_engine/`):** Adjacency list representation, Kahn's algorithm with min-heap determinism, DFS traversal, 3-state cycle detection, and order verification.
4. **Knowledge Base (`backend/knowledge_base/`):** Curated JSON course catalog (35 courses, 59 relationships), alias normalization, and reviewed prerequisite definitions.
5. **Frontend (`frontend/`):** Dedicated UI for course selection, interactive graph rendering, and learning sequence display (deferred to Level 8).

## 4. Technology Stack
* **Language & Runtime:** Python 3.12+
* **API Framework:** FastAPI, Uvicorn
* **AI Provider:** Google Gemini via official `google-genai` SDK (default model: `gemini-3.8-flash`)
* **Data Validation:** Pydantic
* **Testing:** Pytest, HTTPX
* **Storage:** JSON-based structured files (`courses.json`)

## 5. Current Status & Implemented Capabilities
* **Stage:** LEVEL 7 Completed (Pedagogical Optimization, Wave Partitioning, and Curricular Constraints).
* **Capabilities:**
  * Clean directory structure with strictly separated architectural boundaries.
  * FastAPI application with `/`, `/api/v1/health`, and `/api/v1/learning-path` routes.
  * Curated Knowledge Base catalog (`backend/knowledge_base/courses.json`) with exactly 35 courses and 59 reviewed relationships.
  * Hardened Knowledge Base validator (`backend/knowledge_base/validate_kb_by_Claude.py`) with type-safe checks, boolean confidence rejection, and cycle validation.
  * Course resolution module (`backend/knowledge_base/knowledge_base.py`) supporting canonical lookup, aliases, normalization, and ambiguity detection.
  * Custom DAA Logic Engine (`backend/daa_engine/`):
    * Explicit adjacency-list `DirectedGraph` with edge convention (prerequisite -> dependent) and duplicate edge protection.
    * Kahn's algorithm with min-heap deterministic tie-breaking by canonical course ID ($O((V+E)\log V)$ time).
    * Iterative 3-state DFS cycle detection with exact cycle path reconstruction ($O(V \log V + E)$ time).
    * DFS-based topological sorting ($O(V \log V + E)$ time).
    * Accurate Kahn cycle reporting isolating true cycle members from downstream blocked nodes.
    * Topological ordering verifier asserting prerequisite-before-dependent correctness ($O(V \log V + E)$ time, $O(V + E)$ peak space).
    * Pedagogical course scheduler (`scheduler.py`):
      * Natural wave-based DAG layering for unconstrained study wave assignments.
      * Workload-constrained multi-priority list scheduling (`max_courses_per_semester`).
      * Deadline feasibility bounds checking against maximum allowed terms (`max_semesters`).
      * Difficulty progression smoothing (`beginner` < `intermediate` < `advanced`).
      * Hard vs. soft relationship differentiation (required prerequisites enforce sequential terms; recommended/optional allow concurrent terms).
      * Formal mathematical schedule verifier asserting course uniqueness, precedence, and capacity.
  * Custom AI Engine with Google Gemini (`backend/ai_engine/client.py`):
    * Google Gen AI client integration with environment-variable credentials (`GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_TIMEOUT`).
    * Timeout unit conversion: Configured in seconds, converted to integer milliseconds for SDK `types.HttpOptions`. Rejects non-numeric, zero, negative, NaN, or infinite timeout values with descriptive `ValueError`.
    * Default model `gemini-3.8-flash` selected based on Google AI Studio's current documentation for new projects on the free tier.
    * Targeted prompt builder requesting only missing prerequisite proposals in strict JSON format.
    * Comprehensive schema validator checking course ID membership, direction, relationship type, non-boolean confidence, self-reference prevention, duplicate elimination, and KB-overlap exclusion.
    * Robust exception handling mapping auth errors, rate limits, timeouts, connection issues, and validation failures.
  * End-to-End Learning Path Orchestration (`backend/core_engine/analysis_service.py`):
    * Canonical course ID resolution with alias mapping and error aggregation.
    * Single-course skip: Queries Gemini only when $\ge 2$ distinct courses are selected; single courses return an informative warning without API overhead.
    * Precise `ai_proposals_used`: Sets flag to `true` strictly when at least one valid AI proposal is incorporated; `false` when proposals are empty, skipped, or fallback is engaged.
    * Relationship provenance: Exposes `source`, `is_ai_proposed`, `confidence`, and `evidence_type` for every relationship in the learning path.
    * In-memory merging of curated KB prerequisites with validated Gemini proposals (leaving `courses.json` immutable).
    * Cycle detection before topological ordering, raising explicit `CycleConflictError` on loops.
    * Deterministic linear learning path and wave/semester schedule mathematically verified against all edges and constraints.
    * Safe fallback to curated KB relationships when AI is unavailable or fails.
  * Comprehensive automated test suite (117 tests) covering core engine, knowledge base, DAA engine (including edge cases, deep recursion, disconnected components with cycles, pedagogical scheduler), AI engine, and end-to-end integration with 100% mocked offline execution.
  * Dedicated, reproducible DAA performance benchmark suite (`benchmarks/benchmark_daa.py`) evaluating 5 graph topologies up to V=1000 with pre-timing correctness gates.

## 6. Known Limitations
* Curricular institutional offerings (Fall/Spring specific terms) and credit unit balances are deferred as the current catalog contains difficulty ratings rather than credit units.
* Full-stack web frontend and interactive graph visualization are scheduled for Level 8.
