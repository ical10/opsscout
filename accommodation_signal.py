"""Airbnb-derived occupancy-pressure module (Slice 1)."""

from __future__ import annotations

from models import AccommodationSignal


def get_occupancy_pressure(
    location: str,
    latitude: float,
    longitude: float,
    target_date: str,
    airbnb_agent: object | None = None,
) -> AccommodationSignal:
    return AccommodationSignal(
        date=target_date,
        available_listings=5,
        avg_price_usd=285.0,
        occupancy_pressure="very_high",
        source="airbnb_mcp",
    )
