"""Tests for providers.airbnb_mcp — @openbnb/mcp-server-airbnb adapter."""

from __future__ import annotations

from providers import airbnb_mcp


def test_fetch_aggregates_current_and_baseline(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    async def fake_search(location: str, checkin: str, checkout: str) -> list[dict]:
        calls.append((checkin, checkout))
        if (checkin, checkout) == calls[0]:
            return [{"price": 130.0}, {"price": 145.0}, {"price": 160.0}]
        return [{"price": 95.0}, {"price": 110.0}, {"price": 100.0}, {"price": 120.0}]

    monkeypatch.setattr("providers.airbnb_mcp._search_listings", fake_search)

    business = {"business_id": "nusa_adventures", "address": "Bali", "latitude": -8.51, "longitude": 115.26}
    result = airbnb_mcp.fetch(business)

    assert result["source"] == "openbnb_mcp"
    assert result["location"] == "Bali"
    row = result["results"][0]
    assert row["available_listings"] == 3
    assert row["avg_price_usd"] == 145.0
    assert row["baseline_available"] == 4
    assert row["baseline_price_usd"] == 106.25
    assert len(calls) == 2
