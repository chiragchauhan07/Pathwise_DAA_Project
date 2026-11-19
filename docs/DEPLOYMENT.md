# Production Deployment Guide: Vercel

This guide provides instructions for deploying the Dependency-Aware Course Registration Assistant on [Vercel](https://vercel.com). The project uses a **Unified Full-Stack Deployment** with zero external API key requirements.

---

## 1. Architecture on Vercel

In this setup, Vercel hosts both the React/Vite frontend static assets and the FastAPI backend via Vercel's Python Serverless Runtime (`@vercel/python`).

- **Root Directory:** Repository root (`.`)
- **Frontend Assets:** Built by Vite to `final_frontend/dist/`
- **Serverless API Function:** Executed on-demand from `api/index.py` which mounts the FastAPI app from `backend/core_engine/main.py`.
- **Routing:** Governed by root `vercel.json`:
  - Directs `/api/(.*)` requests to `api/index.py`.
  - Serves static assets from `final_frontend/dist` for all other routes.
- **Zero API Keys Required:** Operates 100% deterministically using the built-in 100-course curriculum knowledge base.

---

## 2. Step-by-Step Vercel Deployment Instructions

### Step 1: Connect Your GitHub Repository
1. Log in to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **"Add New..."** $\to$ **"Project"**.
3. Import the repository: `chiragchauhan07/Pathwise_DAA_Project`.

### Step 2: Configure Build & Development Settings
- **Framework Preset:** Vite (or Other)
- **Root Directory:** `./` (Leave as default project root)
- **Build Command:** `npm --prefix final_frontend run build`
- **Output Directory:** `final_frontend/dist`
- **Install Command:** `npm --prefix final_frontend install`

### Step 3: Configure Environment Variables
No secrets or API keys are required. You may optionally configure:

| Variable Name | Environment | Value Description | Example |
| :--- | :---: | :--- | :--- |
| `CORS_ORIGINS` | Production, Preview | Allowed origins for CORS | `*` |
| `PYTHONPATH` | Production, Preview | Path for Python module discovery | `.` |

### Step 4: Deploy
Click **"Deploy"**. Vercel will install dependencies, compile the TypeScript frontend, configure the Python serverless function package, and provide a live URL.

---

## 3. Configuration Files

### Root `vercel.json` (Serverless API + Frontend Proxy)
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "npm --prefix final_frontend run build",
  "outputDirectory": "final_frontend/dist",
  "installCommand": "npm --prefix final_frontend install",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/api",
      "destination": "/api/index.py"
    },
    {
      "source": "/api/(.*)",
      "destination": "/api/index.py"
    },
    {
      "source": "/docs",
      "destination": "/api/index.py"
    },
    {
      "source": "/docs/(.*)",
      "destination": "/api/index.py"
    },
    {
      "source": "/openapi.json",
      "destination": "/api/index.py"
    },
    {
      "source": "/((?!api/|docs|openapi.json).*)",
      "destination": "/index.html"
    }
  ]
}
```

---

## 4. Production Verification

Once deployed, verify the deployment:

1. **Test Backend Health Endpoint:**
   ```bash
   curl -s https://<your-vercel-domain>.vercel.app/api/v1/health
   # Expected: {"status":"healthy","service":"daa-course-registration-api","version":"2.0.0"}
   ```
2. **Verify Course Catalog:**
   ```bash
   curl -s https://<your-vercel-domain>.vercel.app/api/v1/courses | jq length
   # Expected: 100
   ```
3. **Test Frontend UI:**
   - Open `https://<your-vercel-domain>.vercel.app` in a browser.
   - Click a preset track (e.g. **"CS Core"**).
   - Click **"Generate Registration Order"**.
   - Verify that topological ordering, visual roadmap, and reliable planning card render immediately.
