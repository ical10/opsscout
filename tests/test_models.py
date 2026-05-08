"""Validation tests for the Pydantic contracts in models.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import (
    AccommodationSignal,
    DemandForecast,
    EventSignal,
    WeatherSignal,
)


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


def test_event_signal_valid_construction():
    e = EventSignal(
        name="Ubud Food Festival",
        date="2026-05-12",
        estimated_attendance=2500,
        distance_m=420.0,
        category="food",
        source="mock_events_mcp",
    )
    assert e.name == "Ubud Food Festival"
    assert e.estimated_attendance == 2500


def test_accommodation_signal_valid_construction():
    a = AccommodationSignal(
        date="2026-05-10",
        available_listings=8,
        avg_price_usd=275.0,
        occupancy_pressure="very_high",
        source="airbnb_mcp",
    )
    assert a.occupancy_pressure == "very_high"


def test_accommodation_signal_rejects_unknown_pressure():
    with pytest.raises(ValidationError):
        AccommodationSignal(
            date="2026-05-10",
            available_listings=8,
            avg_price_usd=275.0,
            occupancy_pressure="extreme",
            source="airbnb_mcp",
        )


def _sample_weather() -> WeatherSignal:
    return WeatherSignal(
        date="2026-05-10",
        condition="heavy_rain",
        temperature_c=25.0,
        precipitation_mm=52.0,
        confidence=0.9,
        source="mock_weather_mcp",
    )


def _sample_accommodation() -> AccommodationSignal:
    return AccommodationSignal(
        date="2026-05-10",
        available_listings=8,
        avg_price_usd=275.0,
        occupancy_pressure="very_high",
        source="airbnb_mcp",
    )


def test_demand_forecast_valid_construction():
    f = DemandForecast(
        business_id="nusa_adventures",
        forecast_for_date="2026-05-10",
        generated_at="2026-05-09T08:00:00Z",
        weather=_sample_weather(),
        events=[],
        accommodation=_sample_accommodation(),
        demand_multiplier=1.6,
        demand_trend="above_normal",
        confidence=0.82,
        reasoning="Heavy rain + tourists stuck indoors → indoor activity spike.",
    )
    assert f.demand_multiplier == 1.6
    assert f.demand_trend == "above_normal"
