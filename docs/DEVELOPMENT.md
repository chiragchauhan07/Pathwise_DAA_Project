# Pathwise Local Development Guide

This guide walks you through setting up, running, and testing Pathwise on your local development machine.

---

## 1. System Requirements

- **Python:** 3.10, 3.11, or 3.12 (CPython recommended)
- **Node.js:** 18.x or 20.x+ with `npm`
- **Git:** 2.30+
- **Operating System:** Windows 10/11, macOS, or Linux

---

## 2. Environment Setup

### 2.1 Clone the Repository
```bash
git clone https://github.com/chiragchauhan07/Pathwise_DAA_Project.git
cd Pathwise_DAA_Project
```

### 2.2 Backend Environment Setup

#### Windows (PowerShell):
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### macOS / Linux (Bash):
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.3 Frontend Setup
```bash
cd final_frontend
npm install
cd ..
```

### 2.4 Environment Configuration (`.env`)
Copy the example environment template:
```bash
cp .env.example .env
```
Edit `.env` and add your Google Gemini API key:
```env
GEMINI_API_KEY=your_actual_api_key_from_google_ai_studio
GEMINI_MODEL=gemini-2.5-flash-lite
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173
```
> [!NOTE]
> If you do not have a Gemini API key immediately, the backend operates normally using the curated knowledge base of 70 courses and 115 prerequisite relationships.

---

## 3. Running Pathwise Locally

### Option 1: Automated Start Script (Windows PowerShell)
Pathwise includes a convenient launch script:
```powershell
.\start_pathwise.ps1
```

### Option 2: Running Services Manually in Separate Terminals

#### Terminal 1 — Backend API (FastAPI):
```bash
# Ensure venv is active
uvicorn backend.core_engine.main:app --reload --host 127.0.0.1 --port 8000
```
- API will be accessible at: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

#### Terminal 2 — Frontend Application (Vite):
```bash
cd final_frontend
npm run dev
```
- Frontend application will be accessible at: `http://localhost:5173`

---

## 4. Running the Verification & Test Suites

Pathwise includes a test suite covering pure DAA graph algorithms, AI integration with graceful degradation, FastAPI endpoints, knowledge base consistency, and frontend components.

### 4.1 Knowledge Base Validation
Validates the 70 courses, 115 prerequisite edges, category taxonomy, and acyclicity of the curated curriculum:
```bash
python backend/knowledge_base/validate_kb_by_Claude.py
```

### 4.2 Backend Unit & Integration Tests (204 tests)
Runs the entire pytest suite:
```bash
pytest
```
Or run specific test modules:
```bash
pytest tests/test_daa_engine.py -v         # Pure DAA graph algorithms
pytest tests/test_ai_pipeline.py -v        # AI pipeline & disambiguation
pytest tests/test_scenarios_e2e.py -v      # 14 Real-world user journeys
pytest tests/test_learning_path.py -v      # End-to-end path generation
```

### 4.3 DAA Empirical Benchmarks
Measures execution times of Kahn's algorithm, DFS cycle detection, and verification across Sparse, Dense, Linear, Disconnected, and Cyclic graphs up to $V=1000$ and $E=49,950$:
```bash
python benchmarks/benchmark_daa.py
```

### 4.4 Frontend Tests & Typecheck
```bash
# Typecheck TypeScript codebase
npm --prefix final_frontend run typecheck

# Run Vitest suite
npm --prefix final_frontend test

# Test production build
npm --prefix final_frontend run build
```

---

## 5. Pre-Release / Pre-Commit Checklist

Before submitting a Pull Request or pushing changes:
1. [ ] Knowledge base validates: `python backend/knowledge_base/validate_kb_by_Claude.py`
2. [ ] All 204 backend tests pass: `pytest`
3. [ ] DAA benchmarks pass with zero failures: `python benchmarks/benchmark_daa.py`
4. [ ] Frontend builds cleanly: `npm --prefix final_frontend run build`
5. [ ] Frontend typechecks: `npm --prefix final_frontend run typecheck`
6. [ ] Zero secrets or `.env` files in git status: `git status`
