"""Slice 0 scaffolding contract: every Slice 1-4-owned module exposes its
public function, and that function raises NotImplementedError until the
owning slice fills it in.

Tests are intentionally upside-down — they pass while the stubs are still
stubs, then fail (and need updating) once the owning slice ships real
behaviour. That's the signal to the parallel cs worker that they've
landed on the right import surface.
"""

from __future__ import annotations

import pytest


def test_mcp_tools_get_tool_result_stubbed():
    from mcp_tools import get_tool_result

    with pytest.raises(NotImplementedError):
        get_tool_result(tool="weather", business_id="nusa_adventures")


def test_accommodation_signal_get_occupancy_pressure_stubbed():
    from accommodation_signal import get_occupancy_pressure

    with pytest.raises(NotImplementedError):
        get_occupancy_pressure(
            location="Seminyak",
            latitude=-8.69,
            longitude=115.16,
            target_date="2026-05-10",
        )


def test_structured_outputs_extractors_stubbed():
    from structured_outputs import (
        extract_action_proposal,
        extract_demand_forecast,
        extract_react_step,
    )

    with pytest.raises(NotImplementedError):
        extract_demand_forecast(raw_agent_text="x", context={})
    with pytest.raises(NotImplementedError):
        extract_action_proposal(raw_manager_text="x", forecast=None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        extract_react_step(agent_role="X", step_index=0, raw_step_text="x")


def test_crew_run_crew_stubbed():
    from crew import run_crew

    with pytest.raises(NotImplementedError):
        run_crew(business_id="nusa_adventures")


def test_graph_build_and_run_stubbed():
    from graph import build_graph, run_for_business

    with pytest.raises(NotImplementedError):
        build_graph()
    with pytest.raises(NotImplementedError):
        run_for_business(business_id="nusa_adventures")


def test_onboarding_render_stubbed():
    from onboarding import render_onboarding

    with pytest.raises(NotImplementedError):
        render_onboarding()
