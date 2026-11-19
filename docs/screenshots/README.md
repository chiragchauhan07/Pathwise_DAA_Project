# Screenshots & Visual Gallery

This directory documents the visual captures of the Dependency-Aware Course Registration Assistant application.

---

## 1. Primary User Journey Views

### 1.1 Course Selection & Curricular Tracks
* **Route:** `/`
* **Description:** Students can search and select from 100 accredited curriculum courses across Semesters 1 through 8 or pick curricular track presets such as *CS Core*, *AI & ML*, *Software Systems*, or *Core DAA Track*.

### 1.2 Prerequisite-Aware Roadmap & Semester Waves
* **Route:** `/` (upon clicking "Generate Registration Order")
* **Description:** Generated sequence showing the topological order derived from Kahn's algorithm, partitioned into concurrent semester waves, complete with the dedicated educational callout explaining how topological ordering guarantees reliable degree planning.

### 1.3 Step-by-Step DAA Algorithm Inspector
* **Route:** `/daa`
* **Description:** Visual representation of the Directed Acyclic Graph (DAG), inline 6-node trace diagram with initial in-degrees, interactive step-by-step Kahn's in-degree transitions, queue states, and the comparative analysis of reliable topological planning versus ad-hoc scheduling.

### 1.4 Academic Course Catalog Explorer
* **Route:** `/curriculum`
* **Description:** Expandable catalog explorer containing all 100 courses and 136 prerequisite relationships, complete with unified "Filter and Sort" options (filtering by semester 1–8, category, and difficulty, and sorting alphabetically, by semester, or by difficulty).
