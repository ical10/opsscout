"""
Shared pytest fixtures.

Postgres-marked tests require a live database via DATABASE_URL.
They auto-skip when the connection cannot be opened.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make the repo root importable so `from models import ...` resolves
# when pytest is run from the repo root or any subdirectory.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return ROOT / "mock" / "fixtures"


@pytest.fixture(scope="session")
def database_url() -> str | None:
    return os.getenv("DATABASE_URL")


@pytest.fixture(scope="session")
def pg_conn(database_url: str | None):
    """
    Yield a psycopg connection if DATABASE_URL is reachable, else skip.
    All postgres-marked tests should depend on this fixture.
    """
    if not database_url:
        pytest.skip("DATABASE_URL not set; skipping postgres-marked test")
    try:
        import psycopg  # type: ignore[import-not-found]
    except ImportError:
        pytest.skip("psycopg not installed; skipping postgres-marked test")
    try:
        conn = psycopg.connect(database_url, connect_timeout=2)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"postgres unreachable ({exc!r}); skipping")
    try:
        yield conn
    finally:
        conn.close()
