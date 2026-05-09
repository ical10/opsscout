from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta
from statistics import mean

NPM_PACKAGE = "@openbnb/mcp-server-airbnb"
RADIUS_KM = 10
HORIZON_DAYS = 1
BASELINE_OFFSET_DAYS = 28


async def _search_listings(location: str, checkin: str, checkout: str) -> list[dict]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command="npx",
        args=["-y", NPM_PACKAGE, "--ignore-robots-txt"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "airbnb_search",
                {"location": location, "checkin": checkin, "checkout": checkout},
            )
    listings: list[dict] = []
    for item in result.content:
        text = getattr(item, "text", None)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        entries = payload if isinstance(payload, list) else payload.get("searchResults", [])
        for entry in entries:
            price = (entry.get("price") or {}).get("total") or entry.get("price_per_night")
            if price is not None:
                listings.append({"price": float(price)})
    return listings


def fetch(business: dict) -> dict:
    location = business.get("address") or f"{business['latitude']},{business['longitude']}"
    today = date.today()
    target_in = today.isoformat()
    target_out = (today + timedelta(days=HORIZON_DAYS)).isoformat()
    base = today + timedelta(days=BASELINE_OFFSET_DAYS)
    base_in = base.isoformat()
    base_out = (base + timedelta(days=HORIZON_DAYS)).isoformat()

    async def _both() -> tuple[list[dict], list[dict]]:
        cur = await _search_listings(location, target_in, target_out)
        bsl = await _search_listings(location, base_in, base_out)
        return cur, bsl

    current, baseline = asyncio.run(_both())

    return {
        "location": business.get("address", location),
        "query_radius_km": RADIUS_KM,
        "results": [
            {
                "date": target_in,
                "available_listings": len(current),
                "avg_price_usd": round(mean(p["price"] for p in current), 2) if current else 0.0,
                "baseline_available": len(baseline),
                "baseline_price_usd": round(mean(p["price"] for p in baseline), 2) if baseline else 0.0,
            }
        ],
        "source": "openbnb_mcp",
    }
