"""Application configuration.

`Settings` is a Pydantic-settings class: a single encapsulated source of truth for
runtime configuration, loaded from environment variables / a `.env` file. It is
exposed via a cached accessor so the same instance is injected everywhere.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Encapsulates all configurable knobs for the backend.

    Environment variables are prefixed with ``DOCLITE_`` (e.g. ``DOCLITE_SECRET_KEY``).
    """

    model_config = SettingsConfigDict(
        env_prefix="DOCLITE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "DocLite"
    debug: bool = False

    # --- Security ---
    secret_key: str = "dev-secret-change-me-please-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    # --- Database ---
    database_url: str = "sqlite:///./doclite.db"

    # --- Uploads ---
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 MB
    allowed_upload_extensions: List[str] = [".txt", ".md", ".markdown", ".docx"]

    # --- CORS ---
    # Explicit allowed origins (comma-separated env). Add your Vercel production URL here
    # in addition to the regex below if you want to be strict.
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    # Regex that ALSO allows matching origins (in addition to the list). The default
    # permits any *.vercel.app origin so Vercel production + preview deploys work
    # without re-listing each generated URL. Set to "" to disable.
    cors_origin_regex: str = r"https://([a-z0-9-]+\.)*vercel\.app"

    # --- Seeding ---
    seed_on_startup: bool = True

    @field_validator("cors_origins", "allowed_upload_extensions", mode="before")
    @classmethod
    def _split_csv(cls, value):
        """Allow comma-separated env strings as well as JSON lists."""
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance (dependency-injectable)."""
    return Settings()
