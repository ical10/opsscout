from __future__ import annotations

from accommodation_signal import get_occupancy_pressure


def test_occupancy_pressure_very_high_when_listings_low_and_price_spike():
    signal = get_occupancy_pressure(
        location="Seminyak",
        latitude=-8.69,
        longitude=115.16,
        target_date="2026-05-10",
        airbnb_agent=None,
    )
    assert signal.occupancy_pressure == "very_high"
    assert signal.available_listings == 5
    assert signal.source == "airbnb_mcp"
