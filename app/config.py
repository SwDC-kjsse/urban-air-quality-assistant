"""Application configuration loaded from environment variables."""
from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings."""

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip() or "gemini-flash-latest"
    request_timeout_s: float = 12.0
    cache_ttl_s: int = 600


settings = Settings()
