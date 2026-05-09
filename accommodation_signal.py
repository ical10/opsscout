"""Airbnb-derived occupancy-pressure module (Slice 1).

Converts raw Airbnb listing/price data into an `AccommodationSignal` whose
`occupancy_pressure` literal drives the demand multiplier. This is the
hackathon's hero differentiator — it turns "tourists are stuck" into
concrete operational actions.
"""

from __future__ import annotations

import json
from pathlib import Path

from models import AccommodationSignal

FIXTURES_DIR = Path(__file__).parent / "mock" / "fixtures"


def get_occupancy_pressure(
    location: str,
    latitude: float,
    longitude: float,
    target_date: str,
    airbnb_agent: object | None = None,
    business_id: str = "nusa_adventures",
) -> AccommodationSignal:
    fixture = json.loads(
        (FIXTURES_DIR / business_id / "airbnb.json").read_text()
    )
    row = next(r for r in fixture["results"] if r["date"] == target_date)
    avail_ratio = row["available_listings"] / max(row["baseline_available"], 1)
    price_ratio = row["avg_price_usd"] / max(row["baseline_price_usd"], 1)
    if avail_ratio < 0.3 and price_ratio > 1.4:
        pressure = "very_high"
    elif avail_ratio < 0.5 or price_ratio > 1.2:
        pressure = "high"
    elif avail_ratio < 0.75:
        pressure = "medium"
    else:
        pressure = "low"
    return AccommodationSignal(
        date=target_date,
        available_listings=row["available_listings"],
        avg_price_usd=float(row["avg_price_usd"]),
        occupancy_pressure=pressure,
        source="airbnb_mcp",
    )
