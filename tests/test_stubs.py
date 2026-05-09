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


def test_mock_scenarios_get_scenario_stubbed():
    from mock.scenarios import get_scenario

    with pytest.raises(NotImplementedError):
        get_scenario(name="storm")


