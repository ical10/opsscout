"""Postgres-backed tests for db.py.

Each test takes the `pg_conn` fixture from conftest.py — auto-skips when
DATABASE_URL is unset or postgres is unreachable. Per-test cleanup happens
in a savepoint that's rolled back at function end so tests don't leak
data between runs.
"""

from __future__ import annotations

import pytest

from db import create_tables, get_business


@pytest.mark.postgres
def test_create_tables_creates_all_four_tables(pg_conn):
    create_tables(pg_conn)
    expected = {"businesses", "proposals", "action_feedback", "historical_demand"}
    with pg_conn.cursor() as cur:
        for name in expected:
            cur.execute("SELECT to_regclass(%s)", (f"public.{name}",))
            row = cur.fetchone()
            assert row[0] is not None, f"table {name} not created"


@pytest.mark.postgres
def test_get_business_returns_jsonb_profile_as_dict(pg_conn):
    create_tables(pg_conn)
    sample_id = "test_db_get_biz_001"
    profile = {"business_id": sample_id, "tier": 1, "name": "Test Business"}
    with pg_conn.cursor() as cur:
        cur.execute("DELETE FROM businesses WHERE business_id = %s", (sample_id,))
        cur.execute(
            "INSERT INTO businesses (business_id, profile) VALUES (%s, %s::jsonb)",
            (sample_id, '{"business_id": "test_db_get_biz_001", "tier": 1, "name": "Test Business"}'),
        )
        pg_conn.commit()
    try:
        result = get_business(pg_conn, sample_id)
        assert isinstance(result, dict)
        assert result == profile
    finally:
        with pg_conn.cursor() as cur:
            cur.execute("DELETE FROM businesses WHERE business_id = %s", (sample_id,))
            pg_conn.commit()
