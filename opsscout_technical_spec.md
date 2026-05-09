# OpsScout — Technical Specification for Coding Agents

**Version:** 1.0  
**Hackathon:** AMD × lablab.ai Developer Hackathon — Track 1: AI Agents & Agentic Workflows  
**Target Prize:** Best Overall (Track 1) + Best of Qwen (Technology Partner)

---

## 1. Project Overview

OpsScout is an autonomous demand intelligence agent for **event-driven and seasonal businesses** (bazaar vendors, pop-up operators, tour/travel groups) with a secondary tier for **permanent F&B establishments** (cafes, restaurants) scoped to inventory and order management only.

The agent continuously monitors weather, local events, and nearby accommodation occupancy, then proposes staffing, inventory, and communications actions — all gated by a single owner approval before execution.

**One-line pitch for submission:**  
*"OpsScout watches the signals your business can't afford to miss — weather, events, and nearby hotel occupancy — and tells you exactly what to do before the rush hits or the rain comes."*

---

## 2. User Tiers

### Tier 1 — Event-Driven & Seasonal Businesses (Primary)
| Business Type | Key Signals | Agent Actions |
|---|---|---|
| Bazaar / night market food stall | Events, weather, accommodation occupancy | Staffing proposals, prep list, inventory order drafts |
| Pop-up / traveling food operator | Multi-venue event calendar, weather | Venue selection recommendations, go/no-go for upcoming dates |
| Surf / hiking / diving tour operator | Weather (critical), accommodation occupancy | Trip confirm/cancel draft, guest notification draft, logistics adjustments |
| Event catering company | Confirmed bookings + weather + guest count | Ingredient scaling, staff headcount proposal |

### Tier 2 — Permanent F&B (Secondary, Scoped)
| Business Type | Supported Actions | Excluded |
|---|---|---|
| Café / restaurant | Inventory reorder proposals, supplier order drafts, demand-adjusted prep estimates | Staff scheduling (labor law complexity, out of scope) |

---

## 3. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| LLM Inference | `Qwen3-30B-A3B` via vLLM on AMD MI300X | Forecaster, Demand Modeler, Planner |
| Agent Orchestration | **CrewAI** | Role-based multi-agent crew with hierarchical process |
| State Machine / Durability | **LangGraph** (LangChain) | Durable per-business state graph with PostgreSQL checkpointer |
| Structured Outputs | **OpenAI Python SDK** (`openai>=1.30`) with Pydantic models | All critical agent outputs validated before action execution |
| Tool Layer | **PydanticAI** `MCPServerStdio` | MCP server connections |
| Frontend | **Streamlit** | Owner dashboard, approval UI |
| Database | **PostgreSQL** | Business state, action history, feedback log |
| Deployment | AMD Developer Cloud (MI300X) + vLLM | LLM serving |

**Framework requirement satisfied:** CrewAI + LangChain/LangGraph (2 of the required 4).  
**Qwen requirement satisfied:** Qwen3-30B-A3B as the primary reasoning model on AMD MI300X.

---

## 4. vLLM Server Setup

```bash
# On AMD MI300X via AMD Developer Cloud
pip install vllm

vllm serve Qwen/Qwen3-30B-A3B-Instruct-2507 \
  --host 0.0.0.0 \
  --port 8000 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --max-model-len 32768
```

The vLLM server exposes an OpenAI-compatible endpoint at `http://localhost:8000/v1`.  
All OpenAI SDK calls and CrewAI LLM config point to this base URL with `api_key="not-needed"`.

---

## 5. Structured Output Models (OpenAI SDK + Pydantic)

These are the canonical data contracts for all critical agent outputs. Every agent MUST produce one of these validated models — never raw text — for any decision that flows downstream.

Use `client.beta.chat.completions.parse()` from the OpenAI SDK for structured extraction.

```python
# models.py
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

# ── Shared primitives ──────────────────────────────────────────────

class DateRange(BaseModel):
    start: str  # ISO 8601 date string
    end: str

class LocationContext(BaseModel):
    business_name: str
    address: str
    latitude: float
    longitude: float
    radius_km: float = 1.0  # search radius for accommodation/event signals

# ── Forecaster outputs ─────────────────────────────────────────────

class WeatherSignal(BaseModel):
    date: str
    condition: str                              # e.g. "heavy rain", "clear"
    temperature_c: float
    precipitation_mm: float
    confidence: float = Field(ge=0.0, le=1.0)
    source: str                                 # MCP server name

class EventSignal(BaseModel):
    name: str
    date: str
    estimated_attendance: int | None
    distance_m: float
    category: str                               # e.g. "music", "food", "sports"
    source: str

class AccommodationSignal(BaseModel):
    date: str
    available_listings: int
    avg_price_usd: float
    occupancy_pressure: Literal["low", "medium", "high", "very_high"]
    # Derived: low availability + high price = very_high pressure
    source: str                                 # "airbnb_mcp" or "predicthq"

class DemandForecast(BaseModel):
    """
    Primary output of the Forecaster agent.
    This is the single most important structured model in the system.
    All downstream agents consume this before proposing actions.
    """
    business_id: str
    forecast_for_date: str                      # ISO 8601
    generated_at: str                           # ISO 8601 datetime
    weather: WeatherSignal
    events: list[EventSignal]
    accommodation: AccommodationSignal
    demand_multiplier: float = Field(
        ge=0.0, le=5.0,
        description=(
            "Multiplier relative to baseline. "
            "1.0 = normal day. 2.0 = expect double foot traffic. "
            "0.5 = expect half."
        )
    )
    demand_trend: Literal["spike", "above_normal", "normal", "below_normal", "drop"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str  # Human-readable explanation of how the multiplier was derived

# ── ReAct trace ────────────────────────────────────────────────────

class ReActStep(BaseModel):
    """
    One iteration of the Reason → Act → Observe loop.
    Logged for every agent turn. Shown in the Streamlit trace panel.
    """
    step_index: int
    agent_role: str                             # e.g. "Forecaster", "LogisticsAgent"
    thought: str                                # Internal reasoning before acting
    tool_called: str | None                     # MCP tool name, or None if no tool
    tool_input: dict | None                     # Serialized tool arguments
    observation: str | None                     # Tool result summary
    is_final: bool = False                      # True on the last step before output

class ReActTrace(BaseModel):
    """Full trace for one agent task. Stored in DB and shown in UI."""
    task_id: str
    business_id: str
    agent_role: str
    steps: list[ReActStep]
    final_output_type: str                      # e.g. "DemandForecast", "ActionProposal"

# ── Action proposals ───────────────────────────────────────────────

class InventoryItem(BaseModel):
    name: str
    current_quantity: float
    unit: str
    suggested_order_quantity: float
    estimated_cost_usd: float | None
    supplier_name: str | None

class StaffingChange(BaseModel):
    """
    Only used for Tier 1 (event-driven) businesses.
    Tier 2 (permanent F&B) does NOT receive staffing proposals.
    """
    action: Literal["add_shift", "extend_shift", "reduce_shift", "cancel_shift"]
    role: str                                   # e.g. "server", "cashier", "guide"
    count: int
    date: str
    reason: str

class CommunicationDraft(BaseModel):
    channel: Literal["whatsapp", "email", "sms", "instagram_caption"]
    recipient: str                              # "guests", "staff", "supplier"
    subject: str | None                         # For email only
    body: str
    urgency: Literal["low", "medium", "high"]

class ActionProposal(BaseModel):
    """
    The final output of the OpsManager agent.
    Every action requiring real-world execution must be wrapped in this model.
    NOTHING executes without owner approval of this model.
    """
    proposal_id: str                            # UUID
    business_id: str
    proposed_at: str                            # ISO 8601 datetime
    forecast: DemandForecast                    # The forecast that triggered this
    
    # Actions — each list may be empty if not applicable to the business tier
    inventory_actions: list[InventoryItem]
    staffing_actions: list[StaffingChange]      # Empty for Tier 2
    communications: list[CommunicationDraft]
    
    # Control fields
    estimated_cost_usd: float | None
    reversible: bool                            # False = requires extra confirmation
    approval_required: bool = True              # Always True — agent never self-executes
    priority: Literal["low", "medium", "high", "urgent"]
    
    # Shown to owner in Streamlit UI
    summary_for_owner: str                      # 2-sentence plain-English summary
    confidence: float = Field(ge=0.0, le=1.0)

# ── Feedback (Future Improvement — see Section 11) ─────────────────

class ActionFeedback(BaseModel):
    """
    Stored after the owner rates a completed action the following day.
    Used for human evaluation and future agent improvement.
    """
    feedback_id: str
    proposal_id: str
    business_id: str
    submitted_at: str                           # ISO 8601 datetime
    rating: Literal["thumbs_up", "thumbs_down"]
    free_text: str | None                       # Optional comment
    was_accurate: bool | None                   # Did the forecast match reality?
```

---

## 6. Agent Crew (CrewAI)

Four specialist agents orchestrated by a hierarchical CrewAI process. The OpsManager is the manager agent; the others are workers.

```python
# crew.py
from crewai import Agent, Crew, Task, Process
from langchain_openai import ChatOpenAI

# Point CrewAI at the local vLLM endpoint
llm = ChatOpenAI(
    model="Qwen3-30B-A3B-Instruct-2507",
    base_url="http://localhost:8000/v1",
    api_key="not-needed",
    temperature=0.3,
)

forecaster = Agent(
    role="Demand Forecaster",
    goal=(
        "Gather weather, local event, and accommodation occupancy data "
        "for the next 7 days around the business location. "
        "Produce a validated DemandForecast structured output for each day."
    ),
    backstory=(
        "You are a data analyst who has spent years reading market signals "
        "for small hospitality and events businesses. You never guess — "
        "you cite your sources and express uncertainty with a confidence score."
    ),
    llm=llm,
    verbose=True,
)

demand_modeler = Agent(
    role="Demand Modeler",
    goal=(
        "Take the DemandForecast and the business's historical sales/order data "
        "to translate the demand multiplier into concrete quantities: "
        "how many portions to prep, how much stock to order, "
        "how many guests to expect."
    ),
    backstory=(
        "You are an operations researcher who builds simple, explainable models. "
        "You turn abstract demand signals into actionable numbers "
        "a business owner can act on immediately."
    ),
    llm=llm,
    verbose=True,
)

logistics_agent = Agent(
    role="Logistics Agent",
    goal=(
        "Using the modeled demand quantities, produce inventory order proposals "
        "and — for Tier 1 businesses only — staffing change proposals. "
        "Check the business tier before including staffing actions. "
        "Never include staffing for Tier 2 (cafes, restaurants)."
    ),
    backstory=(
        "You are a seasoned operations manager for SMBs. "
        "You know exactly which levers to pull 48 hours before a demand event. "
        "You are conservative: you never over-order and you always flag cost."
    ),
    llm=llm,
    verbose=True,
)

comms_agent = Agent(
    role="Communications Agent",
    goal=(
        "Draft all outbound communications triggered by the operational plan: "
        "guest notifications, staff scheduling messages, supplier order emails. "
        "Match the channel and tone to the business type. "
        "Never send anything — only draft for owner approval."
    ),
    backstory=(
        "You write like the business owner themselves — casual for a food stall, "
        "professional for a tour operator. You are concise. "
        "You always end draft messages with [PENDING OWNER APPROVAL]."
    ),
    llm=llm,
    verbose=True,
)

ops_manager = Agent(
    role="Operations Manager",
    goal=(
        "Merge the logistics plan and communications drafts into a single "
        "ActionProposal structured output. Gate everything behind "
        "approval_required=True. Surface only the top 3 actions if there are many. "
        "Write the summary_for_owner in plain English, no jargon."
    ),
    backstory=(
        "You are the agent the business owner talks to. "
        "You translate the work of four specialists into a single, clear "
        "recommendation the owner can approve in under 30 seconds."
    ),
    llm=llm,
    verbose=True,
)
```

---

## 7. Structured Output Extraction (OpenAI SDK)

Use this pattern for every agent that must produce a validated Pydantic model. Do NOT rely on CrewAI's raw text output for structured data — always extract via the OpenAI SDK parse method.

```python
# structured_outputs.py
from openai import OpenAI
from models import DemandForecast, ActionProposal, ReActStep

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed",
)

def extract_demand_forecast(raw_agent_text: str, context: dict) -> DemandForecast:
    """
    Takes the Forecaster agent's raw output and re-parses it into a
    validated DemandForecast via structured outputs.
    This is the extraction step — NOT a new LLM call for reasoning.
    """
    completion = client.beta.chat.completions.parse(
        model="Qwen3-30B-A3B-Instruct-2507",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a structured data extractor. "
                    "Given the forecaster's analysis, extract the data into "
                    "the exact JSON schema provided. "
                    "Do not add information not present in the input. "
                    "If a field is unknown, use null."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Business context: {context}\n\n"
                    f"Forecaster analysis:\n{raw_agent_text}"
                ),
            },
        ],
        response_format=DemandForecast,
        temperature=0.0,   # Zero temperature for extraction — deterministic
    )
    return completion.choices[0].message.parsed


def extract_action_proposal(raw_manager_text: str, forecast: DemandForecast) -> ActionProposal:
    """
    Extracts the final ActionProposal from the OpsManager's output.
    Always sets approval_required=True regardless of model output.
    """
    completion = client.beta.chat.completions.parse(
        model="Qwen3-30B-A3B-Instruct-2507",
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract the action proposal into the exact JSON schema. "
                    "approval_required MUST be true. "
                    "staffing_actions MUST be empty if this is a Tier 2 business."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Forecast used: {forecast.model_dump_json()}\n\n"
                    f"Manager output:\n{raw_manager_text}"
                ),
            },
        ],
        response_format=ActionProposal,
        temperature=0.0,
    )
    proposal = completion.choices[0].message.parsed
    # Hard override — agent can never bypass approval gate
    proposal.approval_required = True
    return proposal


def extract_react_step(agent_role: str, step_index: int, raw_step_text: str) -> ReActStep:
    """Extracts one ReAct step for the trace log."""
    completion = client.beta.chat.completions.parse(
        model="Qwen3-30B-A3B-Instruct-2507",
        messages=[
            {"role": "system", "content": "Extract the ReAct step fields from this agent output."},
            {"role": "user", "content": f"Agent: {agent_role}\nStep {step_index}:\n{raw_step_text}"},
        ],
        response_format=ReActStep,
        temperature=0.0,
    )
    step = completion.choices[0].message.parsed
    step.agent_role = agent_role
    step.step_index = step_index
    return step
```

---

## 8. LangGraph State Machine

LangGraph wraps the crew execution as a durable state graph. This enables: crash recovery, per-business parallelism, and a persistent audit trail.

```python
# graph.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from typing import TypedDict
from models import DemandForecast, ActionProposal, ReActTrace
import os, psycopg, uuid

class BusinessState(TypedDict):
    business_id: str
    business_tier: int                     # 1 = event-driven, 2 = permanent F&B
    location: dict                         # LocationContext serialized
    connected_integrations: list[str]      # e.g. ["shopify", "google_calendar"]
    forecast: DemandForecast | None
    proposal: ActionProposal | None
    react_trace: ReActTrace | None
    owner_approved: bool
    execution_log: list[str]
    error: str | None

def run_forecaster(state: BusinessState) -> BusinessState:
    # 1. Call MCP tools (Weather, AirBnB, Events) via PydanticAI
    # 2. Run Forecaster CrewAI agent
    # 3. Extract DemandForecast via structured outputs
    # 4. Log ReActTrace steps
    ...
    return {**state, "forecast": forecast, "react_trace": trace}

def run_demand_modeler(state: BusinessState) -> BusinessState:
    # Consumes state["forecast"]
    # Produces modeled quantities (stored in state as intermediate dict)
    ...
    return {**state, "modeled_quantities": quantities}

def run_logistics_and_comms(state: BusinessState) -> BusinessState:
    # LogisticsAgent + CommsAgent run in parallel (LangGraph parallel branch)
    # Both consume state["modeled_quantities"]
    ...
    return {**state, "logistics_output": logistics, "comms_output": comms}

def run_ops_manager(state: BusinessState) -> BusinessState:
    # Merges logistics + comms into ActionProposal
    # Extracts via structured outputs
    # Sets approval_required=True
    ...
    return {**state, "proposal": proposal}

def await_owner_approval(state: BusinessState) -> BusinessState:
    # This node suspends. Streamlit UI writes approval to DB.
    # LangGraph resumes from checkpoint when DB flag is set.
    ...

def execute_approved_actions(state: BusinessState) -> BusinessState:
    # Only reached after owner_approved=True
    # Calls Calendar MCP, Gmail MCP, Slack MCP to execute
    # Logs each execution step
    ...

def should_execute(state: BusinessState) -> str:
    return "execute" if state["owner_approved"] else "wait"

# Build graph
builder = StateGraph(BusinessState)
builder.add_node("forecaster", run_forecaster)
builder.add_node("demand_modeler", run_demand_modeler)
builder.add_node("logistics_and_comms", run_logistics_and_comms)
builder.add_node("ops_manager", run_ops_manager)
builder.add_node("await_approval", await_owner_approval)
builder.add_node("execute", execute_approved_actions)

builder.set_entry_point("forecaster")
builder.add_edge("forecaster", "demand_modeler")
builder.add_edge("demand_modeler", "logistics_and_comms")
builder.add_edge("logistics_and_comms", "ops_manager")
builder.add_edge("ops_manager", "await_approval")
builder.add_conditional_edges("await_approval", should_execute, {
    "execute": "execute",
    "wait": "await_approval",   # re-checks on next poll
})
builder.add_edge("execute", END)

# Durable checkpointer — survives crashes
# Requires: pip install langgraph-checkpoint-postgres psycopg[binary]
import os, psycopg
from langgraph.checkpoint.postgres import PostgresSaver

conn = psycopg.connect(os.environ["DATABASE_URL"])
checkpointer = PostgresSaver(conn)
checkpointer.setup()   # Creates checkpoint tables on first run if they don't exist
graph = builder.compile(checkpointer=checkpointer)
```

---

## 9. MCP Integrations — Mock-Aware Tool Layer

All external tool calls are routed through a single `get_tool_result()` dispatcher. When `DEMO_MODE=true`, it reads from JSON fixtures in `mock/fixtures/`. When `DEMO_MODE=false`, it calls real MCP servers via PydanticAI `MCPServerStdio`. The agents never know the difference — they receive identical data shapes either way.

```python
# mcp_tools.py
import os, json
from pathlib import Path
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
FIXTURES_DIR = Path(__file__).parent / "mock" / "fixtures"

# ── Real MCP servers (used when DEMO_MODE=false) ──────────────────

weather_mcp   = MCPServerStdio("uvx", args=["mcp-server-openmeteo"])
airbnb_mcp    = MCPServerStdio("npx", args=["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"])
calendar_mcp  = MCPServerStdio("npx", args=["-y", "@modelcontextprotocol/server-google-calendar"])
gmail_mcp     = MCPServerStdio("npx", args=["-y", "@modelcontextprotocol/server-gmail"])
slack_mcp     = MCPServerStdio("npx", args=["-y", "@modelcontextprotocol/server-slack"])

# ── Mock dispatcher ───────────────────────────────────────────────

def get_tool_result(tool: str, business_id: str, params: dict = {}) -> dict:
    """
    Central dispatcher for all tool calls.
    In DEMO_MODE, reads from fixture JSON files.
    In production, calls the corresponding MCP server.

    Args:
        tool:        One of: "weather", "airbnb", "events",
                     "inventory", "calendar", "gmail", "slack"
        business_id: "bali_surf_tours" | "kopi_nusa_cafe"
        params:      Optional extra params (e.g. target_date)
    """
    if DEMO_MODE:
        fixture_path = FIXTURES_DIR / business_id / f"{tool}.json"
        with open(fixture_path) as f:
            return json.load(f)
    else:
        # Production: delegate to the appropriate MCP server
        raise NotImplementedError("Wire real MCP calls here in production mode.")
```

**MCP to agent mapping:**

| Tool key | MCP Server (production) | Used By | Purpose |
|---|---|---|---|
| `weather` | open-meteo MCP | Forecaster | Precipitation, temperature, 7-day forecast |
| `airbnb` | AirBnB MCP | Forecaster | Accommodation availability → occupancy pressure |
| `events` | PredictHQ REST / Events MCP | Forecaster | Local events, estimated attendance, distance |
| `inventory` | Shopify / Square MCP | Demand Modeler | Current stock levels, sales velocity |
| `calendar` | Google Calendar MCP | Logistics Agent | Staff availability, existing bookings |
| `gmail` | Gmail MCP | Comms Agent | Draft supplier order emails |
| `slack` | Slack MCP | OpsManager | Owner escalation, approval notification |

---

## 10. Accommodation Occupancy Signal (AirBnB MCP — Core Feature)

This is the feature that differentiates OpsScout. Implement this as a dedicated module so it is clearly demonstrable in the hackathon demo.

```python
# accommodation_signal.py
from models import AccommodationSignal
from datetime import date, timedelta
import statistics

async def get_occupancy_pressure(
    location: str,
    latitude: float,
    longitude: float,
    target_date: date,
    airbnb_agent,           # PydanticAI agent with airbnb_mcp attached
) -> AccommodationSignal:
    """
    Queries AirBnB MCP for listing availability near the business.
    Derives occupancy pressure from available count and average price.

    Logic:
    - Get listings for target_date within 1km radius
    - Compare against a baseline (same weekday, 4 weeks prior)
    - Low availability + price above baseline = high pressure
    """
    # Query target date
    target_result = await airbnb_agent.run(
        f"Search for available Airbnb listings in {location} "
        f"for {target_date.isoformat()} to {(target_date + timedelta(days=1)).isoformat()}. "
        f"Return count and average price."
    )

    # Query baseline (same weekday, 4 weeks ago — already passed, so availability=0 is expected)
    # Instead, query 4 weeks ahead from target as a future baseline
    baseline_date = target_date + timedelta(weeks=4)
    baseline_result = await airbnb_agent.run(
        f"Search for available Airbnb listings in {location} "
        f"for {baseline_date.isoformat()} to {(baseline_date + timedelta(days=1)).isoformat()}. "
        f"Return count and average price."
    )

    # Parse counts and prices from agent output (use structured extraction)
    target_count = parse_listing_count(target_result.output)
    target_price = parse_avg_price(target_result.output)
    baseline_count = parse_listing_count(baseline_result.output)
    baseline_price = parse_avg_price(baseline_result.output)

    # Derive pressure
    availability_ratio = target_count / max(baseline_count, 1)
    price_ratio = target_price / max(baseline_price, 1)

    if availability_ratio < 0.3 and price_ratio > 1.4:
        pressure = "very_high"
    elif availability_ratio < 0.5 or price_ratio > 1.2:
        pressure = "high"
    elif availability_ratio < 0.75:
        pressure = "medium"
    else:
        pressure = "low"

    return AccommodationSignal(
        date=target_date.isoformat(),
        available_listings=target_count,
        avg_price_usd=target_price,
        occupancy_pressure=pressure,
        source="airbnb_mcp",
    )
```

---

## 11. Onboarding Flow

### Demo Mode (Hackathon — Active by Default)

Set `DEMO_MODE=true` in `.env`. The "Connect your tools" screen is replaced by a **pre-seeded business selector** — a Streamlit `selectbox` with two demo businesses already loaded in PostgreSQL by the seed script.

```
┌─────────────────────────────────────────┐
│  👋 Welcome to OpsScout                 │
│                                         │
│  Select a demo business to get started: │
│  ○ Nusa Adventures  (Tier 1)            │
│  ○ Kopi Nusa Café   (Tier 2)            │
│                                         │
│  [ Load Business → ]                    │
└─────────────────────────────────────────┘
```

One click loads the full business context — no forms, no OAuth, no credentials needed. The rest of the app runs identically to production.

### Production Mode (Post-Hackathon)

Set `DEMO_MODE=false`. The selector is replaced by the real OAuth flow:
1. Owner opens OpsScout and is presented with "Connect your tools" buttons:
   - **Shopify** (OAuth 2.0 — orders, products, inventory)
   - **Square** (OAuth 2.0 — orders, inventory)
   - **Google Calendar** (OAuth 2.0 — events, free/busy)
   - **Stripe** (OAuth 2.0 — charges, balance for revenue baseline)
2. After connecting at least one integration, the agent auto-infers business name, address, operating hours, and product catalog from the platform profile.
3. Owner confirms their business tier with a single radio button.

### Fallback path (both modes)
A 3-field form (business name, location, category) for businesses with no supported integrations. Enough to run weather + events + accommodation signals.


---

## 11a. Mock Data Layer

### Design principle

`DEMO_MODE=true` is the default. Every external data source — weather, AirBnB, events, inventory, calendar — is replaced by a static JSON fixture file. The agents receive these fixtures exactly as they would receive real API responses. Nothing in the agent logic, structured outputs, or LangGraph graph changes between demo and production mode.

Think of it like a flight simulator: the cockpit controls are real, the physics model is real, only the out-the-window scenery is pre-rendered.

---

### Two Demo Businesses

#### Business A — Nusa Adventures `(Tier 1)`
A mid-sized multi-activity adventure tour operator running parallel product lines out of Seminyak, Bali: surf lessons (Canggu beach), white water rafting (Ayung River), volcano sunrise treks (Mt. Batur), cycling tours (Ubud rice terraces), and cultural day trips. 18 staff. A fleet of 4 vehicles and 2 boats. Coastal, highland, and inland operations running simultaneously.

**Why this works as a demo business:** Coastal and highland zones respond differently to the same weather event. A storm shuts down beach and river activities but leaves highland and cultural tours completely unaffected. This forces the agent to reason *across* product lines — cancel some, expand others, reallocate staff between them — rather than making a single binary decision. The non-obvious insight (redirect storm-displaced tourists to inland activities) is what makes the ReAct trace compelling for judges.

**Scenario baked into fixtures:** A tropical storm hits the Bali coast Saturday–Sunday. Simultaneously, the Bali International Surf Championships (4,200 attendees) is running in Canggu — meaning a large tourist population is already in the area and cannot leave. AirBnB occupancy is very high. The agent cancels surf lessons and rafting, reallocates two freed surf guides to the trekking team, expands Saturday volcano trek capacity from 8 to 14 guests, flags a rain poncho stock shortage, and drafts a guest upgrade offer converting cancelled surf bookings to the volcano trek at no extra cost.

#### Business B — Kopi Nusa Café `(Tier 2)`
A small café near a popular market in Ubud, Bali. Scoped to inventory and supplier orders only — no staffing actions.

**Scenario baked into fixtures:** Quiet rainy week ahead, AirBnB availability is high (off-peak). Agent recommends reducing the next milk and pastry order by 30%, and drafts a supplier email.

---

### Fixture File Specs

All fixture files live in `mock/fixtures/{business_id}/`. Each is a JSON object that mirrors what the real MCP tool would return.

#### `business.json`
```json
{
  "business_id": "nusa_adventures",
  "business_name": "Nusa Adventures",
  "tier": 1,
  "category": "multi_activity_tour_operator",
  "address": "Jl. Nakula No.18, Seminyak, Bali, Indonesia",
  "latitude": -8.6897,
  "longitude": 115.1609,
  "operating_days": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
  "operating_hours": "05:00-20:00",
  "baseline_daily_guests": 42,
  "activity_types": [
    {"id": "surf",     "name": "Surf Lessons",           "zone": "coastal",   "max_capacity": 16, "duration_hrs": 2},
    {"id": "rafting",  "name": "White Water Rafting",    "zone": "river",     "max_capacity": 12, "duration_hrs": 3},
    {"id": "trekking", "name": "Volcano Sunrise Trek",   "zone": "highland",  "max_capacity": 8,  "duration_hrs": 6},
    {"id": "cycling",  "name": "Ubud Cycling Tour",      "zone": "highland",  "max_capacity": 10, "duration_hrs": 4},
    {"id": "cultural", "name": "Ubud Cultural Day Trip", "zone": "inland",    "max_capacity": 14, "duration_hrs": 8}
  ],
  "staff": [
    {"name": "Wayan",   "roles": ["surf_guide", "trekking_support"], "available_sat": true},
    {"name": "Komang",  "roles": ["surf_guide", "cycling_guide"],    "available_sat": true},
    {"name": "Made",    "roles": ["rafting_guide"],                  "available_sat": true},
    {"name": "Kadek",   "roles": ["trek_lead"],                      "available_sat": true},
    {"name": "Nyoman",  "roles": ["trek_lead", "cultural_guide"],    "available_sat": false},
    {"name": "Agus",    "roles": ["driver"],                         "available_sat": true},
    {"name": "Putu",    "roles": ["driver"],                         "available_sat": true}
  ],
  "vehicles": 4,
  "boats": 2,
  "current_staff_count": 18
}
```

#### `weather.json`
```json
{
  "zones": {
    "coastal": {
      "location": "Seminyak / Canggu, Bali",
      "forecast": [
        {"date": "2026-05-09", "condition": "partly_cloudy", "temperature_c": 29, "precipitation_mm": 4,  "wind_kph": 18, "sea_state": "moderate", "confidence": 0.93},
        {"date": "2026-05-10", "condition": "heavy_rain",    "temperature_c": 25, "precipitation_mm": 52, "wind_kph": 45, "sea_state": "rough",    "confidence": 0.91},
        {"date": "2026-05-11", "condition": "thunderstorm",  "temperature_c": 24, "precipitation_mm": 68, "wind_kph": 55, "sea_state": "very_rough","confidence": 0.89},
        {"date": "2026-05-12", "condition": "clear",         "temperature_c": 30, "precipitation_mm": 0,  "wind_kph": 12, "sea_state": "calm",      "confidence": 0.94}
      ]
    },
    "highland": {
      "location": "Kintamani / Mt. Batur / Ubud, Bali",
      "forecast": [
        {"date": "2026-05-09", "condition": "clear",         "temperature_c": 20, "precipitation_mm": 1,  "wind_kph": 8,  "confidence": 0.95},
        {"date": "2026-05-10", "condition": "partly_cloudy", "temperature_c": 18, "precipitation_mm": 6,  "wind_kph": 10, "confidence": 0.92},
        {"date": "2026-05-11", "condition": "partly_cloudy", "temperature_c": 17, "precipitation_mm": 8,  "wind_kph": 12, "confidence": 0.90},
        {"date": "2026-05-12", "condition": "clear",         "temperature_c": 21, "precipitation_mm": 0,  "wind_kph": 6,  "confidence": 0.96}
      ]
    }
  },
  "source": "mock_weather_mcp"
}
```

#### `airbnb.json`
```json
{
  "location": "Seminyak / Canggu, Bali",
  "query_radius_km": 2.0,
  "results": [
    {"date": "2026-05-10", "available_listings": 5,  "avg_price_usd": 285, "baseline_available": 32, "baseline_price_usd": 145},
    {"date": "2026-05-11", "available_listings": 3,  "avg_price_usd": 310, "baseline_available": 32, "baseline_price_usd": 145},
    {"date": "2026-05-12", "available_listings": 22, "avg_price_usd": 180, "baseline_available": 32, "baseline_price_usd": 145}
  ],
  "source": "mock_airbnb_mcp"
}
```

#### `events.json`
```json
{
  "location": "Seminyak / Canggu, Bali",
  "events": [
    {
      "name": "Bali International Surf Championships",
      "date": "2026-05-10",
      "end_date": "2026-05-11",
      "estimated_attendance": 4200,
      "distance_m": 550,
      "category": "sports",
      "visitor_profile": "international_adventure_traveler",
      "source": "mock_events_mcp"
    },
    {
      "name": "Ubud Writers & Readers Festival",
      "date": "2026-05-10",
      "end_date": "2026-05-12",
      "estimated_attendance": 2800,
      "distance_m": 24000,
      "category": "culture",
      "visitor_profile": "premium_cultural_traveler",
      "source": "mock_events_mcp"
    }
  ]
}
```

#### `inventory.json` (Tier 1 — multi-activity equipment)
```json
{
  "items": [
    {"name": "Surfboard 6ft",        "current_quantity": 14, "unit": "units", "reorder_threshold": 6,  "activity": "surf"},
    {"name": "Surfboard 7ft",        "current_quantity": 10, "unit": "units", "reorder_threshold": 4,  "activity": "surf"},
    {"name": "Wetsuit (M)",          "current_quantity": 8,  "unit": "units", "reorder_threshold": 4,  "activity": "surf"},
    {"name": "Helmet (rafting)",     "current_quantity": 12, "unit": "units", "reorder_threshold": 6,  "activity": "rafting"},
    {"name": "Life Jacket",          "current_quantity": 16, "unit": "units", "reorder_threshold": 8,  "activity": "rafting"},
    {"name": "Rain Poncho",          "current_quantity": 4,  "unit": "units", "reorder_threshold": 12, "activity": "trekking"},
    {"name": "Trekking Pole",        "current_quantity": 10, "unit": "units", "reorder_threshold": 8,  "activity": "trekking"},
    {"name": "Headlamp",             "current_quantity": 9,  "unit": "units", "reorder_threshold": 8,  "activity": "trekking"},
    {"name": "Bicycle (adult)",      "current_quantity": 10, "unit": "units", "reorder_threshold": 5,  "activity": "cycling"},
    {"name": "First Aid Kit",        "current_quantity": 3,  "unit": "kits",  "reorder_threshold": 2,  "activity": "all"}
  ],
  "source": "mock_inventory"
}
```

#### `calendar.json`
```json
{
  "staff_availability": [
    {
      "date": "2026-05-10",
      "schedule": [
        {"name": "Wayan",  "assigned_activity": "surf",     "status": "free_if_surf_cancelled"},
        {"name": "Komang", "assigned_activity": "surf",     "status": "free_if_surf_cancelled"},
        {"name": "Made",   "assigned_activity": "rafting",  "status": "free_if_rafting_cancelled"},
        {"name": "Kadek",  "assigned_activity": "trekking", "status": "confirmed"},
        {"name": "Agus",   "assigned_activity": "driver",   "status": "confirmed"},
        {"name": "Putu",   "assigned_activity": "driver",   "status": "confirmed"}
      ],
      "confirmed_bookings": {
        "surf":     {"guests": 14, "slots_total": 16},
        "rafting":  {"guests": 10, "slots_total": 12},
        "trekking": {"guests": 8,  "slots_total": 8},
        "cycling":  {"guests": 6,  "slots_total": 10},
        "cultural": {"guests": 11, "slots_total": 14}
      }
    },
    {
      "date": "2026-05-11",
      "schedule": [
        {"name": "Wayan",  "assigned_activity": "surf",     "status": "free_if_surf_cancelled"},
        {"name": "Komang", "assigned_activity": "cycling",  "status": "confirmed"},
        {"name": "Made",   "assigned_activity": "rafting",  "status": "free_if_rafting_cancelled"},
        {"name": "Kadek",  "assigned_activity": "trekking", "status": "confirmed"},
        {"name": "Agus",   "assigned_activity": "driver",   "status": "confirmed"},
        {"name": "Putu",   "assigned_activity": "driver",   "status": "confirmed"}
      ],
      "confirmed_bookings": {
        "surf":     {"guests": 12, "slots_total": 16},
        "rafting":  {"guests": 8,  "slots_total": 12},
        "trekking": {"guests": 8,  "slots_total": 8},
        "cycling":  {"guests": 7,  "slots_total": 10},
        "cultural": {"guests": 9,  "slots_total": 14}
      }
    }
  ],
  "source": "mock_calendar_mcp"
}
```

Kopi Nusa Café fixtures follow the same structure with coffee/F&B inventory items (`coffee_beans`, `fresh_milk`, `pastries`, `cups`), no `staff` or `activity_types` fields, and a quiet rainy week + low-occupancy scenario that triggers a straightforward inventory reduction and supplier email draft.

---

### Seed Script

Run once before the demo to populate PostgreSQL with the mock businesses and 30 days of synthetic historical action data (needed so the Demand Modeler has a baseline to compare against).

```python
# seed.py
import json, uuid, os
from pathlib import Path
from datetime import date, timedelta
import psycopg

FIXTURES_DIR = Path("mock/fixtures")
DATABASE_URL = os.environ["DATABASE_URL"]

BUSINESSES = ["nusa_adventures", "kopi_nusa_cafe"]

def seed():
    conn = psycopg.connect(DATABASE_URL)
    with conn.cursor() as cur:

        # Create tables if not exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                business_id TEXT PRIMARY KEY,
                profile     JSONB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS proposals (
                proposal_id  TEXT PRIMARY KEY,
                business_id  TEXT NOT NULL,
                proposed_at  TIMESTAMPTZ NOT NULL,
                proposal     JSONB NOT NULL,
                status       TEXT DEFAULT 'pending'
            );
            CREATE TABLE IF NOT EXISTS action_feedback (
                feedback_id  TEXT PRIMARY KEY,
                proposal_id  TEXT NOT NULL,
                business_id  TEXT NOT NULL,
                submitted_at TIMESTAMPTZ NOT NULL,
                rating       TEXT NOT NULL,
                free_text    TEXT,
                was_accurate BOOLEAN
            );
            CREATE TABLE IF NOT EXISTS historical_demand (
                business_id      TEXT NOT NULL,
                date             DATE NOT NULL,
                actual_guests    INT,
                demand_multiplier FLOAT,
                PRIMARY KEY (business_id, date)
            );
        """)

        # Seed business profiles
        for biz_id in BUSINESSES:
            profile = json.loads((FIXTURES_DIR / biz_id / "business.json").read_text())
            cur.execute(
                "INSERT INTO businesses VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (biz_id, json.dumps(profile))
            )

        # Seed 30 days of synthetic historical demand (simple sine wave around baseline)
        import math
        for biz_id in BUSINESSES:
            profile = json.loads((FIXTURES_DIR / biz_id / "business.json").read_text())
            baseline = profile.get("baseline_daily_guests", 10)
            for i in range(30):
                day = date.today() - timedelta(days=30 - i)
                multiplier = round(1.0 + 0.3 * math.sin(i / 3.0), 2)
                guests = int(baseline * multiplier)
                cur.execute("""
                    INSERT INTO historical_demand VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (biz_id, day.isoformat(), guests, multiplier))

    conn.commit()
    conn.close()
    print("✅ Seed complete.")

if __name__ == "__main__":
    seed()
```

Run with: `python seed.py`

---

### `.env.example`

```bash
# LLM
AMD_VLLM_BASE_URL=http://localhost:8000/v1

# Database
DATABASE_URL=postgresql://opsscout:password@localhost:5432/opsscout

# Mode — set to false to use real MCPs and OAuth
DEMO_MODE=true

# Production-only (leave blank in demo mode)
SHOPIFY_CLIENT_ID=
SHOPIFY_CLIENT_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
SLACK_BOT_TOKEN=
```



### Pages

**Page 1: Connect**
- OAuth buttons for Shopify, Square, Google Calendar
- Fallback 3-field form
- Tier selection radio

**Page 2: Dashboard (main)**
- "Next 7 days" demand forecast table (date, trend badge, demand multiplier, key signal)
- "Pending approvals" panel — one card per ActionProposal
  - Each card shows: `summary_for_owner`, action list, estimated cost, confidence
  - Buttons: ✅ Approve All / ✅ Approve Selected / ❌ Dismiss

**Page 3: Trace (ReAct viewer)**
- Expandable per-agent ReAct trace for the current proposal
- Shows: Thought → Tool called → Observation, for each step
- This is the panel judges look at to evaluate agentic behavior

**Page 4: History**
- Table of past proposals: date, summary, status (approved/dismissed), actions taken

---

## 13. Demo Script (for the ≤5-min video)

Structure the demo to show the ReAct loop clearly within the first 60 seconds.

```
0:00 – 0:20  Problem statement (voiceover while dashboard loads)
             "Nusa Adventures runs surf, rafting, trekking, cycling, and cultural
              tours across Bali. A storm is hitting the coast this weekend —
              but 4,200 surf competition tourists are already here and can't leave.
              Right now the owner is manually figuring out what to cancel,
              who to move, and what to tell 49 guests.
              OpsScout does all of that in one pass."

0:20 – 2:00  Live ReAct trace (Page 3) — show each step as it executes
             ┌──────────────────────────────────────────────────────────────┐
             │ AGENT: Forecaster                                            │
             │ THOUGHT: I need weather data split by operational zone.      │
             │ TOOL: get_tool_result("weather", "nusa_adventures")          │
             │ OBS: Coastal — heavy rain 52mm, wind 45kph, sea rough Sat.  │
             │      Highland — partly cloudy 18°C, wind 10kph. Unaffected. │
             ├──────────────────────────────────────────────────────────────┤
             │ THOUGHT: High storm on coast but highland is clear.          │
             │          Need to know if there are tourists in town          │
             │          who might pivot to inland activities.               │
             │ TOOL: get_tool_result("airbnb", "nusa_adventures")          │
             │ OBS: Only 5 of 32 listings available. Avg $285 vs            │
             │      baseline $145. → very_high occupancy pressure.         │
             ├──────────────────────────────────────────────────────────────┤
             │ THOUGHT: Very high tourist density. Let me check why.        │
             │ TOOL: get_tool_result("events", "nusa_adventures")          │
             │ OBS: Bali International Surf Championships, 4,200 attendees, │
             │      550m from base, Sat–Sun.                                │
             │      Ubud Writers Festival, 2,800 attendees, 24km away.     │
             ├──────────────────────────────────────────────────────────────┤
             │ THOUGHT: Competition tourists are stuck in Bali — they       │
             │          cannot surf but they're adventure travelers.        │
             │          Volcano trek + cultural tours are strong            │
             │          alternatives. But trek is currently at full         │
             │          capacity (8/8). I need to check if staff can cover  │
             │          an expanded trek slot before recommending it.       │
             │ TOOL: get_tool_result("calendar", "nusa_adventures")        │
             │ OBS: Wayan + Komang on surf Sat → free if surf cancelled.   │
             │      Kadek on trek, confirmed. Made on rafting → free       │
             │      if rafting cancelled. Trek currently 8 pax, 8 cap.     │
             ├──────────────────────────────────────────────────────────────┤
             │ THOUGHT: Wayan is certified for trekking support.           │
             │          With Wayan added, trek cap can increase to 14.     │
             │          Check inventory — do we have enough gear for 14?   │
             │ TOOL: get_tool_result("inventory", "nusa_adventures")       │
             │ OBS: Rain Poncho: 4 units available, threshold 12. ⚠️        │
             │      Headlamps: 9 units (sufficient for 14). Poles: 10 ok. │
             ├──────────────────────────────────────────────────────────────┤
             │ FINAL REASONING: Cancel surf + rafting (coastal storm,      │
             │ unsafe). Free up Wayan + Made. Assign Wayan to trek →       │
             │ expand capacity 8 → 14. Urgent reorder: 10 rain ponchos.   │
             │ Draft upgrade offer to 14 surf/rafting guests:              │
             │ volcano trek at no extra cost. Cultural tour has headroom   │
             │ (11/14 booked) — no action needed.                          │
             └──────────────────────────────────────────────────────────────┘
             Show DemandForecast structured output on screen.
             Highlight: demand_multiplier=1.8 (highland), 0.0 (coastal).

2:00 – 3:00  ActionProposal card (Page 2)
             Show the card with 5 actions, confidence 0.91:
               1. Cancel Saturday surf lessons — notify 14 guests
               2. Cancel Saturday Ayung rafting — notify 10 guests
               3. Reallocate Wayan to Saturday trekking team
               4. Expand volcano trek capacity 8 → 14 (add morning batch)
               5. Order 10 rain ponchos — draft supplier email
               + Communications: guest upgrade offer draft
                 "Your Saturday surf is moving mountains — literally.
                  We're upgrading you to our Volcano Sunrise Trek
                  at no extra cost. Same thrill, better view."
             Tap "Approve All."
             Show execution log: calendar updated, supplier email staged.

3:00 – 3:45  Kopi Nusa Café (Tier 2) — quick contrast
             Switch business selector to Kopi Nusa Café.
             Show the same flow, different outcome:
             staffing_actions is empty by design.
             Agent recommends reducing milk order by 28%, drafts supplier email.
             Highlight: "Same agent stack, different tier, scoped output."

3:45 – 4:15  Accommodation signal close-up
             Show the raw airbnb.json query result on screen.
             "5 of 32 listings available. Price up 97%.
              That's 4,000+ tourists who aren't going anywhere.
              This signal alone changed the entire action plan."

4:15 – 5:00  Architecture slide
             Show the multi-agent diagram.
             Mention: Qwen3-30B on AMD MI300X, CrewAI + LangGraph,
             structured outputs via OpenAI SDK, zone-aware weather,
             AirBnB occupancy as demand signal.
```

---

## 14. Project Structure

```
opsscout/
├── main.py                        # Streamlit entry point
├── models.py                      # All Pydantic models (Section 5)
├── structured_outputs.py          # OpenAI SDK extraction functions (Section 7)
├── crew.py                        # CrewAI agents and tasks (Section 6)
├── graph.py                       # LangGraph state machine (Section 8)
├── mcp_tools.py                   # Mock-aware tool dispatcher (Section 9)
├── accommodation_signal.py        # AirBnB occupancy module (Section 10)
├── onboarding.py                  # Business selector (demo) + OAuth (production)
├── db.py                          # PostgreSQL helpers (state, proposals, feedback)
├── seed.py                        # Populates DB with mock businesses + history
├── mock/
│   ├── scenarios.py               # Scenario loader (see Section 11a)
│   └── fixtures/
│       ├── nusa_adventures/
│       │   ├── business.json      # Business profile + tier + activity_types
│       │   ├── weather.json       # Coastal + highland zone split forecast
│       │   ├── airbnb.json        # Accommodation availability fixture
│       │   ├── events.json        # Surf championships + Ubud festival
│       │   ├── inventory.json     # Multi-activity equipment with poncho shortage
│       │   └── calendar.json      # Per-staff, per-activity schedule
│       └── kopi_nusa_cafe/
│           ├── business.json
│           ├── weather.json
│           ├── airbnb.json
│           ├── events.json
│           ├── inventory.json     # Coffee beans, milk, pastries etc.
│           └── calendar.json
├── pages/
│   ├── 1_Connect.py
│   ├── 2_Dashboard.py
│   ├── 3_Trace.py
│   └── 4_History.py
├── requirements.txt
├── README.md                      # Submission README (see Section 16)
└── .env.example                   # API keys template (no secrets in repo)
```

---

## 15. Future Improvements (Do Not Build for Hackathon)

### 15.1 Human Feedback Loop (Thumbs Up / Thumbs Down)

**Concept:** After an approved action plays out, show the owner a simple rating prompt the following day to evaluate whether OpsScout's prediction was accurate and the action was helpful.

**When to show it:**
- 24 hours after an `ActionProposal` was approved and executed, a feedback prompt appears at the top of the Dashboard page.
- Headline: *"Yesterday you approved: [summary_for_owner]. How did it go?"*
- Two buttons: 👍 Good call / 👎 Missed the mark
- Optional free-text field: "What actually happened?"
- Optional checkbox: "Was the forecast accurate?" (yes/no)

**Data model:** See `ActionFeedback` in Section 5.

**How it improves the agents over time:**
- Short term: thumbs-down feedback triggers a Streamlit toast prompting the owner to add context. This context is stored and injected into the next proposal for that business as few-shot examples: *"Note: last week the agent over-estimated demand for Saturday night concerts. The owner reported actual foot traffic was 30% below forecast."*
- Medium term: aggregate feedback per signal source (e.g. AirBnB occupancy vs. actual demand correlation) to calibrate the `demand_multiplier` formula.
- Long term: thumbs-up/down labels form a preference dataset for RLHF or DPO fine-tuning on Qwen3. This is the natural path to a business-specific model.

**Implementation notes (for future):**
- Store feedback in the `action_feedback` PostgreSQL table (schema in `db.py` stub).
- Build a lightweight `FeedbackAnalyzer` CrewAI agent that reads the last 30 days of feedback for a business and produces a `FeedbackSummary` structured output, injected into the Forecaster system prompt as context.
- Do NOT use feedback to auto-adjust agent behavior without a human review step — keep a human in the loop on model updates.

### 15.2 Vision-Based Inventory and Occupancy Reading
- `Qwen3-VL` integration for reading photos of inventory shelves, handwritten booking sheets, or dining room occupancy estimates from a camera feed.
- Adds a `VisionIngestor` module stub in `mcp_tools.py` with a `TODO` comment.
- Only viable with MI300X's 192GB VRAM at full precision — document this as a hardware requirement.

### 15.3 Multi-Venue Support for Pop-Up Operators
- A single owner account manages multiple stall/venue configurations.
- The LangGraph state machine runs one graph instance per venue in parallel.
- Venue-level performance comparison: *"Bazaar A outperformed B by 2× last month — consider dropping B for May."*

### 15.4 PredictHQ Integration (Upgrade from AirBnB Proxy)
- Replace the AirBnB occupancy proxy with PredictHQ's demand intelligence API.
- PredictHQ provides a direct `phq_attendance` metric and `accommodation_signal` endpoint — no derivation needed.
- Free developer tier available: https://developer.predicthq.com

---

## 16. Submission README Template

```markdown
# OpsScout — Autonomous Demand Intelligence for Event-Driven Businesses

## What It Does
OpsScout is a multi-agent system that watches weather, local events, 
and nearby accommodation occupancy to predict demand spikes — then 
proposes staffing, inventory, and communication actions for owner approval.

## Track
Track 1: AI Agents & Agentic Workflows

## Tech Stack
- **LLM:** Qwen3-30B-A3B-Instruct-2507 via vLLM on AMD MI300X
- **Agent Frameworks:** CrewAI (multi-agent crew) + LangGraph (durable state machine)
- **Structured Outputs:** OpenAI SDK `beta.chat.completions.parse` with Pydantic models
- **MCP Servers:** Weather, AirBnB, Google Calendar, Gmail, Slack
- **Frontend:** Streamlit

## ReAct Loop
[Link to Page 3 of the demo showing live agent trace]

## How to Run
1. `git clone ...`
2. `cp .env.example .env` and fill in your AMD Developer Cloud endpoint and `DATABASE_URL`
3. `pip install -r requirements.txt`
4. `streamlit run main.py`

## AMD GPU Usage
All inference runs on Qwen3-30B-A3B-Instruct-2507 served via vLLM 
on the AMD Developer Cloud MI300X instance.
Endpoint: http://[YOUR_AMD_INSTANCE]:8000/v1
```

---

## 17. Dependency Pinning (Critical)

```
# requirements.txt — pin these versions, do not upgrade mid-hackathon
crewai==0.80.0
langgraph==0.2.55
langgraph-checkpoint-postgres==2.0.7
langchain-openai==0.2.14
openai==1.51.0
pydantic==2.9.2
pydantic-ai==0.0.15
streamlit==1.40.0
httpx==0.27.2
python-dotenv==1.0.1
psycopg[binary]==3.2.3
```

---

## 18. 7-Day Build Schedule

| Day | Goal | Done When |
|---|---|---|
| 1 | vLLM + Qwen3 running on AMD MI300X. OpenAI SDK hitting the endpoint. First structured output (`DemandForecast`) extracted successfully. PostgreSQL running, `seed.py` executed. | `client.beta.chat.completions.parse()` returns a valid Pydantic model. Both demo businesses visible in the Streamlit selector. |
| 2 | Mock fixture files complete for both businesses. `get_tool_result()` dispatcher returning fixture data. Forecaster agent producing a full `DemandForecast` from mock weather + AirBnB + events fixtures. | `accommodation_signal.py` returns a valid `AccommodationSignal` from fixture JSON. |
| 3 | Full CrewAI crew running end-to-end. `ActionProposal` extracted via structured outputs. `approval_required=True` enforced. | Full proposal visible in terminal for a test business. |
| 4 | LangGraph state machine wrapping the crew. Streamlit Dashboard page showing the proposal card with Approve/Dismiss. | Owner can tap Approve in browser and the approval is logged to PostgreSQL. |
| 5 | Execution layer: approved actions dispatch via Calendar MCP and Gmail MCP. ReAct trace page working. | A test approval sends a real calendar event or email draft. |
| 6 | Record demo video. Both tiers (Tier 1 surf tour + Tier 2 café) demonstrated. AirBnB occupancy signal highlighted. | Video ≤5 min, shows ReAct trace, structured output panel, approval flow. |
| 7 | README, slide deck, deploy to AMD Cloud, submit on lablab. Post 3× Build-in-Public threads with `#AMDDevHackathon`. | lablab submission form complete. |
```
