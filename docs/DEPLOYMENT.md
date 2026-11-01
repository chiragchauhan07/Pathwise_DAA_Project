# Pathwise Deployment Guide: Vercel & Production

This guide provides end-to-end instructions for deploying Pathwise on [Vercel](https://vercel.com). Pathwise is architected to deploy either as a **Unified Full-Stack Deployment** or a **Separated Frontend + Serverless API Deployment**.

---

## 1. Architecture Options on Vercel

### Option A: Unified Full-Stack Deployment (Recommended)
In this setup, Vercel hosts both the React/Vite frontend static assets and the FastAPI backend via Vercel's Python Serverless Runtime `@vercel/python`.

- **Root Directory:** Repository root (`.`)
- **Frontend Assets:** Built by Vite to `final_frontend/dist/`
- **Serverless API Function:** Executed from `api/index.py` which mounts the FastAPI app from `backend/core_engine/main.py`.
- **Routing:** Governed by root `vercel.json`:
  - Directs `/api/(.*)` requests to `api/index.py`.
  - Serves static assets from `final_frontend/dist` for all other routes.

### Option B: Separated Frontend Deployment
Deploy only the static React application on Vercel Edge Network, pointing to a dedicated backend host (e.g. Railway, Render, or another Vercel Python project).

- **Root Directory in Vercel Settings:** `final_frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Environment Variable:** Set `VITE_API_BASE_URL` to your backend's public URL (e.g. `https://pathwise-api.example.com`).

---

## 2. Step-by-Step Vercel Deployment Instructions

### Step 1: Connect Your GitHub Repository
1. Log in to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **"Add New..."** $\to$ **"Project"**.
3. Import the repository: `chiragchauhan07/Pathwise_DAA_Project`.

### Step 2: Configure Build & Development Settings
For **Option A (Unified Full-Stack)**:
- **Framework Preset:** Vite (or Other)
- **Root Directory:** `./` (Leave as default project root)
- **Build Command:** `npm --prefix final_frontend run build`
- **Output Directory:** `final_frontend/dist`
- **Install Command:** `npm --prefix final_frontend install`

### Step 3: Configure Environment Variables
In the Vercel Project Settings under **Environment Variables**, configure the following:

| Variable Name | Environment | Value Description | Example |
| :--- | :---: | :--- | :--- |
| `GEMINI_API_KEY` | Production, Preview | Google Gemini API Key | `AIzaSy...` (from Google AI Studio) |
| `GEMINI_MODEL` | Production, Preview | Target Gemini model | `gemini-2.5-flash-lite` |
| `CORS_ORIGINS` | Production, Preview | Allowed origins for CORS | `https://*.vercel.app,http://localhost:5173` |
| `PYTHONPATH` | Production, Preview | Path for Python module discovery | `.` |

> [!CAUTION]
> **Never commit your `.env` file to GitHub.** Add your `GEMINI_API_KEY` only through the encrypted Vercel Project Dashboard.

### Step 4: Deploy
Click **"Deploy"**. Vercel will install dependencies, compile the TypeScript frontend, build the Python serverless function package, and provide a live URL.

---

## 3. Configuration Files Breakdown

### Root `vercel.json` (Serverless API + Frontend Proxy)
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "final_frontend/package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
      }
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "api/index.py"
    },
    {
      "handle": "filesystem"
    },
    {
      "src": "/(.*)",
      "dest": "final_frontend/$1"
    }
  ]
}
```

### Serverless Entrypoint: `api/index.py`
```python
import sys
from pathlib import Path

# Ensure root repository directory is in Python path for Vercel Serverless
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.core_engine.main import app
```

---

## 4. Production Checklist & Verification

Once deployed, verify the deployment:

1. **Test Backend Health Endpoint:**
   ```bash
   curl -s https://<your-vercel-domain>.vercel.app/api/v1/health
   # Expected: {"status":"healthy","service":"Pathwise DAA Learning Path API","version":"1.0.0"}
   ```
2. **Test AI Engine Status:**
   ```bash
   curl -s https://<your-vercel-domain>.vercel.app/api/v1/ai/status
   # Confirms Gemini client is configured and initialized
   ```
3. **Verify Course Catalog:**
   ```bash
   curl -s https://<your-vercel-domain>.vercel.app/api/v1/courses | jq length
   # Expected: 70
   ```
4. **Test Frontend UI:**
   - Open `https://<your-vercel-domain>.vercel.app` in a browser.
   - Select the preset **"Machine Learning Engineer"**.
   - Click **"Generate Path"**.
   - Verify that topological ordering, semester grid, and Mermaid-style prerequisite graph render instantly.

---

## 5. Troubleshooting

- **500 Internal Server Error on `/api/*`:** Check Vercel Function Runtime logs. Ensure `requirements.txt` contains `google-genai`, `fastapi`, `pydantic`, `uvicorn`.
- **404 Not Found on API routes:** Verify that requests are hitting `/api/v1/...` and that the Vercel routing rule matches `/api/(.*)`.
- **CORS Issues:** Add your custom domain to `CORS_ORIGINS` in Vercel project environment variables.
- **Python Import Errors:** Ensure `PYTHONPATH=.` is set or that `api/index.py` inserts root path into `sys.path`.
