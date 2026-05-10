"""Slice 4 Streamlit page tests — uses streamlit.testing.v1.AppTest."""
from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from db import create_tables, save_proposal
from models import (
    AccommodationSignal,
    ActionProposal,
    DemandForecast,
    ReActStep,
    ReActTrace,
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
    # OAuth shell still rendered as a hint about production wiring,
    # but the demo picker is always available so live data + demo
    # businesses can co-exist.
    assert "Connect Shopify" in button_labels
    assert "Connect Google" in button_labels
    assert len(app.radio) == 1
    assert "Nusa Adventures" in app.radio[0].options


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
    # Header sections + sentence-1 of the summary should be visible.
    assert "Recommended actions" in rendered
    assert "Owner brief" in rendered
    assert proposal.summary_for_owner.split(". ")[0] in rendered
    button_labels = [b.label for b in app.button]
    assert any("Approve" in label for label in button_labels)
    assert any("Reject" in label for label in button_labels)


def test_trace_page_renders_react_steps_in_order(monkeypatch):
    trace = ReActTrace(
        task_id="task-1",
        business_id="nusa_adventures",
        agent_role="manager",
        final_output_type="ActionProposal",
        steps=[
            ReActStep(
                step_index=0,
                agent_role="forecaster",
                thought="Need weather first",
                tool_called="weather_lookup",
                tool_input={"date": "2026-05-10"},
                observation="sunny, 29C",
                is_final=False,
            ),
            ReActStep(
                step_index=1,
                agent_role="forecaster",
                thought="Check occupancy now",
                tool_called="airbnb_lookup",
                tool_input={"date": "2026-05-10"},
                observation="occupancy high",
                is_final=False,
            ),
            ReActStep(
                step_index=2,
                agent_role="manager",
                thought="Compile proposal",
                tool_called=None,
                tool_input=None,
                observation=None,
                is_final=True,
            ),
        ],
    )

    import pages._data as _data

    monkeypatch.setattr(_data, "fetch_latest_trace", lambda bid: trace)

    app = AppTest.from_file("pages/3_Trace.py")
    app.session_state["business_id"] = "nusa_adventures"
    app.run()
    assert not app.exception

    rendered = " | ".join(
        [m.value for m in app.markdown]
        + [s.value for s in app.subheader]
        + [c.value for c in app.caption]
        + [e.label for e in app.expander]
    )
    assert "Need weather first" in rendered
    assert "weather_lookup" in rendered
    assert "sunny, 29C" in rendered
    assert "Check occupancy now" in rendered
    assert "Compile proposal" in rendered
    idx0 = rendered.index("Need weather first")
    idx1 = rendered.index("Check occupancy now")
    idx2 = rendered.index("Compile proposal")
    assert idx0 < idx1 < idx2
    assert "0" in rendered and "1" in rendered and "2" in rendered


def test_onboarding_demo_mode_shows_welcome_and_picker(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    from onboarding import render_onboarding

    app = AppTest.from_function(render_onboarding).run()
    assert not app.exception
    headers = (
        [h.value for h in app.header]
        + [s.value for s in app.subheader]
        + [t.value for t in app.title]
    )
    assert any("Welcome" in h for h in headers)
    assert len(app.radio) == 1
    options = app.radio[0].options
    assert "Nusa Adventures" in options
    assert "Kopi Nusa Café" in options


def test_onboarding_production_mode_shows_oauth_placeholders(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    from onboarding import render_onboarding

    app = AppTest.from_function(render_onboarding).run()
    assert not app.exception
    button_labels = [b.label for b in app.button]
    assert "Connect Shopify" in button_labels
    assert all(b.disabled for b in app.button)


def test_history_page_lists_past_proposals(monkeypatch):
    rows = [
        {
            "proposed_at": "2026-05-08T01:00:00",
            "summary_for_owner": "Saturday surge plan",
            "status": "approved",
            "rating": "thumbs_up",
        },
        {
            "proposed_at": "2026-05-07T01:00:00",
            "summary_for_owner": "Wednesday slowdown plan",
            "status": "rejected",
            "rating": "thumbs_down",
        },
    ]

    import pages._data as _data

    monkeypatch.setattr(_data, "list_proposals", lambda bid: rows)

    app = AppTest.from_file("pages/4_History.py", default_timeout=10)
    app.session_state["business_id"] = "nusa_adventures"
    app.run()
    assert not app.exception
    assert len(app.dataframe) == 1
    df = app.dataframe[0].value
    summaries = df["summary_for_owner"].tolist()
    statuses = df["status"].tolist()
    assert "Saturday surge plan" in summaries
    assert "Wednesday slowdown plan" in summaries
    assert "approved" in statuses
    assert "rejected" in statuses


def test_dashboard_approve_updates_db_and_resumes_graph(monkeypatch):
    proposal = _make_proposal()
    import graph
    import pages._data as _data

    status_calls: list[tuple[str, str]] = []
    graph_calls: list[str] = []
    monkeypatch.setattr(_data, "fetch_pending_proposal", lambda bid: proposal)
    monkeypatch.setattr(
        _data,
        "update_proposal_status",
        lambda pid, status: status_calls.append((pid, status)),
    )
    monkeypatch.setattr(graph, "run_for_business", lambda bid: graph_calls.append(bid))

    app = AppTest.from_file("pages/2_Dashboard.py")
    app.session_state["business_id"] = "nusa_adventures"
    app.run()
    [b for b in app.button if "Approve" in b.label][0].click().run()

    assert status_calls == [("prop-1", "approved")]
    assert graph_calls == ["nusa_adventures"]


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


@pytest.mark.postgres
def test_update_proposal_status_writes_status(pg_conn):
    from pages import _data

    create_tables(pg_conn)
    with pg_conn.cursor() as cur:
        cur.execute("DELETE FROM proposals WHERE business_id = 'nusa_adventures'")
    pg_conn.commit()
    save_proposal(pg_conn, _make_proposal(proposal_id="prop-x"))

    import os

    os.environ["DATABASE_URL"] = pg_conn.info.dsn
    _data.update_proposal_status("prop-x", "approved")

    with pg_conn.cursor() as cur:
        cur.execute("SELECT status FROM proposals WHERE proposal_id = 'prop-x'")
        assert cur.fetchone()[0] == "approved"


@pytest.mark.postgres
def test_list_proposals_returns_rows_for_business(pg_conn):
    from pages import _data

    create_tables(pg_conn)
    with pg_conn.cursor() as cur:
        cur.execute("DELETE FROM proposals WHERE business_id = 'nusa_adventures'")
        cur.execute("DELETE FROM action_feedback WHERE business_id = 'nusa_adventures'")
    pg_conn.commit()
    older = _make_proposal(proposal_id="prop-old", summary="older plan")
    newer = _make_proposal(proposal_id="prop-new", summary="newer plan")
    object.__setattr__(older, "proposed_at", "2026-05-08T00:00:00")
    object.__setattr__(newer, "proposed_at", "2026-05-09T00:00:00")
    save_proposal(pg_conn, older)
    save_proposal(pg_conn, newer)

    import os

    os.environ["DATABASE_URL"] = pg_conn.info.dsn
    rows = _data.list_proposals("nusa_adventures")
    assert len(rows) >= 2
    summaries = [r["summary_for_owner"] for r in rows]
    assert summaries.index("newer plan") < summaries.index("older plan")
    assert {"proposed_at", "status", "rating"} <= set(rows[0].keys())


@pytest.mark.postgres
def test_fetch_latest_trace_synthesizes_from_proposal(pg_conn):
    from pages import _data

    create_tables(pg_conn)
    with pg_conn.cursor() as cur:
        cur.execute("DELETE FROM proposals WHERE business_id = 'nusa_adventures'")
    pg_conn.commit()
    save_proposal(pg_conn, _make_proposal(proposal_id="prop-trace"))

    import os

    os.environ["DATABASE_URL"] = pg_conn.info.dsn
    trace = _data.fetch_latest_trace("nusa_adventures")
    assert trace is not None
    assert trace.business_id == "nusa_adventures"
    roles = [s.agent_role for s in trace.steps]
    # All five spec §6 agents must appear in the synthesized timeline.
    assert {
        "Demand Forecaster",
        "Demand Modeler",
        "Logistics Agent",
        "Communications Agent",
        "Operations Manager",
    } <= set(roles)
    # Forecaster steps cite the dispatcher tool calls run_crew makes.
    forecaster_tools = {s.tool_called for s in trace.steps if s.agent_role == "Demand Forecaster"}
    assert {"get_tool_result"} <= forecaster_tools
    # Final step's observation reflects the proposal's actual priority.
    assert "priority=" in trace.steps[-1].observation
    assert trace.steps[-1].is_final is True
