import os
from pathlib import Path
from typing import Any, Dict, Optional

# Compute project root deterministically (3 levels up from backend/core_engine/config.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


def _parse_env_file_pure_python(path: Path, override: bool = False) -> bool:
    """Zero-dependency standard-library parser for .env files.

    Guarantees environment variables are loaded even if python-dotenv
    is not installed in the active environment.
    Preserves existing environment variables unless override=True.
    """
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
                    # Strip matching surrounding quotes
                    if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
                        val = val[1:-1]
                    if key and (override or key not in os.environ):
                        os.environ[key] = val
                        loaded_any = True
        return loaded_any
    except Exception:
        return False


def load_project_env(override: bool = False) -> str:
    """Loads environment variables from project .env file.

    Tries python-dotenv first. If unavailable or not installed, falls back
    to the built-in parser. Returns the detected source of GEMINI_API_KEY.
    """
    initial_key = os.getenv("GEMINI_API_KEY")
    had_os_key = initial_key is not None and initial_key.strip() != ""

    target_paths = [ENV_PATH]
    cwd_env = Path.cwd() / ".env"
    if cwd_env not in target_paths:
        target_paths.append(cwd_env)

    for p in target_paths:
        if p.is_file():
            # Try python-dotenv first
            try:
                from dotenv import load_dotenv

                load_dotenv(dotenv_path=p, override=override)
            except ImportError:
                _parse_env_file_pure_python(p, override=override)
            break

    # Determine safe key source classification without logging secret
    current_key = os.getenv("GEMINI_API_KEY")
    if had_os_key and not override:
        return "os_environ"
    elif current_key and current_key.strip():
        return "dotenv_file"
    elif current_key is not None:
        return "empty"
    return "none"


_initial_source = load_project_env(override=False)


class Settings:
    """Application configuration with deterministic .env loading and centralized AI settings."""

    def __init__(self, key_source: Optional[str] = None) -> None:
        self.service_name: str = os.getenv("SERVICE_NAME", "daa-learning-path-api")
        self.version: str = os.getenv("API_VERSION", "1.0.0")
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.cors_origins: str = os.getenv("CORS_ORIGINS", "*")

        # Centralized Gemini configuration
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

        raw_timeout = os.getenv("GEMINI_TIMEOUT", "15.0")
        try:
            self.gemini_timeout: float = float(raw_timeout)
            if self.gemini_timeout <= 0:
                self.gemini_timeout = 15.0
        except (ValueError, TypeError):
            self.gemini_timeout = 15.0

        raw_retries = os.getenv("GEMINI_MAX_RETRIES", "2")
        try:
            self.gemini_max_retries: int = int(raw_retries)
            if self.gemini_max_retries < 1:
                self.gemini_max_retries = 1
        except (ValueError, TypeError):
            self.gemini_max_retries = 2

        self._key_source: str = key_source or _initial_source

    @property
    def gemini_api_key(self) -> Optional[str]:
        """Returns the configured Gemini API key, or None if not set or blank."""
        key = os.getenv("GEMINI_API_KEY")
        if key and key.strip():
            return key.strip()
        return None

    @property
    def is_gemini_configured(self) -> bool:
        """Returns True if a non-empty Gemini API key is configured."""
        return self.gemini_api_key is not None

    @property
    def gemini_key_source(self) -> str:
        """Returns safe key source ('os_environ', 'dotenv_file', 'empty', or 'none')."""
        key = os.getenv("GEMINI_API_KEY")
        if key is not None and not key.strip():
            return "empty"
        if key and key.strip():
            return self._key_source if self._key_source != "none" else "os_environ"
        return "none"

    def get_ai_diagnostic(self) -> Dict[str, Any]:
        """Returns safe diagnostic information about AI configuration without exposing secrets."""
        key = self.gemini_api_key
        raw_key = os.getenv("GEMINI_API_KEY")
        is_empty = raw_key is not None and not raw_key.strip()
        return {
            "is_configured": key is not None,
            "is_empty": is_empty,
            "key_source": self.gemini_key_source,
            "model": self.gemini_model,
            "timeout_seconds": self.gemini_timeout,
            "max_retries": self.gemini_max_retries,
        }

    def reload(self, override: bool = True) -> None:
        """Re-reads settings from environment and .env."""
        new_source = load_project_env(override=override)
        self.__init__(key_source=new_source)


settings = Settings()
