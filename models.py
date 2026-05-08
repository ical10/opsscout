# Pydantic data contracts for OpsScout — populated test-by-test.
from __future__ import annotations

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
