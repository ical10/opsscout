from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from models import (
    AccommodationSignal,
    DemandForecast,
    EventSignal,
    WeatherSignal,
)
from structured_outputs import extract_demand_forecast


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
