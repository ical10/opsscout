# Slice 3 — CrewAI Crew + LangGraph State Machine

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans` or `superpowers:subagent-driven-development`. Tests use checkbox `- [ ]`.

**Goal:** Build the 5-agent CrewAI crew (Forecaster, DemandModeler, LogisticsAgent, CommsAgent, OpsManager) and the LangGraph state machine that wraps them with PostgresSaver checkpointing for human-in-the-loop approval.

**Architecture:** CrewAI gives idiomatic agent definitions; LangGraph gives the durable state machine + the suspend-at-`await_approval` / resume-on-flag pattern. `crew.run_crew(business_id)` orchestrates the agents and returns a validated `ActionProposal`. `graph.run_for_business(business_id)` builds the graph, runs it through `await_approval`, persists state, and re-enters when `owner_approved=True` is set in the checkpoint by the Streamlit UI.

**Tech Stack:** Python 3.11, `crewai==0.80.0`, `langgraph==0.2.55`, `langgraph-checkpoint-postgres==2.0.7`, `langchain-openai==0.2.14`, pydantic 2.9.2, pytest 8.3.3 + pytest-mock + pytest-asyncio.

**Inputs you can rely on (Slice 0 + Slice 1 + Slice 2 contracts):**
- `models` — every Pydantic class locked
- `mcp_tools.get_tool_result(tool, business_id, params)` — Slice 1 (use `monkeypatch` in tests if Slice 1 hasn't merged yet)
- `structured_outputs.{extract_demand_forecast,extract_action_proposal,extract_react_step}` — Slice 2 (same monkeypatch trick)
- `graph.BusinessState` — TypedDict already defined in stub
- `graph.{build_graph,run_for_business}` — currently raise `NotImplementedError`

**Files owned (do not edit anything else):**
- `crew.py`
- `graph.py`
- `tests/test_crew.py` (new)
- `tests/test_graph.py` (new)

**Postgres prerequisite:** `tests/test_graph.py` checkpointer tests need `DATABASE_URL` reachable; auto-skip via `pg_conn` fixture in `tests/conftest.py`. CrewAI tests do not touch postgres.

---

## Task 1: 5 agents instantiate with verbatim role/goal/backstory

- [ ] **Step 1: Write failing test** — `tests/test_crew.py`

```python
from __future__ import annotations

from crew import (
    comms_agent,
    demand_modeler,
    forecaster,
    logistics_agent,
    ops_manager,
)


def test_forecaster_role_goal_backstory_match_spec():
    assert forecaster.role == "Demand Forecaster"
    assert "weather, local event, and accommodation occupancy" in forecaster.goal
    assert "data analyst" in forecaster.backstory.lower()


def test_all_five_agents_present():
    assert demand_modeler.role == "Demand Modeler"
    assert logistics_agent.role == "Logistics Agent"
    assert comms_agent.role == "Communications Agent"
    assert ops_manager.role == "Operations Manager"
```

- [ ] **Step 2: Run** → FAIL (ImportError on agents).

- [ ] **Step 3: Implement** — copy spec §6 verbatim, including the `llm = ChatOpenAI(...)` block pointing at `AMD_VLLM_BASE_URL`. Wrap in module-level constants so tests can import. Do not change role/goal/backstory text.

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `feat(crew): instantiate 5 agents per spec §6`.

## Task 2: `run_crew` orchestrates extractors in correct order

- [ ] **Step 1: Add test** monkey-patching `mcp_tools.get_tool_result` and `structured_outputs.extract_*`. Track call order with a list, assert `get_tool_result(weather)` → `get_tool_result(events)` → `get_tool_result(airbnb)` → `extract_demand_forecast` → `get_tool_result(inventory)` → `get_tool_result(calendar)` → `extract_action_proposal`.

```python
def test_run_crew_calls_in_correct_order(monkeypatch):
    calls: list[tuple] = []
    def fake_tool(tool, business_id, params=None):
        calls.append(("tool", tool))
        return {"items": []} if tool == "inventory" else {"results": [], "events": [], "zones": {}, "source": "x", "staff_availability": []}
    def fake_forecast(*a, **kw):
        calls.append(("extract_demand_forecast",))
        from models import AccommodationSignal, WeatherSignal, DemandForecast
        return DemandForecast(
            business_id="nusa_adventures", forecast_for_date="2026-05-10",
            generated_at="2026-05-09T08:00:00Z",
            weather=WeatherSignal(date="2026-05-10", condition="x",
                temperature_c=25.0, precipitation_mm=0.0, confidence=0.5, source="m"),
            events=[],
            accommodation=AccommodationSignal(date="2026-05-10",
                available_listings=10, avg_price_usd=100.0,
                occupancy_pressure="medium", source="airbnb_mcp"),
            demand_multiplier=1.0, demand_trend="normal",
            confidence=0.8, reasoning="x")
    def fake_proposal(*a, **kw):
        calls.append(("extract_action_proposal",))
        # …build a valid ActionProposal pointing at the forecast above…
    monkeypatch.setattr("mcp_tools.get_tool_result", fake_tool)
    monkeypatch.setattr("structured_outputs.extract_demand_forecast", fake_forecast)
    monkeypatch.setattr("structured_outputs.extract_action_proposal", fake_proposal)
    from crew import run_crew
    run_crew(business_id="nusa_adventures")
    tool_order = [c[1] for c in calls if c[0] == "tool"]
    assert tool_order.index("weather") < tool_order.index("airbnb")
    assert any(c[0] == "extract_demand_forecast" for c in calls)
    assert any(c[0] == "extract_action_proposal" for c in calls)
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** `run_crew` to call the dispatcher + extractors in the order spec §13 ReAct trace shows. Avoid actually running CrewAI's `Crew(...).kickoff()` in unit tests — wrap the orchestration in a `_orchestrate(state)` helper that the test can drive without real LLM calls.

- [ ] **Step 4: Run** → PASS. **Commit** — `feat(crew): run_crew orchestrates dispatcher + extractors in spec order`.

## Task 3: Graph compiles 6 nodes

- [ ] **Step 1: Write failing test** — `tests/test_graph.py`

```python
from graph import build_graph


def test_build_graph_has_expected_nodes():
    graph = build_graph()
    nodes = set(graph.get_graph().nodes)
    assert {"forecaster", "demand_modeler", "logistics_and_comms", "ops_manager", "await_approval", "execute"} <= nodes
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** `build_graph()` per spec §8 listing — 6 named nodes, conditional edge from `await_approval` based on `owner_approved`. Use `MemorySaver` as a default checkpointer if `DATABASE_URL` unset, otherwise `PostgresSaver` (so unit tests can run without postgres).

- [ ] **Step 4: Run** → PASS. **Commit** — `feat(graph): build_graph wires the 6-node state machine`.

## Task 4: Suspend at `await_approval`, resume on flag

- [ ] **Step 1: Add test** — `tests/test_graph.py::test_graph_suspends_then_resumes_after_approval`. Use a configured graph with monkey-patched extractors. First invocation: graph runs to `await_approval`, returns proposal. Set `owner_approved=True` in state, re-invoke, assert `execute` ran (state has non-empty `execution_log`).

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** the `should_execute` conditional, the `await_approval` node (returns state unchanged), and `execute` node (appends to `execution_log`).

- [ ] **Step 4: Run** → PASS. **Commit** — `feat(graph): suspend/resume behaviour via owner_approved flag`.

## Task 5: PostgresSaver checkpointer (postgres-marked)

- [ ] **Step 1: Add test** — `tests/test_graph.py::test_postgres_checkpoint_persists`. Marked `@pytest.mark.postgres`. Uses the `pg_conn` fixture. Runs the graph, asserts a row exists in `checkpoints` table for that thread.

- [ ] **Step 2: Run** → SKIPS without DATABASE_URL; FAILS with it.

- [ ] **Step 3: Implement** `run_for_business(business_id)` to use `PostgresSaver(conn).setup()` once + `graph.compile(checkpointer=PostgresSaver)`. Each business uses `thread_id=f"opsscout:{business_id}"`.

- [ ] **Step 4: Run** with postgres → PASS. **Commit** — `feat(graph): PostgresSaver wired for durable checkpoints`.

## Task 6: Update Slice-0 stub tests

- [ ] Delete `test_crew_run_crew_stubbed` and `test_graph_build_and_run_stubbed` from `tests/test_stubs.py`.
- [ ] Run full suite — `pytest -m "not live"` (postgres tests will skip if no DB).
- [ ] Commit — `chore: drop slice-0 stub guards for crew + graph`.

## Verification

```bash
pytest tests/test_crew.py tests/test_graph.py -v
pytest -m "not live and not postgres"
# With DATABASE_URL set:
pytest -m postgres
```

All tests green (or skipped with reason).

## Out of scope

- Real LLM round-trips through CrewAI in tests — too slow + brittle. Slice 5 owns the live E2E.
- Streamlit integration — Slice 4
- Demo recording — Slice 5

## Source-of-truth pointers

- spec §6 (agent definitions, copy verbatim)
- spec §7 (extractor return types — DO NOT redefine)
- spec §8 (LangGraph node listing + edges)
- spec §13 (demo script — implies tool-call ordering)
