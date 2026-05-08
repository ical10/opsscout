"""Postgres-backed tests for db.py.

Each test takes the `pg_conn` fixture from conftest.py — auto-skips when
DATABASE_URL is unset or postgres is unreachable. Per-test cleanup happens
in a savepoint that's rolled back at function end so tests don't leak
data between runs.
"""

from __future__ import annotations

import pytest

from models import (
    AccommodationSignal,
    ActionProposal,
    DemandForecast,
    WeatherSignal,
)

from db import create_tables, get_business, get_proposal, save_proposal


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


def _sample_proposal(proposal_id: str) -> ActionProposal:
    weather = WeatherSignal(
        date="2026-05-10", condition="heavy_rain",
        temperature_c=25.0, precipitation_mm=52.0,
        confidence=0.91, source="mock_weather_mcp",
    )
    accommodation = AccommodationSignal(
        date="2026-05-10", available_listings=5,
        avg_price_usd=285.0, occupancy_pressure="very_high",
        source="airbnb_mcp",
    )
    forecast = DemandForecast(
        business_id="nusa_adventures", forecast_for_date="2026-05-10",
        generated_at="2026-05-09T08:00:00Z",
        weather=weather, events=[], accommodation=accommodation,
        demand_multiplier=1.6, demand_trend="above_normal",
        confidence=0.82, reasoning="storm + tourists stuck",
    )
    return ActionProposal(
        proposal_id=proposal_id,
        business_id="nusa_adventures",
        proposed_at="2026-05-09T08:30:00Z",
        forecast=forecast,
        inventory_actions=[], staffing_actions=[], communications=[],
        estimated_cost_usd=240.0, reversible=False,
        priority="urgent",
        summary_for_owner="Cancel surf, expand trek.",
        confidence=0.88,
    )


@pytest.mark.postgres
def test_save_and_get_proposal_round_trips_action_proposal(pg_conn):
    create_tables(pg_conn)
    proposal_id = "test_db_save_get_001"
    original = _sample_proposal(proposal_id)
    try:
        save_proposal(pg_conn, original)
        loaded = get_proposal(pg_conn, proposal_id)
        assert isinstance(loaded, ActionProposal)
        assert loaded.proposal_id == proposal_id
        assert loaded.business_id == "nusa_adventures"
        assert loaded.summary_for_owner == "Cancel surf, expand trek."
        assert loaded.approval_required is True
        assert loaded.forecast.demand_multiplier == 1.6
    finally:
        with pg_conn.cursor() as cur:
            cur.execute("DELETE FROM proposals WHERE proposal_id = %s", (proposal_id,))
            pg_conn.commit()
