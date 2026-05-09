"""Airbnb-derived occupancy-pressure module.

Converts Airbnb listing/price data (from the mock-aware dispatcher) into
an `AccommodationSignal` whose `occupancy_pressure` literal drives the
demand multiplier. The dispatcher decides where the data comes from —
fixture in DEMO_MODE=true, @openbnb MCP via providers/airbnb_mcp.py in
DEMO_MODE=false.
"""

from __future__ import annotations

from mcp_tools import get_tool_result
from models import AccommodationSignal


def _classify(avail_ratio: float, price_ratio: float) -> str:
    if avail_ratio < 0.3 and price_ratio > 1.4:
        return "very_high"
    if avail_ratio < 0.5 or price_ratio > 1.2:
        return "high"
    if avail_ratio < 0.75:
        return "medium"
    return "low"


def get_occupancy_pressure(
    location: str,
    latitude: float,
    longitude: float,
    target_date: str,
    airbnb_agent: object | None = None,
    business_id: str = "nusa_adventures",
) -> AccommodationSignal:
    airbnb = get_tool_result("airbnb", business_id)
    rows = airbnb["results"]
    row = next((r for r in rows if r["date"] == target_date), rows[0])
    avail_ratio = row["available_listings"] / max(row["baseline_available"], 1)
    price_ratio = row["avg_price_usd"] / max(row["baseline_price_usd"], 1)
    return AccommodationSignal(
        date=target_date,
        available_listings=row["available_listings"],
        avg_price_usd=float(row["avg_price_usd"]),
        occupancy_pressure=_classify(avail_ratio, price_ratio),
        source="airbnb_mcp",
    )
