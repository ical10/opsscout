"""Slice 4 Streamlit page tests — uses streamlit.testing.v1.AppTest."""
from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from db import create_tables, save_proposal
from models import (
    AccommodationSignal,
    ActionProposal,
    DemandForecast,
    WeatherSignal,
)


def _make_proposal(
    proposal_id: str = "prop-1",
    business_id: str = "nusa_adventures",
    summary: str = "ACT NOW: weather + occupancy say staff up Saturday.",
    priority: str = "high",
) -> ActionProposal:
    forecast = DemandForecast(
        business_id=business_id,
        forecast_for_date="2026-05-10",
        generated_at="2026-05-09T00:00:00",
        weather=WeatherSignal(
            date="2026-05-10",
            condition="sunny",
            temperature_c=29.0,
            precipitation_mm=0.0,
            confidence=0.8,
            source="test",
        ),
        events=[],
        accommodation=AccommodationSignal(
            date="2026-05-10",
            available_listings=5,
            avg_price_usd=100.0,
            occupancy_pressure="high",
            source="test",
        ),
        demand_multiplier=1.5,
        demand_trend="above_normal",
        confidence=0.7,
        reasoning="test",
    )
    return ActionProposal(
        proposal_id=proposal_id,
        business_id=business_id,
        proposed_at="2026-05-09T01:00:00",
        forecast=forecast,
        inventory_actions=[],
        staffing_actions=[],
        communications=[],
        estimated_cost_usd=None,
        reversible=True,
        priority=priority,
        summary_for_owner=summary,
        confidence=0.7,
    )


def test_main_app_loads():
    app = AppTest.from_file("main.py").run()
    assert not app.exception


def test_connect_page_demo_mode_picker(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    app = AppTest.from_file("pages/1_Connect.py").run()
    assert not app.exception
    options = app.radio[0].options
    assert "Nusa Adventures" in options
    assert "Kopi Nusa Café" in options


def test_connect_page_writes_business_id_on_select(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    app = AppTest.from_file("pages/1_Connect.py").run()
    app.radio[0].set_value("Nusa Adventures").run()
    assert app.session_state["business_id"] == "nusa_adventures"


def test_connect_page_shows_oauth_buttons_when_not_demo(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    app = AppTest.from_file("pages/1_Connect.py").run()
    button_labels = [b.label for b in app.button]
    assert "Connect Shopify" in button_labels
    assert "Connect Google" in button_labels
    assert len(app.radio) == 0


def test_dashboard_renders_pending_proposal_card(monkeypatch):
    proposal = _make_proposal()
    import pages._data as _data

    monkeypatch.setattr(_data, "fetch_pending_proposal", lambda bid: proposal)

    app = AppTest.from_file("pages/2_Dashboard.py")
    app.session_state["business_id"] = "nusa_adventures"
    app.run()
    assert not app.exception
    rendered = " ".join(
        [m.value for m in app.markdown]
        + [s.value for s in app.subheader]
        + [c.value for c in app.caption]
    )
    assert proposal.summary_for_owner in rendered
    assert "high" in rendered.lower()
    button_labels = [b.label for b in app.button]
    assert "Approve" in button_labels
    assert "Reject" in button_labels


@pytest.mark.postgres
def test_fetch_pending_proposal_returns_latest_pending(pg_conn):
    from pages import _data

    create_tables(pg_conn)
    with pg_conn.cursor() as cur:
        cur.execute("DELETE FROM proposals WHERE business_id = 'nusa_adventures'")
    pg_conn.commit()
    older = _make_proposal(proposal_id="prop-old")
    newer = _make_proposal(proposal_id="prop-new", summary="newer summary")
    object.__setattr__(older, "proposed_at", "2026-05-08T00:00:00")
    object.__setattr__(newer, "proposed_at", "2026-05-09T00:00:00")
    save_proposal(pg_conn, older)
    save_proposal(pg_conn, newer)

    import os

    os.environ["DATABASE_URL"] = pg_conn.info.dsn
    got = _data.fetch_pending_proposal("nusa_adventures")
    assert got is not None
    assert got.proposal_id == "prop-new"
