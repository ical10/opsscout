"""Airbnb-derived occupancy-pressure module (Slice 1).

Converts raw Airbnb listing/price data into an `AccommodationSignal` whose
`occupancy_pressure` literal drives the demand multiplier. This is the
hackathon's hero differentiator — it turns "tourists are stuck" into
concrete operational actions.
"""

from __future__ import annotations

from models import AccommodationSignal


def get_occupancy_pressure(
    location: str,
    latitude: float,
    longitude: float,
    target_date: str,
    airbnb_agent: object | None = None,
) -> AccommodationSignal:
    raise NotImplementedError(
        "owned by Slice 1 — see docs/plans/slice-1-mcp-tools.md"
    )
