# Pydantic data contracts for OpsScout — populated test-by-test.
from __future__ import annotations

from pydantic import BaseModel


class WeatherSignal(BaseModel):
    date: str
    condition: str
    temperature_c: float
    precipitation_mm: float
    confidence: float
    source: str
