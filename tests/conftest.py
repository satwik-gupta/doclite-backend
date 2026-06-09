"""Pytest fixtures: an isolated SQLite test DB, freshly seeded per test."""
import os
import tempfile

# Configure the app for testing BEFORE importing it.
_TEST_DB = os.path.join(tempfile.gettempdir(), "doclite_pytest.db")
os.environ["DOCLITE_DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["DOCLITE_SEED_ON_STARTUP"] = "false"
os.environ.setdefault("DOCLITE_SECRET_KEY", "test-secret-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture()
def client():
    """A TestClient backed by a fresh, seeded database for each test."""
    Base.metadata.drop_all(bind=db.engine)
    Base.metadata.create_all(bind=db.engine)
    seed(get_settings(), db)
    with TestClient(app) as test_client:
        yield test_client


def auth_header(client, username, password="password123"):
    res = client.post("/api/auth/login", json={"identifier": username, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def create_doc(client, header, title="Test Doc", html="<p>hello</p>"):
    res = client.post("/api/documents", headers=header, json={"title": title, "content_html": html})
    assert res.status_code == 201, res.text
    return res.json()
