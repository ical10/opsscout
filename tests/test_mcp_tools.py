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


def test_get_tool_result_live_dispatches_to_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr("mcp_tools.CACHE_DIR", tmp_path)

    captured: dict = {}

    def fake_fetch(business: dict) -> dict:
        captured["business_id"] = business["business_id"]
        return {"source": "openmeteo", "zones": {"default": {"forecast": []}}}

    monkeypatch.setattr("mcp_tools.openmeteo.fetch", fake_fetch)

    result = get_tool_result(tool="weather", business_id="nusa_adventures")
    assert result["source"] == "openmeteo"
    assert captured["business_id"] == "nusa_adventures"


def test_live_dispatch_caches_so_second_call_skips_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr("mcp_tools.CACHE_DIR", tmp_path)

    call_count = {"n": 0}

    def fake_fetch(business: dict) -> dict:
        call_count["n"] += 1
        return {"source": "openmeteo", "n": call_count["n"]}

    monkeypatch.setattr("mcp_tools.openmeteo.fetch", fake_fetch)

    first = get_tool_result(tool="weather", business_id="nusa_adventures")
    second = get_tool_result(tool="weather", business_id="nusa_adventures")
    assert first == second
    assert call_count["n"] == 1


def test_live_dispatch_routes_airbnb_and_events_to_their_providers(monkeypatch, tmp_path):
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setattr("mcp_tools.CACHE_DIR", tmp_path)
    monkeypatch.setattr("mcp_tools.airbnb_mcp.fetch", lambda b: {"source": "openbnb_mcp"})
    monkeypatch.setattr("mcp_tools.predicthq.fetch", lambda b: {"source": "predicthq"})

    assert get_tool_result(tool="airbnb", business_id="nusa_adventures")["source"] == "openbnb_mcp"
    assert get_tool_result(tool="events", business_id="nusa_adventures")["source"] == "predicthq"


def test_live_dispatch_falls_back_to_fixture_for_inventory_calendar_business(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    inventory = get_tool_result(tool="inventory", business_id="kopi_nusa_cafe")
    assert {item["name"] for item in inventory["items"]} >= {"coffee_beans"}


def test_get_tool_result_unknown_business_raises(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    with pytest.raises(FileNotFoundError):
        get_tool_result(tool="weather", business_id="nope")
