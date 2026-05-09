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


def test_occupancy_pressure_kopi_nusa_low():
    signal = get_occupancy_pressure(
        location="Ubud",
        latitude=-8.51,
        longitude=115.26,
        target_date="2026-05-09",
        airbnb_agent=None,
        business_id="kopi_nusa_cafe",
    )
    assert signal.occupancy_pressure == "low"
    assert signal.available_listings == 32


def test_occupancy_pressure_high_when_price_spike_alone():
    signal = get_occupancy_pressure(
        location="Seminyak",
        latitude=-8.69,
        longitude=115.16,
        target_date="2026-05-12",
        airbnb_agent=None,
    )
    assert signal.occupancy_pressure == "high"
    assert signal.available_listings == 22
    assert signal.avg_price_usd == 180.0


def test_occupancy_pressure_uses_dispatcher_so_live_data_flows_through(monkeypatch):
    fake_airbnb = {
        "results": [
            {
                "date": "2026-05-10",
                "available_listings": 7,
                "avg_price_usd": 240.0,
                "baseline_available": 30,
                "baseline_price_usd": 110.0,
            }
        ],
        "source": "openbnb_mcp",
    }
    monkeypatch.setattr("accommodation_signal.get_tool_result", lambda tool, business_id: fake_airbnb)

    signal = get_occupancy_pressure(
        location="Seminyak",
        latitude=-8.69,
        longitude=115.16,
        target_date="2026-05-10",
        airbnb_agent=None,
        business_id="nusa_adventures",
    )
    assert signal.available_listings == 7
    assert signal.avg_price_usd == 240.0
    assert signal.occupancy_pressure == "very_high"
