# Slice 4 — Streamlit Multipage Frontend

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans` or `superpowers:subagent-driven-development`. Tests use checkbox `- [ ]`.

**Goal:** Build the 4-page Streamlit app that the owner uses to pick a business, see pending `ActionProposal` cards, approve/reject them, watch the live ReAct trace, and review history.

**Architecture:** `main.py` is the Streamlit entry. `pages/1_Connect.py` has the DEMO_MODE business picker (no OAuth in hackathon path). `pages/2_Dashboard.py` shows pending proposals from `db.get_proposal()` with Approve / Reject buttons that update the `proposals` table and (eventually) flip `owner_approved=True` in the LangGraph checkpoint. `pages/3_Trace.py` renders the ReAct trace from `db`. `pages/4_History.py` lists past proposals + ratings.

**Tech Stack:** Python 3.11, `streamlit==1.40.0`. Tests via `streamlit.testing.v1.AppTest` — no real browser.

**Inputs you can rely on (Slice 0 + Slice 3 contract):**
- `models.{ActionProposal,ReActTrace,ActionFeedback}` — locked
- `db.{save_proposal,get_proposal,save_feedback,get_business}` — Slice 0 implements (or stub if not yet)
- `graph.run_for_business(business_id)` — Slice 3 (in tests, monkey-patch this)

**Files owned (do not edit anything else):**
- `main.py`
- `onboarding.py`
- `pages/1_Connect.py`
- `pages/2_Dashboard.py`
- `pages/3_Trace.py`
- `pages/4_History.py`
- `tests/test_pages.py` (new)

**DO NOT touch:** `models.py`, `crew.py`, `graph.py`, `mcp_tools.py`, `structured_outputs.py`, `db.py`, fixtures.

---

## Task 1: `main.py` runs the multipage app

- [ ] **Step 1: Write failing test** — `tests/test_pages.py`

```python
from streamlit.testing.v1 import AppTest


def test_main_app_loads():
    app = AppTest.from_file("main.py").run()
    assert not app.exception
```

- [ ] **Step 2: Run** → FAIL (NotImplementedError).

- [ ] **Step 3: Implement minimum** `main.py`:

```python
from __future__ import annotations

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="OpsScout", page_icon="🌦", layout="wide")
    st.title("OpsScout")
    st.caption("Use the sidebar to navigate: Connect → Dashboard → Trace → History.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run** → PASS. **Commit** — `feat(ui): main.py boots the multipage app`.

## Task 2: Connect page shows demo businesses (DEMO_MODE)

- [ ] Add test: `AppTest.from_file("pages/1_Connect.py").run()` shows radio with "Nusa Adventures" and "Kopi Nusa Café".
- [ ] Implement `pages/1_Connect.py` reading the business names from the two `business.json` fixtures (no DB hop yet — keep it simple). Selection writes `st.session_state["business_id"]`.
- [ ] Hide OAuth buttons when `DEMO_MODE != "false"`.
- [ ] Commit — `feat(ui): Connect page demo-mode picker`.

## Task 3: Dashboard renders pending proposal card

- [ ] Test: seed an `ActionProposal` via `db.save_proposal`, navigate to dashboard, assert the page text contains `summary_for_owner` and the proposal's priority badge.
- [ ] Implement: read pending proposals via `db.get_proposal_pending(business_id)` (extend `db.py` only if owner exists — coordinate with Slice 0 maintainer; otherwise use raw SQL). Render with `st.container(border=True)`, show summary + bulleted action lists + Approve / Reject buttons.
- [ ] Commit — `feat(ui): Dashboard renders pending proposal card`.

## Task 4: Approve button updates DB + flips checkpoint flag

- [ ] Test: click Approve, assert proposal row's `status='approved'` AND `graph.run_for_business` was re-invoked (monkey-patched).
- [ ] Implement: on click, `db.update_proposal_status(proposal_id, "approved")`. If Slice 3's checkpointer is wired, also write `owner_approved=True` to the LangGraph state thread. If not, leave a TODO + the DB update is enough for the demo.
- [ ] Commit — `feat(ui): Approve flow updates DB and resumes graph`.

## Task 5: Trace page renders ReAct steps in order

- [ ] Test: seed a `ReActTrace` with 3 steps, assert page renders thoughts + tool calls + observations in order, with step indices visible.
- [ ] Implement: `pages/3_Trace.py` reads the latest trace for the selected business and renders each step in an `st.expander` with status icons (🤔 thought, 🛠 tool, 👀 observation, ✅ if `is_final`).
- [ ] Commit — `feat(ui): Trace page renders ReAct steps`.

## Task 6: History page lists past proposals

- [ ] Test: seed 2 proposals (one approved, one rejected), assert page shows both with status labels.
- [ ] Implement: simple `st.dataframe(...)` over `db.list_proposals(business_id)`. Columns: `proposed_at`, `summary_for_owner`, `status`, optional 👍/👎 from `action_feedback`.
- [ ] Commit — `feat(ui): History page shows past proposals + feedback`.

## Task 7: `onboarding.py`

- [ ] Test: `render_onboarding()` shows a "Welcome" header and the same picker as Connect when DEMO_MODE.
- [ ] Implement to match. In production (`DEMO_MODE=false`), it would show OAuth buttons — leave them as `st.button("Connect Shopify", disabled=True)` placeholders for the hackathon.
- [ ] Commit — `feat(ui): onboarding entry point`.

## Task 8: Update Slice-0 stub tests

- [ ] Delete `test_main_entry_stubbed`, `test_onboarding_render_stubbed`, and `test_streamlit_page_module_raises_not_implemented` from `tests/test_stubs.py`.
- [ ] Run full suite — `pytest -m "not live and not postgres"` → all green.
- [ ] Commit — `chore: drop slice-0 stub guards for streamlit pages`.

## Verification

```bash
pytest tests/test_pages.py -v
streamlit run main.py
# Then click through: Connect → Dashboard → Trace → History
```

## Out of scope

- Real OAuth (Shopify, Google, Slack) — buttons are no-op placeholders
- Real-time SSE/WebSocket polling — page reruns on user interaction is sufficient
- Mobile-responsive layout

## Source-of-truth pointers

- spec §11 (Onboarding flow — DEMO_MODE picker)
- spec §12 (Streamlit page list)
- spec §13 (demo script — what the dashboard should look like)
