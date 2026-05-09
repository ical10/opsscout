from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from models import (
    AccommodationSignal,
    ActionProposal,
    DemandForecast,
    EventSignal,
    ReActStep,
    WeatherSignal,
)
from structured_outputs import (
    extract_action_proposal,
    extract_demand_forecast,
    extract_react_step,
)


def _sample_forecast() -> DemandForecast:
    return DemandForecast(
        business_id="nusa_adventures",
        forecast_for_date="2026-05-10",
        generated_at="2026-05-09T08:00:00Z",
        weather=WeatherSignal(
            date="2026-05-10", condition="heavy_rain",
            temperature_c=25.0, precipitation_mm=52.0,
            confidence=0.91, source="mock_weather_mcp",
        ),
        events=[],
        accommodation=AccommodationSignal(
            date="2026-05-10", available_listings=5,
            avg_price_usd=285.0, occupancy_pressure="very_high",
            source="airbnb_mcp",
        ),
        demand_multiplier=1.6,
        demand_trend="above_normal",
        confidence=0.82,
        reasoning="storm + tourists stuck → indoor pivot",
    )


def test_extract_demand_forecast_returns_validated_model(monkeypatch):
    fake = _sample_forecast()
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=fake))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion
    monkeypatch.setattr("structured_outputs._client", fake_client)

    result = extract_demand_forecast(
        raw_agent_text="Storm tomorrow…", context={"business_id": "x"}
    )
    assert isinstance(result, DemandForecast)
    assert result.demand_trend == "above_normal"
    fake_client.beta.chat.completions.parse.assert_called_once()
    kwargs = fake_client.beta.chat.completions.parse.call_args.kwargs
    assert kwargs["response_format"] is DemandForecast
    assert kwargs["temperature"] == 0.0


def test_extract_demand_forecast_overrides_generated_at(monkeypatch):
    bad = _sample_forecast()
    bad.generated_at = "2025-04-05T10:00:00Z"  # model hallucinated past timestamp
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=bad))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion
    monkeypatch.setattr("structured_outputs._client", fake_client)

    result = extract_demand_forecast(raw_agent_text="…", context={})
    assert result.generated_at != "2025-04-05T10:00:00Z"
    from datetime import datetime
    datetime.fromisoformat(result.generated_at.replace("Z", "+00:00"))


def test_extract_action_proposal_overrides_approval_required(monkeypatch):
    forecast = _sample_forecast()
    bad_proposal = ActionProposal(
        proposal_id="p_001", business_id="nusa_adventures",
        proposed_at="2026-05-09T08:30:00Z", forecast=forecast,
        inventory_actions=[], staffing_actions=[], communications=[],
        estimated_cost_usd=None, reversible=True,
        approval_required=False,  # <-- model lied
        priority="high", summary_for_owner="x", confidence=0.9,
    )
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=bad_proposal))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion
    monkeypatch.setattr("structured_outputs._client", fake_client)

    result = extract_action_proposal(raw_manager_text="…", forecast=forecast)
    assert result.approval_required is True


def test_extract_action_proposal_tier2_strips_staffing_actions(monkeypatch):
    forecast = _sample_forecast()
    forecast.business_id = "kopi_nusa_cafe"
    bad = ActionProposal(
        proposal_id="p_002", business_id="kopi_nusa_cafe",
        proposed_at="2026-05-09T08:30:00Z", forecast=forecast,
        inventory_actions=[],
        staffing_actions=[
            __import__("models").StaffingChange(
                action="add_shift", role="barista", count=1,
                date="2026-05-10", reason="busy",
            )
        ],
        communications=[],
        estimated_cost_usd=None, reversible=True,
        priority="medium", summary_for_owner="x", confidence=0.8,
    )
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=bad))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion
    monkeypatch.setattr("structured_outputs._client", fake_client)

    result = extract_action_proposal(raw_manager_text="…", forecast=forecast)
    assert result.staffing_actions == []


def test_extract_react_step_pins_agent_role_and_step_index(monkeypatch):
    bad_step = ReActStep(
        step_index=99,
        agent_role="WrongAgent",
        thought="check weather",
        tool_called="weather",
        tool_input={"business_id": "nusa_adventures"},
        observation=None,
        is_final=False,
    )
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=bad_step))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion
    monkeypatch.setattr("structured_outputs._client", fake_client)

    result = extract_react_step(
        agent_role="DemandForecaster",
        step_index=3,
        raw_step_text="…",
    )
    assert result.agent_role == "DemandForecaster"
    assert result.step_index == 3


@pytest.mark.live
def test_extract_demand_forecast_live_round_trip():
    pytest.importorskip("openai")
    if not os.getenv("AMD_VLLM_BASE_URL"):
        pytest.skip("AMD_VLLM_BASE_URL not set — skipping live vLLM round-trip")

    raw_text = (
        "Forecast for nusa_adventures on 2026-05-10. Heavy rain (52mm) is expected. "
        "Airbnb data shows only 5 listings left at $285 avg, occupancy_pressure=very_high. "
        "No major events nearby. Tourists will be stuck indoors — demand for indoor and "
        "rain-friendly tour activities should spike. Estimated demand_multiplier ≈ 1.6, "
        "trend above_normal, confidence around 0.8."
    )
    result = extract_demand_forecast(
        raw_agent_text=raw_text,
        context={
            "business_id": "nusa_adventures",
            "forecast_for_date": "2026-05-10",
        },
    )
    assert isinstance(result, DemandForecast)
    assert 0.0 <= result.demand_multiplier <= 5.0
    assert result.reasoning.strip() != ""
