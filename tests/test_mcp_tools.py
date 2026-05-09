from __future__ import annotations

from mcp_tools import get_tool_result


def test_get_tool_result_demo_mode_returns_weather_fixture(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    result = get_tool_result(tool="weather", business_id="nusa_adventures")
    assert result["source"] == "mock_weather_mcp"
    assert "zones" in result
    assert "coastal" in result["zones"]
