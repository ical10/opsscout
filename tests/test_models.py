"""Validation tests for the Pydantic contracts in models.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import (
    AccommodationSignal,
    ActionFeedback,
    ActionProposal,
    CommunicationDraft,
    DemandForecast,
    EventSignal,
    InventoryItem,
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


def test_action_feedback_rejects_unknown_rating():
    with pytest.raises(ValidationError):
        ActionFeedback(
            feedback_id="fb_002",
            proposal_id="p_002",
            business_id="nusa_adventures",
            submitted_at="2026-05-11T09:00:00Z",
            rating="meh",
            free_text=None,
            was_accurate=None,
        )


def test_action_feedback_records_ids_and_freetext():
    fb = ActionFeedback(
        feedback_id="fb_003",
        proposal_id="p_003",
        business_id="kopi_nusa_cafe",
        submitted_at="2026-05-11T09:00:00Z",
        rating="thumbs_down",
        free_text="Forecast missed the festival impact.",
        was_accurate=False,
    )
    assert fb.feedback_id == "fb_003"
    assert fb.proposal_id == "p_003"
    assert fb.business_id == "kopi_nusa_cafe"
    assert fb.submitted_at == "2026-05-11T09:00:00Z"
    assert fb.free_text == "Forecast missed the festival impact."


def test_inventory_item_valid_construction():
    item = InventoryItem(
        name="rain_ponchos",
        current_quantity=12.0,
        unit="units",
        suggested_order_quantity=40.0,
        estimated_cost_usd=160.0,
        supplier_name="Bali Outdoor Supply",
    )
    assert item.name == "rain_ponchos"
    assert item.suggested_order_quantity == 40.0
    assert item.supplier_name == "Bali Outdoor Supply"


def test_inventory_item_records_quantity_unit_cost():
    item = InventoryItem(
        name="oat_milk",
        current_quantity=4.0,
        unit="L",
        suggested_order_quantity=12.0,
        estimated_cost_usd=48.0,
        supplier_name=None,
    )
    assert item.current_quantity == 4.0
    assert item.unit == "L"
    assert item.estimated_cost_usd == 48.0


def test_communication_draft_valid_construction():
    cd = CommunicationDraft(
        channel="whatsapp",
        recipient="guests",
        subject=None,
        body="Heavy rain tomorrow — surfing replaced with cooking class.",
        urgency="medium",
    )
    assert cd.channel == "whatsapp"
    assert cd.urgency == "medium"


def test_communication_draft_records_recipient_subject_body():
    cd = CommunicationDraft(
        channel="email",
        recipient="staff",
        subject="Tomorrow's schedule change",
        body="Please report at 09:00 instead of 07:00.",
        urgency="high",
    )
    assert cd.recipient == "staff"
    assert cd.subject == "Tomorrow's schedule change"
    assert cd.body.startswith("Please report")


def _sample_forecast() -> DemandForecast:
    return DemandForecast(
        business_id="nusa_adventures",
        forecast_for_date="2026-05-10",
        generated_at="2026-05-09T08:00:00Z",
        weather=_sample_weather(),
        events=[],
        accommodation=_sample_accommodation(),
        demand_multiplier=1.6,
        demand_trend="above_normal",
        confidence=0.82,
        reasoning="indoor pivot",
    )


def test_action_proposal_approval_required_defaults_true():
    p = ActionProposal(
        proposal_id="p_001",
        business_id="nusa_adventures",
        proposed_at="2026-05-09T08:30:00Z",
        forecast=_sample_forecast(),
        inventory_actions=[],
        staffing_actions=[],
        communications=[],
        estimated_cost_usd=None,
        reversible=True,
        priority="high",
        summary_for_owner="Indoor pivot for tomorrow's heavy rain.",
        confidence=0.82,
    )
    assert p.approval_required is True
