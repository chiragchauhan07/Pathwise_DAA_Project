# Project Context: Dependency-Aware Course Registration Assistant

## 1. Project Objective
Build a deterministic, graph-theoretic course registration assistant for the Design and Analysis of Algorithms (DAA) Problem-Based Learning (PBL 2) curriculum at Manav Rachna International Institute of Research and Studies (MRIIRS).
The tool represents university course prerequisites as a directed graph, detects circular prerequisite deadlocks using 3-state DFS, generates valid course-taking sequences using Kahn's topological sort with min-heap tie-breaking, and demonstrates how topological ordering guarantees reliable academic degree planning.

## 2. Core Architectural Principles
* **Pure DAA Engine Integrity:** Graph construction, in-degree calculation, 3-state DFS cycle detection, Kahn's topological sorting, and semester wave partitioning are explicitly implemented in pure Python (without third-party graph frameworks like NetworkX) inside `backend/daa_engine/`.
* **Curriculum Knowledge Base:** Represents an accredited undergraduate B.Tech Computer Science and Engineering curriculum containing exactly 100 courses and 136 verified prerequisite relationships spanning Semesters 1 through 8 (`courses.json`).
* **Deterministic Tie-Breaking:** Min-heap priority queues guarantee that identical course selections produce identical, mathematically reproducible registration orders.
* **Explainable Planning:** The system isolates the exact cycle path ($A \to B \to A$) upon cycle detection and provides clear educational explanations of prerequisite precedence, deadlock immunity, and concurrent semester waves.

## 3. Technology Stack
* **Backend:** Python 3.10+, FastAPI, Pydantic, Uvicorn.
* **DAA Engine:** Pure Python (`graph.py`, `scheduler.py`).
* **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4.
* **Testing:** Pytest (118 unit, integration, and scenario tests).
