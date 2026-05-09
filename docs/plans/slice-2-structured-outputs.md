# Slice 2 — Structured Outputs Layer

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans` or `superpowers:subagent-driven-development`. Tests use checkbox `- [ ]`.

**Goal:** Implement the three OpenAI-SDK-driven extractors in `structured_outputs.py` that turn raw agent prose into validated Pydantic models — `DemandForecast`, `ActionProposal`, `ReActStep`. Every LLM extraction in OpsScout flows through these three functions and nothing else.

**Architecture:** All extractors call `client.beta.chat.completions.parse()` with a `response_format=<PydanticModel>` argument and `temperature=0.0`. Two hard guards live in code (not just prompt): `extract_action_proposal` always sets `approval_required=True` post-extract; for Tier-2 businesses it forces `staffing_actions=[]`. `extract_react_step` overrides `agent_role` and `step_index` with the caller-supplied values regardless of model output.

**Tech Stack:** Python 3.11, `openai==1.51.0` (vLLM-compatible), pydantic 2.9.2, pytest 8.3.3 + pytest-mock 3.14.0.

**Inputs you can rely on (Slice 0 contract):**
- `models.DemandForecast`, `models.ActionProposal`, `models.ReActStep` (all locked, see spec §5)
- `structured_outputs.{extract_demand_forecast,extract_action_proposal,extract_react_step}` — currently raise `NotImplementedError`

**Files owned (do not edit anything else):**
- `structured_outputs.py`
- `tests/test_structured_outputs.py` (new)

**Live-test prerequisite:** Slice 0.5 must be done so `AMD_VLLM_BASE_URL` resolves to a reachable vLLM instance. The `@pytest.mark.live` test skips when env var is absent.

---

## Task 1: `extract_demand_forecast` happy path with mocked client

- [ ] **Step 1: Write failing test** — `tests/test_structured_outputs.py`

```python
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from models import (
    AccommodationSignal,
    DemandForecast,
    EventSignal,
    WeatherSignal,
)
from structured_outputs import extract_demand_forecast


def _sample_forecast() -> DemandForecast:
    return DemandForecast(
        business_id="nusa_adventures",
        forecast_for_date="2026-05-10",
        generated_at="2026-05-09T08:00:00Z",
        weather=WeatherSignal(
            date="2026-05-10", condition="heavy_rain",
            temperature_c=25.0, precipitation_mm=52.0,
            confidence=0.91, source="mock_weather_mcp",
        ),
        events=[],
        accommodation=AccommodationSignal(
            date="2026-05-10", available_listings=5,
            avg_price_usd=285.0, occupancy_pressure="very_high",
            source="airbnb_mcp",
        ),
        demand_multiplier=1.6,
        demand_trend="above_normal",
        confidence=0.82,
        reasoning="storm + tourists stuck → indoor pivot",
    )


def test_extract_demand_forecast_returns_validated_model(monkeypatch):
    fake = _sample_forecast()
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=fake))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion
    monkeypatch.setattr("structured_outputs._client", fake_client)

    result = extract_demand_forecast(
        raw_agent_text="Storm tomorrow…", context={"business_id": "x"}
    )
    assert isinstance(result, DemandForecast)
    assert result.demand_trend == "above_normal"
    fake_client.beta.chat.completions.parse.assert_called_once()
    kwargs = fake_client.beta.chat.completions.parse.call_args.kwargs
    assert kwargs["response_format"] is DemandForecast
    assert kwargs["temperature"] == 0.0
```

- [ ] **Step 2: Run** → FAILS (NotImplementedError + missing `_client`).

- [ ] **Step 3: Implement minimum**

```python
# structured_outputs.py
from __future__ import annotations

import os

from openai import OpenAI

from models import ActionProposal, DemandForecast, ReActStep

_client = OpenAI(
    base_url=os.getenv("AMD_VLLM_BASE_URL", "http://localhost:8000/v1"),
    api_key="not-needed",
)

_MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"


def extract_demand_forecast(raw_agent_text: str, context: dict) -> DemandForecast:
    completion = _client.beta.chat.completions.parse(
        model=_MODEL,
        messages=[
            {"role": "system", "content": "Extract the demand forecast into the schema. Use null when unknown."},
            {"role": "user", "content": f"Business context: {context}\n\nAnalysis:\n{raw_agent_text}"},
        ],
        response_format=DemandForecast,
        temperature=0.0,
    )
    return completion.choices[0].message.parsed
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(structured): extract_demand_forecast wraps OpenAI parse with schema`.

## Task 2: `extract_action_proposal` always forces `approval_required=True`

- [ ] **Step 1: Add test** — fixture returns a proposal where the model wrongly set `approval_required=False`. Assert post-extract is `True`.

```python
def test_extract_action_proposal_overrides_approval_required(monkeypatch):
    forecast = _sample_forecast()
    bad_proposal = ActionProposal(
        proposal_id="p_001", business_id="nusa_adventures",
        proposed_at="2026-05-09T08:30:00Z", forecast=forecast,
        inventory_actions=[], staffing_actions=[], communications=[],
        estimated_cost_usd=None, reversible=True,
        approval_required=False,  # <-- model lied
        priority="high", summary_for_owner="x", confidence=0.9,
    )
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=bad_proposal))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion
    monkeypatch.setattr("structured_outputs._client", fake_client)

    result = extract_action_proposal(raw_manager_text="…", forecast=forecast)
    assert result.approval_required is True
```

- [ ] **Step 2: Run** → FAILS (NotImplementedError).

- [ ] **Step 3: Implement**

```python
def extract_action_proposal(
    raw_manager_text: str,
    forecast: DemandForecast,
) -> ActionProposal:
    completion = _client.beta.chat.completions.parse(
        model=_MODEL,
        messages=[
            {"role": "system", "content": "Extract the action proposal. approval_required MUST be true. staffing_actions MUST be [] for Tier-2 businesses."},
            {"role": "user", "content": f"Forecast: {forecast.model_dump_json()}\n\nProposal:\n{raw_manager_text}"},
        ],
        response_format=ActionProposal,
        temperature=0.0,
    )
    proposal = completion.choices[0].message.parsed
    proposal.approval_required = True
    return proposal
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(structured): extract_action_proposal hard-overrides approval_required=True`.

## Task 3: Tier-2 businesses force `staffing_actions=[]`

- [ ] **Step 1: Add test** — fixture returns a Tier-2 proposal containing a `StaffingChange`. Assert post-extract `staffing_actions == []`.

```python
def test_extract_action_proposal_tier2_strips_staffing_actions(monkeypatch):
    forecast = _sample_forecast()
    forecast.business_id = "kopi_nusa_cafe"
    bad = ActionProposal(
        proposal_id="p_002", business_id="kopi_nusa_cafe",
        proposed_at="…", forecast=forecast,
        inventory_actions=[],
        staffing_actions=[
            __import__("models").StaffingChange(
                action="add_shift", role="barista", count=1,
                date="2026-05-10", reason="busy",
            )
        ],
        communications=[],
        estimated_cost_usd=None, reversible=True,
        priority="medium", summary_for_owner="x", confidence=0.8,
    )
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(parsed=bad))]
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = fake_completion
    monkeypatch.setattr("structured_outputs._client", fake_client)

    result = extract_action_proposal(raw_manager_text="…", forecast=forecast)
    assert result.staffing_actions == []
```

- [ ] **Step 2: Run** → FAILS.

- [ ] **Step 3: Update impl** — after override, look up `business_id` tier and strip if 2. Tier lookup reads `mock/fixtures/<business_id>/business.json`.

```python
import json
from pathlib import Path
_FIXTURES = Path(__file__).parent / "mock" / "fixtures"

def _is_tier2(business_id: str) -> bool:
    profile = json.loads((_FIXTURES / business_id / "business.json").read_text())
    return int(profile.get("tier", 1)) == 2

# In extract_action_proposal, after `proposal.approval_required = True`:
    if _is_tier2(proposal.business_id):
        proposal.staffing_actions = []
    return proposal
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(structured): Tier-2 proposals always have empty staffing_actions`.

## Task 4: `extract_react_step` overrides agent_role + step_index

- [ ] Add test where the mocked parse returns a step with `agent_role="WrongAgent", step_index=99`. Assert the returned step has `agent_role` and `step_index` from the caller args.
- [ ] Implement: same parse pattern, then `step.agent_role = agent_role; step.step_index = step_index; return step`.
- [ ] Commit — `feat(structured): extract_react_step pins agent_role and step_index from caller`.

## Task 5: Live round-trip (skip without vLLM)

- [ ] Add `@pytest.mark.live` test that imports the real `_client`, sends a synthetic forecaster paragraph, and asserts the returned `DemandForecast` has reasonable values (multiplier ∈ [0,5], non-empty reasoning).
- [ ] Skip-condition: `pytest.importorskip("openai")` and `pytest.skip()` if `os.getenv("AMD_VLLM_BASE_URL")` is missing.
- [ ] Commit — `test(structured): live round-trip via vLLM endpoint`.

## Task 6: Update Slice-0 stub test

- [ ] Delete `test_structured_outputs_extractors_stubbed` from `tests/test_stubs.py`.
- [ ] Run `pytest -m "not live and not postgres"` → all green.
- [ ] Commit — `chore: drop slice-0 stub guard for structured_outputs`.

## Verification

```bash
pytest tests/test_structured_outputs.py -v
pytest -m "not live and not postgres"
# With AMD_VLLM_BASE_URL set:
pytest -m live
```

## Out of scope

- Streaming, retries framework, prompt caching → hackathon scope cut
- Real model fine-tuning, RLHF prompt iteration

## Source-of-truth pointers

- spec §5 (Pydantic schemas — DO NOT redefine)
- spec §7 (extraction patterns + system prompts — copy verbatim where possible)
- spec §11a (Tier-2 = café, no staffing rule)
