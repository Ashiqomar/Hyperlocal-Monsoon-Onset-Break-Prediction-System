import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        ("postgresql://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:///./monsoon.db", "sqlite:///./monsoon.db"),
    ],
)
def test_database_url_uses_psycopg3(given: str, expected: str) -> None:
    assert Settings(database_url=given).database_url == expected


@pytest.mark.parametrize(
    "env_value",
    ['["https://a.vercel.app", "http://localhost:5173"]', "https://a.vercel.app/, http://localhost:5173"],
)
def test_cors_origins_accepts_json_or_comma_list(monkeypatch: pytest.MonkeyPatch, env_value: str) -> None:
    monkeypatch.setenv("CORS_ORIGINS", env_value)
    assert Settings().cors_origins == ["https://a.vercel.app", "http://localhost:5173"]
