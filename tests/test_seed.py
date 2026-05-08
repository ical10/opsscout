"""Smoke test for seed.py — runs the full seed against the live test DB."""

from __future__ import annotations

import pytest


@pytest.mark.postgres
def test_seed_populates_both_businesses_and_30d_history(pg_conn):
    from seed import seed

    seed()
    with pg_conn.cursor() as cur:
        cur.execute("SELECT business_id FROM businesses ORDER BY business_id")
        biz_ids = [r[0] for r in cur.fetchall()]
        assert "kopi_nusa_cafe" in biz_ids
        assert "nusa_adventures" in biz_ids

        cur.execute(
            "SELECT business_id, COUNT(*) FROM historical_demand GROUP BY business_id"
        )
        counts = dict(cur.fetchall())
        assert counts.get("nusa_adventures", 0) >= 30
        assert counts.get("kopi_nusa_cafe", 0) >= 30


@pytest.mark.postgres
def test_seed_loads_real_profiles_from_fixtures(pg_conn):
    from seed import seed

    seed()
    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT profile->>'tier', profile->>'business_name' "
            "FROM businesses WHERE business_id = 'kopi_nusa_cafe'"
        )
        tier, name = cur.fetchone()
        assert tier == "2"
        assert name == "Kopi Nusa Café"

        cur.execute(
            "SELECT profile->>'tier' FROM businesses WHERE business_id = 'nusa_adventures'"
        )
        assert cur.fetchone()[0] == "1"
