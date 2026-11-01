"""Vercel Serverless Function entry point for Pathwise FastAPI Backend."""

import os
import sys
from pathlib import Path

# Add project root to sys.path so 'backend' can be imported reliably in serverless environments
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core_engine.main import app as fastapi_app


class VercelFastAPIWrapper:
    """ASGI wrapper ensuring incoming Vercel Serverless requests retain their
    intended route path even when rewritten through /api/index.py.
    """

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            path = scope.get("path", "")

            # If path was rewritten directly to the entrypoint script or bare /api
            if path in ("/api/index.py", "/index.py", "/api", "/api/"):
                header_dict = {k.lower(): v for k, v in scope.get("headers", [])}
                # Check headers injected by Vercel's Edge Router
                for header_key in (
                    b"x-matched-path",
                    b"x-forwarded-uri",
                    b"x-vercel-original-uri",
                    b"x-real-path",
                ):
                    raw_val = header_dict.get(header_key)
                    if raw_val:
                        val_str = raw_val.decode("utf-8", "ignore").strip()
                        if val_str and val_str not in ("/api/index.py", "/index.py", "/api", "/api/"):
                            clean_path = val_str.split("?")[0]
                            scope["path"] = clean_path
                            scope["raw_path"] = clean_path.encode("utf-8")
                            break

        await self.asgi_app(scope, receive, send)


app = VercelFastAPIWrapper(fastapi_app)

# Vercel serverless expects 'app' exposed at module level
__all__ = ["app"]
