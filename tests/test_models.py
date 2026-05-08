"""Validation tests for the Pydantic contracts in models.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import WeatherSignal


def test_weather_signal_valid_construction():
    w = WeatherSignal(
        date="2026-05-10",
        condition="heavy_rain",
        temperature_c=25.0,
        precipitation_mm=52.0,
        confidence=0.91,
        source="mock_weather_mcp",
    )
    assert w.condition == "heavy_rain"
    assert w.confidence == 0.91


def test_weather_signal_rejects_confidence_above_one():
    with pytest.raises(ValidationError):
        WeatherSignal(
            date="2026-05-10",
            condition="heavy_rain",
            temperature_c=25.0,
            precipitation_mm=52.0,
            confidence=1.5,
            source="mock_weather_mcp",
        )
