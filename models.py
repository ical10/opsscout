# Pydantic data contracts for OpsScout — populated test-by-test.
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WeatherSignal(BaseModel):
    date: str
    condition: str
    temperature_c: float
    precipitation_mm: float
    confidence: float = Field(ge=0.0, le=1.0)
    source: str


class EventSignal(BaseModel):
    name: str
    date: str
    estimated_attendance: int | None
    distance_m: float
    category: str
    source: str


class AccommodationSignal(BaseModel):
    date: str
    available_listings: int
    avg_price_usd: float
    occupancy_pressure: Literal["low", "medium", "high", "very_high"]
    source: str


class DemandForecast(BaseModel):
    business_id: str
    forecast_for_date: str
    generated_at: str
    weather: WeatherSignal
    events: list[EventSignal]
    accommodation: AccommodationSignal
    demand_multiplier: float = Field(ge=0.0, le=5.0)
    demand_trend: Literal[
        "spike", "above_normal", "normal", "below_normal", "drop"
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
