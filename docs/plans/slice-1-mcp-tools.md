# Slice 1 — MCP Tools + Accommodation Signal

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans` or `superpowers:subagent-driven-development`. Tests use checkbox `- [ ]` syntax.

**Goal:** Implement the mock-aware MCP dispatcher (`mcp_tools.py`) and the Airbnb-derived occupancy-pressure module (`accommodation_signal.py`) — pure functions over JSON fixtures with no LLM and no network in DEMO_MODE.

**Architecture:** `get_tool_result(tool, business_id, params)` is the single funnel for every external data lookup. DEMO_MODE=true reads `mock/fixtures/<business_id>/<tool>.json`; production path raises `NotImplementedError` (deferred to Slice 5). `get_occupancy_pressure` derives an `AccommodationSignal` from the airbnb fixture's listing-availability and price-vs-baseline ratios using the rules in spec §10.

**Tech Stack:** Python 3.11, pydantic 2.9.2, pytest 8.3.3. No external deps.

**Inputs you can rely on (Slice 0 contract):**
- `models.AccommodationSignal` — pinned with `Literal["low","medium","high","very_high"]`
- `mock/fixtures/{nusa_adventures,kopi_nusa_cafe}/{business,weather,airbnb,events,inventory,calendar}.json`
- `mcp_tools.get_tool_result` and `accommodation_signal.get_occupancy_pressure` — currently raise `NotImplementedError`
- `tests/test_stubs.py::test_mcp_tools_get_tool_result_stubbed` and `::test_accommodation_signal_get_occupancy_pressure_stubbed` are CURRENTLY GREEN — your first task is to update or delete them as the stubs become real

**Files owned (do not edit anything else):**
- `mcp_tools.py`
- `accommodation_signal.py`
- `tests/test_mcp_tools.py` (new)
- `tests/test_accommodation_signal.py` (new)

---

## Task 1: `get_tool_result` happy path (DEMO_MODE)

- [ ] **Step 1: Write the failing test** — `tests/test_mcp_tools.py`

```python
from __future__ import annotations

import os

from mcp_tools import get_tool_result


def test_get_tool_result_demo_mode_returns_weather_fixture(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    result = get_tool_result(tool="weather", business_id="nusa_adventures")
    assert result["source"] == "mock_weather_mcp"
    assert "zones" in result
    assert "coastal" in result["zones"]
```

- [ ] **Step 2: Run** — `pytest tests/test_mcp_tools.py -v` → FAILS with NotImplementedError.

- [ ] **Step 3: Implement minimum**

```python
# mcp_tools.py
from __future__ import annotations

import json
import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "mock" / "fixtures"


def get_tool_result(
    tool: str,
    business_id: str,
    params: dict | None = None,
) -> dict:
    if os.getenv("DEMO_MODE", "true").lower() != "true":
        raise NotImplementedError(
            "Production MCP path is out of scope until Slice 5."
        )
    fixture_path = FIXTURES_DIR / business_id / f"{tool}.json"
    return json.loads(fixture_path.read_text())
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(mcp): get_tool_result reads fixtures in DEMO_MODE`.

## Task 2: kopi_nusa_cafe inventory loads

- [ ] **Step 1: Add test**

```python
def test_get_tool_result_kopi_nusa_inventory():
    result = get_tool_result(tool="inventory", business_id="kopi_nusa_cafe")
    assert {item["name"] for item in result["items"]} >= {
        "coffee_beans", "fresh_milk", "pastries"
    }
```

- [ ] **Step 2: Run** → PASS (fixture already wired).
- [ ] **Step 3: Commit** — `test(mcp): kopi_nusa inventory fixture exposes café items`.

## Task 3: Production-mode + missing-business error paths

- [ ] **Step 1: Add tests**

```python
def test_get_tool_result_demo_mode_false_raises_not_implemented(monkeypatch):
    import pytest
    monkeypatch.setenv("DEMO_MODE", "false")
    with pytest.raises(NotImplementedError):
        get_tool_result(tool="weather", business_id="nusa_adventures")


def test_get_tool_result_unknown_business_raises(monkeypatch):
    import pytest
    monkeypatch.setenv("DEMO_MODE", "true")
    with pytest.raises(FileNotFoundError):
        get_tool_result(tool="weather", business_id="nope")
```

- [ ] **Step 2: Run** → PASS (already covered by impl).
- [ ] **Step 3: Commit** — `test(mcp): error paths covered`.

## Task 4: `get_occupancy_pressure` very_high case

- [ ] **Step 1: Write failing test** — `tests/test_accommodation_signal.py`

```python
from __future__ import annotations

from datetime import date

from accommodation_signal import get_occupancy_pressure


def test_occupancy_pressure_very_high_when_listings_low_and_price_spike():
    signal = get_occupancy_pressure(
        location="Seminyak",
        latitude=-8.69,
        longitude=115.16,
        target_date="2026-05-10",
        airbnb_agent=None,  # DEMO_MODE: read fixture, ignore agent
    )
    assert signal.occupancy_pressure == "very_high"
    assert signal.available_listings == 5
    assert signal.source == "airbnb_mcp"
```

- [ ] **Step 2: Run** → FAILS with NotImplementedError.

- [ ] **Step 3: Implement**

```python
# accommodation_signal.py
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
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(accommodation): derive occupancy_pressure from airbnb fixture`.

## Task 5: Coverage for low/medium pressure

- [ ] Add `test_occupancy_pressure_low_when_supply_normal`: target_date `2026-05-12` (avail 22/32 ≈ 0.69, price ratio 1.24) → spec rule says <0.75 → `medium`. Adjust based on actual fixture.
- [ ] Add `test_occupancy_pressure_kopi_nusa_low`: kopi airbnb has 32/30 supply ratio + 0.98 price ratio → `low`.
- [ ] Run → PASS (impl already covers).
- [ ] Commit — `test(accommodation): low/medium pressure cases`.

## Task 6: Update Slice-0 stub tests

- [ ] Open `tests/test_stubs.py`. Delete `test_mcp_tools_get_tool_result_stubbed`, `test_accommodation_signal_get_occupancy_pressure_stubbed`, and `test_mock_scenarios_get_scenario_stubbed` (or leave the last alone if you don't touch `mock/scenarios.py`).
- [ ] Run full suite — `pytest -m "not live and not postgres"` → all green.
- [ ] Commit — `chore: drop slice-0 stub guards now that Slice 1 ships real impl`.

## Verification

```bash
pytest tests/test_mcp_tools.py tests/test_accommodation_signal.py -v
pytest -m "not live and not postgres"
```

All green. Branch ready for merge into `main`.

## Out of scope

- Real PydanticAI `MCPServerStdio` wiring → Slice 5 deferred
- Scenario flag overrides via `mock/scenarios.py` → leave the stub
- Caching, retries, rate limiting

## Source-of-truth pointers

- spec §9 (MCP integrations table)
- spec §10 (occupancy pressure rules)
- spec §11a (fixture shapes)
