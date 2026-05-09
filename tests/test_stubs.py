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


def test_mock_scenarios_get_scenario_stubbed():
    from mock.scenarios import get_scenario

    with pytest.raises(NotImplementedError):
        get_scenario(name="storm")


