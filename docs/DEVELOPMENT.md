# Local Development Guide

This guide walks you through setting up, running, and testing the Dependency-Aware Course Registration Assistant on your local development machine.

---

## 1. System Requirements

- **Python:** 3.10+ (CPython recommended)
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
*(No API keys or external secrets are required; the application runs completely deterministically using the built-in curriculum knowledge base).*

---

## 3. Running Locally

### Option 1: Automated Start Script (Windows PowerShell)
```powershell
.\start_pathwise.ps1
```

### Option 2: Running Services Manually in Separate Terminals

#### Terminal 1 — Backend API (FastAPI):
```bash
python -m uvicorn backend.core_engine.main:app --reload --host 127.0.0.1 --port 8000
```
- API URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

#### Terminal 2 — Frontend Application (Vite):
```bash
cd final_frontend
npm run dev
```
- Frontend application URL: `http://localhost:5173`

---

## 4. Running the Verification & Test Suites

The project includes an automated test suite covering pure DAA graph algorithms, cycle detection, FastAPI endpoints, knowledge base consistency, and frontend components.

### 4.1 Knowledge Base Validation
Validates the 100 courses, 136 prerequisite edges, category taxonomy, and acyclicity of the curated curriculum:
```bash
python backend/knowledge_base/validate_kb_by_Claude.py
```

### 4.2 Backend Unit & Integration Tests (118 tests)
Runs the entire pytest suite:
```bash
pytest
```
Or run specific test modules:
```bash
pytest tests/test_daa_engine.py -v         # Pure DAA graph algorithms
pytest tests/test_scenarios_e2e.py -v      # Real-world registration journeys
pytest tests/test_knowledge_base.py -v     # Knowledge base validation tests
```

### 4.3 Frontend Verification & Build Check
```bash
# Typecheck TypeScript codebase
node final_frontend/node_modules/typescript/bin/tsc -b

# Production build test
node final_frontend/node_modules/vite/bin/vite.js build
```

---

## 5. Pre-Commit Checklist

Before submitting a Pull Request or pushing changes:
1. [ ] Knowledge base validates: `python backend/knowledge_base/validate_kb_by_Claude.py`
2. [ ] All 118 backend tests pass: `pytest`
3. [ ] Frontend builds cleanly: `npm --prefix final_frontend run build`
4. [ ] Zero secrets or `.env` files in git status: `git status`
