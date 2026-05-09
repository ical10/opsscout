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
