"""Postgres-backed tests for db.py.

Each test takes the `pg_conn` fixture from conftest.py — auto-skips when
DATABASE_URL is unset or postgres is unreachable. Per-test cleanup happens
in a savepoint that's rolled back at function end so tests don't leak
data between runs.
"""

from __future__ import annotations

import pytest

from db import create_tables


@pytest.mark.postgres
def test_create_tables_creates_all_four_tables(pg_conn):
    create_tables(pg_conn)
    expected = {"businesses", "proposals", "action_feedback", "historical_demand"}
    with pg_conn.cursor() as cur:
        for name in expected:
            cur.execute("SELECT to_regclass(%s)", (f"public.{name}",))
            row = cur.fetchone()
            assert row[0] is not None, f"table {name} not created"
