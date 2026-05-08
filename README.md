# OpsScout — Autonomous Demand Intelligence for Event-Driven Businesses

## What It Does

OpsScout is a multi-agent system that watches weather, local events, and
nearby accommodation occupancy to predict demand spikes — then proposes
staffing, inventory, and communication actions for owner approval. The
agent never self-executes: every action ships through a single
`ActionProposal` that the owner approves in the Streamlit dashboard.

## Track

Track 1: AI Agents & Agentic Workflows  
Submitted to: AMD × lablab.ai Developer Hackathon  
Targeting: Best Overall + Best of Qwen

## Tech Stack

- **LLM:** Qwen3-30B-A3B-Instruct via vLLM on AMD MI300X
- **Agent Frameworks:** CrewAI 0.80 (multi-agent crew) + LangGraph 0.2.55 (durable state machine with PostgresSaver)
- **Structured Outputs:** OpenAI SDK 1.51 `beta.chat.completions.parse()` with Pydantic 2.9 models
- **MCP Servers:** open-meteo (weather), AirBnB, Events, Google Calendar, Gmail, Slack — mock-aware in DEMO_MODE
- **Frontend:** Streamlit 1.40 (4-page multipage app)
- **Database:** PostgreSQL 15+ for proposals, feedback, historical demand, and LangGraph checkpoints

## The Differentiator

OpsScout's hero feature is the **Airbnb occupancy signal**: it converts
"tourists are stuck" into concrete operational actions. When listings are
scarce and prices have spiked, demand for nearby experiences won't drop
just because a storm hits — the agent reasons about which products to
cancel and which to expand.

## ReAct Loop

The Trace page (`pages/3_Trace.py`) shows the live ReAct trace for the
current run — Thought → Tool → Observation per agent step. See spec §13
for the demo timeline.

[Demo video link — to be added in Slice 5]

## How to Run

1. `git clone https://github.com/<user>/opsscout.git && cd opsscout`
2. `python3 -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. `cp .env.example .env` and fill in:
   - `AMD_VLLM_BASE_URL` — your AMD Developer Cloud vLLM endpoint
   - `DATABASE_URL` — local PostgreSQL connection string
5. Make sure PostgreSQL is running, then `python seed.py` to populate businesses + 30 days of synthetic history.
6. `streamlit run main.py`

The default `DEMO_MODE=true` loads pre-seeded businesses (Nusa Adventures
+ Kopi Nusa Café) — no OAuth or external API access needed.

## AMD GPU Usage

All inference runs on `Qwen3-30B-A3B-Instruct` served via vLLM on the AMD
Developer Cloud MI300X instance. The MoE 30B-A3B model fits the
192GB VRAM with `--max-model-len 32768`, exposing an OpenAI-compatible
`/v1/chat/completions` endpoint with `--tool-call-parser hermes`.

Endpoint URL: `[TO BE FILLED IN SLICE 0.5]`

## Repo Layout

See `opsscout_technical_spec.md` §14 for the canonical layout. Slice
ownership is documented in `~/.claude/plans/check-opsscout-technical-spec-md-and-dra-mighty-goblet.md`
(the master plan) and `docs/plans/slice-N-*.md` (per-slice TDD plans for
parallel cs workers).

## Tests

```bash
# Fast local tests (no postgres, no live LLM)
pytest -m "not live and not postgres"

# Postgres-backed tests (requires DATABASE_URL reachable)
pytest -m postgres

# Live tests (requires AMD_VLLM_BASE_URL reachable)
pytest -m live
```

The pre-commit hook runs the first command automatically.

## Status

Hackathon submission build — solo developer. See `docs/plans/` for the
slice plan files driving parallel implementation via Claude Squad.
