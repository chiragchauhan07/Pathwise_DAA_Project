import os
from pathlib import Path
from typing import Any, Dict, Optional

# Compute project root deterministically (3 levels up from backend/core_engine/config.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


def _parse_env_file_pure_python(path: Path, override: bool = False) -> bool:
    """Zero-dependency standard-library parser for .env files."""
    if not path.is_file():
        return False

    loaded_any = False
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
                        val = val[1:-1]
                    if key and (override or key not in os.environ):
                        os.environ[key] = val
                        loaded_any = True
        return loaded_any
    except Exception:
        return False


def load_project_env(override: bool = False) -> None:
    """Loads environment variables from project .env file if present."""
    target_paths = [ENV_PATH]
    cwd_env = Path.cwd() / ".env"
    if cwd_env not in target_paths:
        target_paths.append(cwd_env)

    for p in target_paths:
        if p.is_file():
            try:
                from dotenv import load_dotenv

                load_dotenv(dotenv_path=p, override=override)
            except ImportError:
                _parse_env_file_pure_python(p, override=override)
            break


load_project_env(override=False)


class Settings:
    """Application configuration for the pure DAA Course Registration Assistant."""

    def __init__(self) -> None:
        self.service_name: str = os.getenv("SERVICE_NAME", "daa-course-registration-api")
        self.version: str = os.getenv("API_VERSION", "2.0.0")
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    def reload(self, override: bool = True) -> None:
        """Re-reads settings from environment and .env."""
        load_project_env(override=override)
        self.__init__()


settings = Settings()
