"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ShortLink"

    # Public base URL used when returning short links to clients.
    base_url: str = "http://localhost:8000"

    # Storage backend: "memory" (zero-config) or "sqlite" (persistent).
    storage_backend: Literal["memory", "sqlite"] = "memory"
    sqlite_path: str = "shortlink.db"

    # The id sequence starts here so the very first code isn't a single char,
    # which keeps short codes a consistent, less-guessable length.
    id_start: int = 100_000

    # Rate limiting (token bucket per client) for the shorten endpoint.
    rate_limit_enabled: bool = True
    rate_limit_capacity: int = 20      # burst size
    rate_limit_refill_per_sec: float = 5.0

    # LRU cache size for hot short-code -> URL lookups (read path).
    cache_size: int = 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
