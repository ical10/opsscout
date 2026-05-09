"""Tests for providers.openmeteo — Open-Meteo daily forecast adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

from providers import openmeteo


def test_fetch_maps_response_to_fixture_shape(monkeypatch) -> None:
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json = MagicMock(return_value={
        "latitude": -8.51,
        "longitude": 115.26,
        "timezone": "Asia/Makassar",
        "daily": {
            "time": ["2026-05-10", "2026-05-11"],
            "temperature_2m_max": [29.4, 30.1],
            "temperature_2m_min": [23.0, 23.4],
            "precipitation_sum": [12.5, 0.4],
            "weather_code": [63, 1],
            "wind_speed_10m_max": [22.0, 14.5],
        },
    })
    captured: dict = {}

    def fake_get(url: str, params: dict, timeout: float):
        captured["url"] = url
        captured["params"] = params
        return fake_response

    monkeypatch.setattr("providers.openmeteo.httpx.get", fake_get)

    business = {"business_id": "nusa_adventures", "latitude": -8.51, "longitude": 115.26, "address": "Bali"}
    result = openmeteo.fetch(business)

    assert result["source"] == "openmeteo"
    assert "zones" in result
    forecast = result["zones"]["default"]["forecast"]
    assert len(forecast) == 2
    assert forecast[0]["date"] == "2026-05-10"
    assert forecast[0]["condition"] == "rain"
    assert forecast[0]["temperature_c"] == 26.2
    assert forecast[0]["precipitation_mm"] == 12.5
    assert forecast[1]["condition"] == "partly_cloudy"
    assert captured["params"]["latitude"] == -8.51
