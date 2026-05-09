"""Tests for crew.py — 5 CrewAI agents + run_crew orchestrator."""

from __future__ import annotations

from crew import forecaster


def test_forecaster_role_goal_backstory_match_spec() -> None:
    assert forecaster.role == "Demand Forecaster"
    assert "weather, local event, and accommodation occupancy" in forecaster.goal
    assert "data analyst" in forecaster.backstory.lower()


def test_all_five_agents_present() -> None:
    from crewai import Agent

    from crew import comms_agent, demand_modeler, logistics_agent, ops_manager

    for agent, role in [
        (demand_modeler, "Demand Modeler"),
        (logistics_agent, "Logistics Agent"),
        (comms_agent, "Communications Agent"),
        (ops_manager, "Operations Manager"),
    ]:
        assert isinstance(agent, Agent), f"{role} must be a real CrewAI Agent (spec §6)"
        assert agent.role == role


def _sample_forecast():
    from models import AccommodationSignal, DemandForecast, WeatherSignal

    return DemandForecast(
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


def _sample_proposal():
    from models import ActionProposal

    return ActionProposal(
        proposal_id="p1", business_id="nusa_adventures",
        proposed_at="2026-05-09T08:00:00Z",
        forecast=_sample_forecast(),
        inventory_actions=[], staffing_actions=[], communications=[],
        estimated_cost_usd=0.0, reversible=True, approval_required=True,
        priority="medium", summary_for_owner="ok", confidence=0.7,
    )


def test_run_crew_calls_dispatcher_and_extractors_in_spec_order(monkeypatch) -> None:
    calls: list[tuple] = []

    def fake_tool(tool, business_id, params=None):
        calls.append(("tool", tool))
        if tool == "inventory":
            return {"items": []}
        if tool == "calendar":
            return {"staff_availability": []}
        if tool == "events":
            return {"events": []}
        if tool == "airbnb":
            return {"results": [{"date": "2026-05-10", "available_listings": 10,
                                 "avg_price_usd": 120.0, "baseline_available": 12,
                                 "baseline_price_usd": 100.0}]}
        return {"zones": {"default": {"forecast": []}}, "source": "openmeteo"}

    def fake_forecast(*a, **kw):
        calls.append(("extract_demand_forecast",))
        return _sample_forecast()

    def fake_proposal(*a, **kw):
        calls.append(("extract_action_proposal",))
        return _sample_proposal()

    monkeypatch.setattr("crew.get_tool_result", fake_tool)
    monkeypatch.setattr("crew.extract_demand_forecast", fake_forecast)
    monkeypatch.setattr("crew.extract_action_proposal", fake_proposal)

    from crew import run_crew

    proposal = run_crew(business_id="nusa_adventures")

    tool_order = [c[1] for c in calls if c[0] == "tool"]
    assert tool_order.index("weather") < tool_order.index("airbnb")
    assert any(c[0] == "extract_demand_forecast" for c in calls)
    assert any(c[0] == "extract_action_proposal" for c in calls)
    assert proposal.business_id == "nusa_adventures"
    assert proposal.approval_required is True
