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

- **LLM:** Qwen3-30B-A3B-Instruct-2507 via vLLM on AMD MI300X
- **Agent Frameworks:** CrewAI 0.80 (multi-agent crew) + LangGraph 0.2.55 (durable state machine with PostgresSaver)
- **Structured Outputs:** OpenAI SDK 1.58 `beta.chat.completions.parse()` with Pydantic 2.10 models
- **Real data providers (DEMO_MODE=false):** [Open-Meteo](https://open-meteo.com/) for weather, [@openbnb/mcp-server-airbnb](https://www.npmjs.com/package/@openbnb/mcp-server-airbnb) for accommodation occupancy (the same MCP server [AMD's ROCm pydantic-ai+vLLM tutorial](https://rocm.docs.amd.com/projects/ai-developer-hub/en/latest/notebooks/inference/build_airbnb_agent_mcp.html) uses), [PredictHQ](https://www.predicthq.com/) for events. Cached read-through at `mock/cache/`. DEMO_MODE=true falls back to fixtures.
- **Frontend:** Streamlit 1.40 (4-page multipage app)
- **Database:** PostgreSQL 15+ for proposals, feedback, historical demand, and LangGraph checkpoints

## The Differentiator

OpsScout's hero feature is the **Airbnb occupancy signal**: it converts
"tourists are stuck" into concrete operational actions. When listings are
scarce and prices have spiked, demand for nearby experiences won't drop
just because a storm hits — the agent reasons about which products to
cancel and which to expand.

## Data Sources

When `DEMO_MODE=false`, the dispatcher in `mcp_tools.py` routes external
lookups to real providers and caches the responses at `mock/cache/<key>.json`
so demo replays and tests don't burn quota.

- **Weather — [Open-Meteo](https://open-meteo.com/).** Free for non-commercial
  use, no API key required. WMO weather codes are mapped to the coarse
  conditions the Forecaster reasons about (`clear`, `partly_cloudy`, `fog`,
  `light_rain`, `rain`, `heavy_rain`, `snow`, `thunderstorm`).
- **Accommodation — [@openbnb/mcp-server-airbnb](https://www.npmjs.com/package/@openbnb/mcp-server-airbnb).**
  Open-source MCP server invoked over stdio via the official `mcp` Python
  SDK; same server pattern as AMD's published ROCm + Qwen3 + pydantic-ai
  [Airbnb agent tutorial](https://rocm.docs.amd.com/projects/ai-developer-hub/en/latest/notebooks/inference/build_airbnb_agent_mcp.html).
  We aggregate `airbnb_search` results into `available_listings` /
  `avg_price_usd`, and derive a baseline by re-querying the same location
  4 weeks out — `accommodation_signal.get_occupancy_pressure` then
  classifies `low / medium / high / very_high`.

  **Caveat:** Airbnb is a *proxy* for accommodation occupancy. Short-term
  rental coverage varies by destination, and the signal under-counts
  hotels, hostels, villas booked direct, and long-stay rentals. The
  signal is directionally useful — the same listings tracked over time
  reveal demand inflection — but it's not the universe of accommodation.
  Production deployments should layer in PredictHQ's `phq_attendance` or
  hotel-supply APIs for fuller coverage. The MCP server is also
  scraper-based and runs with `--ignore-robots-txt`; respect Airbnb's
  ToS and rate-limit accordingly.
- **Events — [PredictHQ](https://www.predicthq.com/).** REST API with a
  14-day free trial that's enough for the hackathon window. Bearer
  `PHQ_TOKEN` in `.env`. Events are filtered by lat/lng radius and the
  next 7 days, and `phq_attendance` becomes the Forecaster's
  `estimated_attendance` input.

`inventory`, `calendar`, and `business` lookups continue to read fixtures
even in live mode — Shopify / Square / Google Calendar wiring is out of
scope for this submission.

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
   - `PHQ_TOKEN` — only needed if you set `DEMO_MODE=false` and want live PredictHQ events
5. Make sure PostgreSQL is running, then `python seed.py` to populate businesses + 30 days of synthetic history.
6. `streamlit run main.py`

The default `DEMO_MODE=true` loads pre-seeded businesses (Nusa Adventures
+ Kopi Nusa Café) — no OAuth or external API access needed.

## AMD GPU Usage

All inference runs on `Qwen3-30B-A3B-Instruct-2507` served via vLLM on the AMD
Developer Cloud MI300X instance. The MoE 30B-A3B model fits the
192GB VRAM with `--max-model-len 32768`, exposing an OpenAI-compatible
`/v1/chat/completions` endpoint with `--tool-call-parser hermes`.

Endpoint URL: set via `AMD_VLLM_BASE_URL` in `.env` (gitignored). For development we use an SSH tunnel from the laptop to the droplet's port 8000 — typically `http://localhost:8001/v1` after `ssh -N -L 8001:localhost:8000 root@<droplet-ip>`. See `infra/vllm.md` for the full provisioning runbook.

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

# Live-provider tests (requires PHQ_TOKEN + npx in PATH)
pytest -m live_provider
```

The pre-commit hook runs the first command automatically.

## Status

Hackathon submission build — solo developer. See `docs/plans/` for the
slice plan files driving parallel implementation via Claude Squad.
