"""Vercel Serverless Function entry point for Pathwise FastAPI Backend."""

import os
import sys
from pathlib import Path

# Add project root to sys.path so 'backend' can be imported reliably in serverless environments
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core_engine.main import app

# Vercel serverless expects 'app' exposed at module level
__all__ = ["app"]
