"""Validation tests for the Pydantic contracts in models.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import (
    AccommodationSignal,
    ActionFeedback,
    DemandForecast,
    EventSignal,
    ReActStep,
    StaffingChange,
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


def test_demand_forecast_rejects_multiplier_above_five():
    with pytest.raises(ValidationError):
        DemandForecast(
            business_id="nusa_adventures",
            forecast_for_date="2026-05-10",
            generated_at="2026-05-09T08:00:00Z",
            weather=_sample_weather(),
            events=[],
            accommodation=_sample_accommodation(),
            demand_multiplier=7.5,
            demand_trend="spike",
            confidence=0.82,
            reasoning="hyperbole",
        )


def test_demand_forecast_rejects_unknown_trend():
    with pytest.raises(ValidationError):
        DemandForecast(
            business_id="nusa_adventures",
            forecast_for_date="2026-05-10",
            generated_at="2026-05-09T08:00:00Z",
            weather=_sample_weather(),
            events=[],
            accommodation=_sample_accommodation(),
            demand_multiplier=1.0,
            demand_trend="explosive",
            confidence=0.82,
            reasoning="not a valid trend",
        )


def test_react_step_allows_null_tool_and_observation():
    s = ReActStep(
        step_index=0,
        agent_role="Forecaster",
        thought="I need to decide which signal to fetch first.",
        tool_called=None,
        tool_input=None,
        observation=None,
    )
    assert s.tool_called is None
    assert s.observation is None
    assert s.is_final is False


def test_react_step_records_thought_and_index():
    s = ReActStep(
        step_index=3,
        agent_role="Forecaster",
        thought="Fetching weather first.",
        tool_called="weather",
        tool_input={"date": "2026-05-10"},
        observation="heavy rain forecast",
    )
    assert s.step_index == 3
    assert s.agent_role == "Forecaster"
    assert s.thought == "Fetching weather first."
    assert s.tool_input == {"date": "2026-05-10"}


def test_staffing_change_valid_construction():
    sc = StaffingChange(
        action="add_shift",
        role="server",
        count=2,
        date="2026-05-10",
        reason="Demand spike from indoor pivot.",
    )
    assert sc.action == "add_shift"
    assert sc.count == 2


def test_staffing_change_rejects_unknown_action():
    with pytest.raises(ValidationError):
        StaffingChange(
            action="hire_immediately",
            role="server",
            count=1,
            date="2026-05-10",
            reason="not in the allowed enum",
        )


def test_staffing_change_records_role_date_reason():
    sc = StaffingChange(
        action="add_shift",
        role="guide",
        count=2,
        date="2026-05-10",
        reason="indoor activity surge",
    )
    assert sc.role == "guide"
    assert sc.date == "2026-05-10"
    assert sc.reason == "indoor activity surge"


def test_action_feedback_valid_construction():
    fb = ActionFeedback(
        feedback_id="fb_001",
        proposal_id="p_001",
        business_id="nusa_adventures",
        submitted_at="2026-05-11T09:00:00Z",
        rating="thumbs_up",
        free_text=None,
        was_accurate=True,
    )
    assert fb.rating == "thumbs_up"
    assert fb.was_accurate is True
