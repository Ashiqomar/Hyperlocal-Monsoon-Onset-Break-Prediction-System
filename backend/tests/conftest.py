import os
import tempfile
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

# Point the app at a throwaway SQLite file before anything imports the settings.
_db_dir = tempfile.mkdtemp(prefix="monsoon-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_db_dir, 'test.db')}"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
