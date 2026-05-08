# Slice 5 — Integration, Demo Recording, Submission

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans`. Tests use checkbox `- [ ]`.

**Goal:** Wire all 4 parallel slices together, run end-to-end against the live vLLM endpoint, record the ≤5-minute demo video, finalize the README, and submit to lablab.ai.

**Architecture:** Sequential slice — assumes Slices 1–4 have merged into `main`. This slice does not introduce new modules; it integrates existing ones, surfaces and fixes E2E bugs, and produces the deliverables (video + submission form + README + 3 build-in-public threads).

**Tech Stack:** Same as the rest. New testing dep: `pytest -m live` against the AMD MI300X vLLM endpoint.

**Inputs you can rely on:**
- All Pydantic models locked
- `mcp_tools.get_tool_result` reads fixtures
- `accommodation_signal.get_occupancy_pressure` returns validated signals
- `structured_outputs.extract_*` round-trip via vLLM
- `crew.run_crew` produces an `ActionProposal`
- `graph.run_for_business` suspends + resumes via PostgresSaver
- Streamlit pages render and accept Approve clicks

**Files owned (this slice):**
- `tests/test_e2e.py` (new)
- `README.md` (final form)
- `infra/demo_runbook.md` (new)
- Demo video file (NOT committed — gitignored)
- lablab.ai submission form fields (external)

**DO NOT touch:** `models.py`, fixtures, agent role/goal/backstory text. Tweaks to system prompts and demand multipliers are acceptable here, but flag them in the commit message.

---

## Task 1: E2E test for Nusa Adventures

- [ ] **Step 1: Pre-flight**
  ```bash
  python seed.py
  pytest -m "not live and not postgres"  # all green from Slices 1–4
  ```

- [ ] **Step 2: Write live E2E test** — `tests/test_e2e.py`

```python
from __future__ import annotations

import os

import pytest

from graph import run_for_business


@pytest.mark.live
@pytest.mark.postgres
def test_full_run_for_nusa_adventures(pg_conn):
    if not os.getenv("AMD_VLLM_BASE_URL"):
        pytest.skip("AMD_VLLM_BASE_URL not reachable")
    proposal = run_for_business("nusa_adventures")
    assert proposal.business_id == "nusa_adventures"
    assert proposal.approval_required is True
    summary = proposal.summary_for_owner.lower()
    assert "surf" in summary or "rain" in summary
    assert any(
        "rain poncho" in item.name.lower()
        for item in proposal.inventory_actions
    )
```

- [ ] **Step 3: Run** with both env vars set. Iterate on agent prompts until proposal is sensible (mentions surf cancellation + poncho reorder).
- [ ] **Step 4: Commit** — `test(e2e): Nusa Adventures storm scenario produces sensible proposal`.

## Task 2: E2E test for Kopi Nusa Café (Tier-2 guard)

- [ ] Add `tests/test_e2e.py::test_full_run_for_kopi_nusa_cafe`. Live + postgres. Assert:
  - `proposal.staffing_actions == []` (Tier-2 guard)
  - At least one inventory action mentions `fresh_milk` (the quiet-rainy-week scenario)
  - `proposal.approval_required is True`
- [ ] Iterate on prompts until the milk reduction shows up reliably.
- [ ] Commit — `test(e2e): Kopi Nusa scenario triggers milk reduction with no staffing`.

## Task 3: Streamlit + vLLM smoke

- [ ] Run `streamlit run main.py`.
- [ ] Click through: Connect → pick Nusa → Dashboard "Run forecast" button → wait → see proposal card → Approve → confirm execution log appears.
- [ ] Switch to Kopi Nusa → run forecast → see no staffing actions, milk reduction visible.
- [ ] Open Trace page → confirm at least 5 ReAct steps for the Forecaster.
- [ ] If anything looks broken, file the issue back in the responsible slice (don't fix in Slice 5 unless trivial).

## Task 4: Demo recording (≤5 min, 1080p)

- [ ] Use the timeline from spec §13 verbatim.
- [ ] Record voiceover script:
  - 0:00–0:20 problem statement
  - 0:20–2:00 live ReAct trace for Nusa
  - 2:00–3:00 ActionProposal card + Approve flow
  - 3:00–3:45 Kopi Nusa contrast
  - 3:45–4:15 Airbnb signal close-up
  - 4:15–5:00 architecture slide
- [ ] Save as `opsscout-demo.mov` in repo root (gitignored). Upload to YouTube/Vimeo unlisted; capture URL.
- [ ] Document the recording rig in `infra/demo_runbook.md`.
- [ ] Commit — `docs(infra): demo runbook + recording notes`.

## Task 5: Final README

- [ ] Use spec §16 template. Fill in:
  - AMD MI300X endpoint URL or note that it's set via `.env` only
  - Demo video link
  - "How to run" steps including `python seed.py` and `streamlit run main.py`
- [ ] Commit — `docs: final README for submission`.

## Task 6: lablab.ai submission

- [ ] Go to lablab.ai hackathon submission form.
- [ ] Fill: project name, one-line pitch (spec §1), tech stack, demo video, GitHub repo URL.
- [ ] Confirm Track 1 (AI Agents & Agentic Workflows) + check "Best of Qwen" prize.
- [ ] Submit.

## Task 7: Build-in-public

- [ ] Post 3 threads on X / LinkedIn with `#AMDDevHackathon`. Suggested topics:
  1. The Airbnb-occupancy-as-demand-signal insight
  2. Why Tier-1 vs Tier-2 — same agent stack, different proposal shape
  3. The CrewAI + LangGraph hybrid pattern (CrewAI for agent abstractions, LangGraph for durable suspend/resume)

## Verification

```bash
# Local
python seed.py
pytest -m "not live and not postgres"

# With AMD_VLLM_BASE_URL + DATABASE_URL set
pytest -m "live and postgres"
pytest -m live
pytest -m postgres

streamlit run main.py
# manual click-through per Task 3
```

## Out of scope

- Real production deployment (Railway / Fly / Vercel)
- Real OAuth implementation
- Production CI/CD pipelines
- Post-hackathon roadmap (see spec §15 for future improvements)

## Source-of-truth pointers

- spec §13 (demo script — copy timing verbatim)
- spec §16 (README template)
- spec §15 (out-of-scope future improvements — do NOT build for hackathon)
