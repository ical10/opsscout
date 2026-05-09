# CLAUDE.md

## project
- name: OpsScout
- stack: Python 3.11, CrewAI 0.80, LangGraph 0.2.55 (+ langgraph-checkpoint-postgres 2.0.7), OpenAI SDK 1.51 (vLLM-compatible), pydantic 2.9.2, pydantic-ai 0.0.15, Streamlit 1.40, PostgreSQL 15+, vLLM serving Qwen3-30B-A3B-Instruct-2507 on AMD MI300X
- deployed on: AMD Developer Cloud (vLLM only) + local laptop (Streamlit + Postgres). No production deploy — hackathon submission.
- domain: autonomous demand-intelligence agent for event-driven SMBs (tour operators, cafés). Watches weather + local events + nearby Airbnb occupancy, produces an `ActionProposal` (staffing, inventory, comms) that the owner approves before anything executes.
- solo project — solo developer (Husni); main only, no staging branch
- target: AMD × lablab.ai hackathon — Track 1 (Best Overall) + Best of Qwen
- authoritative spec: `opsscout_technical_spec.md` (sections 1–18)
- master implementation plan: `~/.claude/plans/check-opsscout-technical-spec-md-and-dra-mighty-goblet.md`

## folder structure
```
/                                    ← repo root
  /models.py                         ← Pydantic data contracts (spec §5) — Slice 0 owns
  /db.py                             ← postgres helpers — Slice 0 owns
  /seed.py                           ← seeds businesses + 30d historical demand — Slice 0 owns
  /mcp_tools.py                      ← mock-aware MCP dispatcher — Slice 1 owns
  /accommodation_signal.py           ← Airbnb-derived occupancy pressure — Slice 1 owns
  /structured_outputs.py             ← OpenAI SDK + Pydantic structured-output extractors — Slice 2 owns
  /crew.py                           ← 5 CrewAI agents + Tasks — Slice 3 owns
  /graph.py                          ← LangGraph state machine + PostgresSaver — Slice 3 owns
  /onboarding.py                     ← OAuth-or-DEMO_MODE business connect — Slice 4 owns
  /main.py                           ← Streamlit entry — Slice 4 owns
  /pages/                            ← Streamlit multipage app — Slice 4 owns
    /1_Connect.py
    /2_Dashboard.py
    /3_Trace.py
    /4_History.py
  /mock/
    /scenarios.py                    ← scenario flag → fixture overrides
    /fixtures/
      /nusa_adventures/{business,weather,airbnb,events,inventory,calendar}.json
      /kopi_nusa_cafe/{business,weather,airbnb,events,inventory,calendar}.json
  /tests/                            ← pytest suite (mirrors module under test)
    /conftest.py                     ← sys.path setup + pg_conn / fixtures_dir fixtures
    /test_models.py
    /test_fixtures.py
    /test_db.py
    ... (per-slice test files added by their owning slice)
  /docs/plans/                       ← per-slice TDD plan files (slice-1..5)
  /plans/                            ← pre-coding plan documents (multi-file or new-dep tasks)
  /infra/
    /vllm.md                         ← AMD MI300X provisioning runbook
    /smoke_test.py                   ← gitignored — one-off vLLM smoke
  /.env.example                      ← env template; real .env is gitignored
  /requirements.txt                  ← pinned per spec §17
  /pytest.ini                        ← live + postgres markers
  /opsscout_technical_spec.md        ← authoritative spec
```

## conventions
- Python 3.11 with `from __future__ import annotations` at the top of every module
- Pydantic 2.9.2 for all data contracts; closed enums via `Literal[...]`; field validators where constraints exist
- All LLM extraction via `client.beta.chat.completions.parse()` with a Pydantic schema — never store raw model output
- LangGraph nodes are pure functions over `BusinessState` (TypedDict); side effects only in DB / dispatcher layers
- CrewAI agents instantiated with role/goal/backstory verbatim from spec §6
- pytest 8.3.3 (+ pytest-asyncio 0.24.0, pytest-mock 3.14.0); tests live in `tests/`, named `test_*.py`
- pytest markers (configured in `pytest.ini`):
  - `live` — requires `AMD_VLLM_BASE_URL` reachable
  - `postgres` — requires `DATABASE_URL` pointing at a running postgres
  - default `pytest` run excludes neither, so use `-m "not live and not postgres"` for fast local runs (the pre-commit hook does)
- TDD discipline: red → green → refactor, one failing test per commit before implementation
- conventional commits: `feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`
- no comments by default — only where the code would be genuinely hard to understand without one
- no manager-layer abstractions (no retries framework, session manager, daemon supervisor)
- Slice 0 freezes `models.py`; Slices 1–4 build in parallel git worktrees (claude-squad). Per the master plan's ownership table, a slice never edits files outside its owned set without stopping to ask.

## architecture decisions
- chose Qwen3-30B-A3B-Instruct-2507 on AMD MI300X via vLLM (May 2026): hackathon track is "Best of Qwen" + "Best Overall"; MoE 30B-A3B fits MI300X memory and serves OpenAI-compatible `/v1/*` endpoints with hermes tool-call parser
- chose CrewAI 0.80 + LangGraph 0.2.55 hybrid (May 2026): CrewAI gives idiomatic agent/role/goal abstractions; LangGraph gives durable state-machine + Postgres-backed checkpointing for human-in-the-loop approval suspend/resume — neither alone covers both needs
- chose `client.beta.chat.completions.parse()` with Pydantic schemas (May 2026): structured output is enforceable at the model boundary; no parsing-prompt brittleness; bubbles `ValidationError` cleanly
- chose mock-aware dispatcher (DEMO_MODE=true) (May 2026): judges never see auth screens; 6 fixture JSON files per business cover weather/airbnb/events/inventory/calendar/business; production MCP path raises `NotImplementedError` until Slice 5 (out of hackathon scope)
- chose Airbnb occupancy as the differentiating demand signal (May 2026): "tourists are here and stuck" → concrete operational actions (more staff, more inventory, on-site activity comms); converts an unused public signal into demand intelligence
- chose Streamlit 1.40 multipage over a custom React app (May 2026): solo dev + 7-day clock; Streamlit ships a 4-page owner dashboard fast and reads/writes through the same Python objects as the agents
- chose two demo businesses — Nusa Adventures (Tier 1, multi-activity tour operator, Bali) and Kopi Nusa Café (Tier 2, café in Ubud) (May 2026): same agent pipeline must produce different proposal shapes (Tier 2 forces empty `staffing_actions`); proves generalization beyond a single vertical
- chose Slice-0-locks-contract execution model (May 2026): four parallel cs workers can build Slices 1–4 against the same Pydantic surface without merge conflicts; final Slice 5 wires + records demo

## current focus
- Slice 0 (Scaffolding & Contracts) — in progress
  - completed: repo layout, `.gitignore`, pinned `requirements.txt`, `.env.example`, `pytest.ini`, `tests/conftest.py`, first failing `WeatherSignal` test (commit `b1d2f06`)
  - in progress: `models.py` (TDD red→green; one Pydantic class at a time per the karpathy-guidelines hook)
  - pending: fixtures JSON for both businesses, `db.py` + `seed.py`, NotImplementedError stubs for Slices 1–4, five `docs/plans/slice-N-*.md` TDD plan files, README skeleton
- Slice 0.5 (vLLM on AMD MI300X) — deferred until Husni is back at the laptop with AMD Cloud access
- Slices 1–4 (parallel cs workers) — blocked on Slice 0 + 0.5 completion
- Slice 5 (integration + demo recording + lablab submission) — blocked on Slices 1–4

## rules
- never commit without running `pytest -m "not live and not postgres"` first (pre-commit hook enforces this)
- never edit `models.py` field definitions once a slice has branched (Slice 0 contract — breaks parallel slices)
- never call an LLM without going through `client.beta.chat.completions.parse()` with a Pydantic schema — never store raw model output
- never call an LLM without a timeout and a structured-output schema
- never dispatch a tool call outside `mcp_tools.get_tool_result(...)` — DEMO_MODE=true is the only path until Slice 5
- never plan or implement an OAuth real-credential flow during the hackathon — DEMO_MODE buttons are stubs
- if a task touches more than 3 files or requires a new dependency, write a plan in `/plans/` first and show it before writing any code
- new Pydantic schemas require at least one happy-path test and one validation-failure test
- AI-generated code touching auth, OAuth, or DB write paths is rewritten by hand before being accepted (per Husni's global rules)
- TDD discipline: write a failing test, commit at red; implement minimum, commit at green; refactor, commit again
- demo recordings (`*.mov`, `*.mp4`, `*.webm`) and `infra/smoke_test.py` are gitignored — never commit them
