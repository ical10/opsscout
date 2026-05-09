"""Mock-aware MCP dispatcher.

`get_tool_result` is the single funnel for every external data lookup.

- DEMO_MODE=true (default) reads JSON fixtures from
  ``mock/fixtures/<business_id>/<tool>.json`` — offline, deterministic,
  hackathon-safe.
- DEMO_MODE=false routes ``weather``, ``airbnb``, ``events`` to real
  providers (Open-Meteo, @openbnb MCP, PredictHQ) with a read-through
  cache at ``mock/cache/`` so demo replays don't burn quota. Tools
  without a real provider (``inventory``, ``calendar``, ``business``)
  continue to read fixtures even in live mode.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from providers import airbnb_mcp, cache, openmeteo, predicthq

ROOT = Path(__file__).parent
FIXTURES_DIR = ROOT / "mock" / "fixtures"
CACHE_DIR = ROOT / "mock" / "cache"

def _read_fixture(tool: str, business_id: str) -> dict:
    return json.loads((FIXTURES_DIR / business_id / f"{tool}.json").read_text())


def _live_fetch(tool: str, business: dict) -> dict | None:
    if tool == "weather":
        return openmeteo.fetch(business)
    if tool == "airbnb":
        return airbnb_mcp.fetch(business)
    if tool == "events":
        return predicthq.fetch(business)
    return None


def get_tool_result(
    tool: str,
    business_id: str,
    params: dict | None = None,
) -> dict:
    if os.getenv("DEMO_MODE", "true").lower() == "true":
        return _read_fixture(tool, business_id)

    cache_key = f"{tool}__{business_id}__{date.today().isoformat()}"
    cached = cache.read(cache_key, CACHE_DIR)
    if cached is not None:
        return cached

    business = _read_fixture("business", business_id)
    live = _live_fetch(tool, business)
    if live is None:
        return _read_fixture(tool, business_id)

    cache.write(cache_key, live, CACHE_DIR)
    return live
