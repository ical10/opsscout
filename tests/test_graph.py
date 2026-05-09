"""Tests for graph.py — LangGraph state machine + checkpointer."""

from __future__ import annotations


def test_build_graph_has_expected_nodes() -> None:
    from graph import build_graph

    graph = build_graph()
    nodes = set(graph.get_graph().nodes)
    expected = {
        "forecaster",
        "demand_modeler",
        "logistics_and_comms",
        "ops_manager",
        "await_approval",
        "execute",
    }
    assert expected <= nodes


def test_graph_skips_execute_until_owner_approved(monkeypatch) -> None:
    from models import (
        AccommodationSignal,
        ActionProposal,
        DemandForecast,
        WeatherSignal,
    )

    forecast = DemandForecast(
        business_id="nusa_adventures",
        forecast_for_date="2026-05-10",
        generated_at="2026-05-09T08:00:00Z",
        weather=WeatherSignal(
            date="2026-05-10", condition="rain", temperature_c=25.0,
            precipitation_mm=10.0, confidence=0.9, source="openmeteo",
        ),
        events=[],
        accommodation=AccommodationSignal(
            date="2026-05-10", available_listings=10, avg_price_usd=120.0,
            occupancy_pressure="medium", source="airbnb_mcp",
        ),
        demand_multiplier=1.0, demand_trend="normal",
        confidence=0.8, reasoning="ok",
    )
    monkeypatch.setattr("graph.run_crew", lambda bid: ActionProposal(
        proposal_id="susp", business_id=bid, proposed_at="2026-05-09T08:00:00Z",
        forecast=forecast, inventory_actions=[], staffing_actions=[], communications=[],
        estimated_cost_usd=0.0, reversible=True, approval_required=True,
        priority="medium", summary_for_owner="ok", confidence=0.7,
    ))

    from graph import build_graph

    graph = build_graph()
    config = {"configurable": {"thread_id": "test-thread-1"}}

    initial = {"business_id": "nusa_adventures", "owner_approved": False, "execution_log": []}
    first = graph.invoke(initial, config=config)
    assert first.get("execution_log") == []

    second = graph.invoke({**first, "owner_approved": True}, config=config)
    assert len(second.get("execution_log") or []) >= 1
    assert second["execution_log"][-1]["action"] == "executed"


def test_ops_manager_node_populates_proposal_via_run_crew(monkeypatch) -> None:
    from models import (
        AccommodationSignal,
        ActionProposal,
        DemandForecast,
        WeatherSignal,
    )

    forecast = DemandForecast(
        business_id="nusa_adventures",
        forecast_for_date="2026-05-10",
        generated_at="2026-05-09T08:00:00Z",
        weather=WeatherSignal(
            date="2026-05-10", condition="rain", temperature_c=25.0,
            precipitation_mm=10.0, confidence=0.9, source="openmeteo",
        ),
        events=[],
        accommodation=AccommodationSignal(
            date="2026-05-10", available_listings=10, avg_price_usd=120.0,
            occupancy_pressure="medium", source="airbnb_mcp",
        ),
        demand_multiplier=1.0, demand_trend="normal",
        confidence=0.8, reasoning="ok",
    )
    fake = ActionProposal(
        proposal_id="ops-test", business_id="nusa_adventures",
        proposed_at="2026-05-09T08:00:00Z", forecast=forecast,
        inventory_actions=[], staffing_actions=[], communications=[],
        estimated_cost_usd=0.0, reversible=True, approval_required=True,
        priority="medium", summary_for_owner="ok", confidence=0.7,
    )
    monkeypatch.setattr("graph.run_crew", lambda bid: fake)

    from graph import build_graph

    graph = build_graph()
    final = graph.invoke(
        {"business_id": "nusa_adventures", "owner_approved": False, "execution_log": []},
        config={"configurable": {"thread_id": "ops-test-thread"}},
    )
    assert final["proposal"].proposal_id == "ops-test"
    assert final["forecast"].business_id == "nusa_adventures"


def test_business_state_carries_react_trace_and_error_per_spec_section_8() -> None:
    from graph import BusinessState

    annotations = BusinessState.__annotations__
    assert "react_trace" in annotations
    assert "error" in annotations


import pytest


@pytest.fixture
def _clean_postgres_thread(pg_conn):
    """Wipe checkpoint rows for `opsscout:nusa_adventures` before + after
    so reruns don't accumulate rows and the assertion sees a fresh write."""
    thread = "opsscout:nusa_adventures"

    def _wipe():
        with pg_conn.cursor() as cur:
            for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                cur.execute(
                    f"DELETE FROM {table} WHERE thread_id = %s", (thread,)
                )
        pg_conn.commit()

    _wipe()
    yield
    _wipe()


@pytest.mark.postgres
def test_run_for_business_persists_checkpoint_to_postgres(pg_conn, monkeypatch, _clean_postgres_thread):
    from models import (
        AccommodationSignal,
        ActionProposal,
        DemandForecast,
        WeatherSignal,
    )

    forecast = DemandForecast(
        business_id="nusa_adventures",
        forecast_for_date="2026-05-10",
        generated_at="2026-05-09T08:00:00Z",
        weather=WeatherSignal(
            date="2026-05-10", condition="rain", temperature_c=25.0,
            precipitation_mm=10.0, confidence=0.9, source="openmeteo",
        ),
        events=[],
        accommodation=AccommodationSignal(
            date="2026-05-10", available_listings=10, avg_price_usd=120.0,
            occupancy_pressure="medium", source="airbnb_mcp",
        ),
        demand_multiplier=1.0, demand_trend="normal",
        confidence=0.8, reasoning="ok",
    )
    fake_proposal = ActionProposal(
        proposal_id="pg-test", business_id="nusa_adventures",
        proposed_at="2026-05-09T08:00:00Z", forecast=forecast,
        inventory_actions=[], staffing_actions=[], communications=[],
        estimated_cost_usd=0.0, reversible=True, approval_required=True,
        priority="medium", summary_for_owner="ok", confidence=0.7,
    )
    monkeypatch.setattr("graph.run_crew", lambda bid: fake_proposal)

    from graph import run_for_business

    result = run_for_business("nusa_adventures")
    assert result.business_id == "nusa_adventures"

    cur = pg_conn.cursor()
    cur.execute(
        "SELECT thread_id FROM checkpoints WHERE thread_id = %s LIMIT 1",
        ("opsscout:nusa_adventures",),
    )
    assert cur.fetchone() is not None
