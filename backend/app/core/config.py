import json
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables (or a .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Monsoon Decision Twin"
    version: str = "0.1.0"

    # SQLite for local dev. Swap to Postgres by setting DATABASE_URL, e.g.
    # postgresql+psycopg://user:pass@host:5432/dbname
    # Plain postgres:// / postgresql:// URLs (as given by Render/Railway) are accepted too.
    database_url: str = "sqlite:///./monsoon.db"

    # Allowed browser origins. Accepts a JSON list or a comma-separated string.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    # Optional regex for extra origins, e.g. Vercel previews: https://.*\.vercel\.app
    cors_origin_regex: str | None = None

    # Base URL of the frontend, used for links in outgoing messages.
    public_app_url: str = "http://localhost:5173"

    # --- Notifications ---
    # Regional language that messages will be translated into (ISO 639-1).
    notify_regional_language: str = "mr"
    # WhatsApp via Twilio. Not used yet: messages are only logged (see app/services/notify.py).
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_from: str | None = None  # e.g. "whatsapp:+14155238886"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg3(cls, url: str) -> str:
        """Hosting platforms (Render, Railway, Heroku-style) hand out postgres:// URLs, which
        SQLAlchemy rejects outright; pin the psycopg 3 driver we ship rather than rely on
        SQLAlchemy's default driver for postgresql://."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return json.loads(value)
            return [o.strip().rstrip("/") for o in value.split(",") if o.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
