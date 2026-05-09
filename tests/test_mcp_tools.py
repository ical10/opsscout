from __future__ import annotations

import pytest

from mcp_tools import get_tool_result


def test_get_tool_result_demo_mode_returns_weather_fixture(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    result = get_tool_result(tool="weather", business_id="nusa_adventures")
    assert result["source"] == "mock_weather_mcp"
    assert "zones" in result
    assert "coastal" in result["zones"]


def test_get_tool_result_kopi_nusa_inventory():
    result = get_tool_result(tool="inventory", business_id="kopi_nusa_cafe")
    assert {item["name"] for item in result["items"]} >= {
        "coffee_beans", "fresh_milk", "pastries"
    }


def test_get_tool_result_demo_mode_false_raises_not_implemented(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    with pytest.raises(NotImplementedError):
        get_tool_result(tool="weather", business_id="nusa_adventures")


def test_get_tool_result_unknown_business_raises(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    with pytest.raises(FileNotFoundError):
        get_tool_result(tool="weather", business_id="nope")
