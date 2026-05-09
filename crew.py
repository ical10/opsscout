from __future__ import annotations

import os

from crewai import Agent, Task
from langchain_openai import ChatOpenAI

from mcp_tools import get_tool_result
from models import ActionProposal
from structured_outputs import extract_action_proposal, extract_demand_forecast


def _execute_agent(agent: Agent, description: str, expected_output: str = "") -> str:
    """Run one agent against the local vLLM with the given task and return
    the raw text. Tests monkeypatch this; the live demo path goes through
    `agent.execute_task` and the ChatOpenAI llm bound at module load.
    """
    task = Task(description=description, expected_output=expected_output, agent=agent)
    return str(agent.execute_task(task))

llm = ChatOpenAI(
    model="Qwen3-30B-A3B-Instruct-2507",
    base_url=os.getenv("AMD_VLLM_BASE_URL", "http://localhost:8000/v1"),
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


def run_crew(business_id: str) -> ActionProposal:
    weather = get_tool_result("weather", business_id)
    events = get_tool_result("events", business_id)
    airbnb = get_tool_result("airbnb", business_id)

    forecaster_text = _execute_agent(
        forecaster,
        description=(
            f"Analyze 7-day demand for business {business_id}. "
            f"Weather: {weather}. Events: {events}. Accommodation: {airbnb}. "
            "Cite each signal and produce a demand multiplier (0–5), trend, and confidence."
        ),
        expected_output="A demand analysis with multiplier, trend, confidence, and reasoning.",
    )
    forecast = extract_demand_forecast(
        raw_agent_text=forecaster_text,
        context={"business_id": business_id, "weather": weather, "events": events, "airbnb": airbnb},
    )

    inventory = get_tool_result("inventory", business_id)
    calendar = get_tool_result("calendar", business_id)

    modeler_text = _execute_agent(
        demand_modeler,
        description=(
            f"Translate the demand multiplier {forecast.demand_multiplier} into concrete quantities "
            f"using inventory={inventory} and calendar={calendar}."
        ),
        expected_output="Modeled quantities (portions, stock, expected guests).",
    )
    logistics_text = _execute_agent(
        logistics_agent,
        description=(
            f"From these modeled quantities ({modeler_text}) produce inventory order proposals "
            f"and (Tier 1 only) staffing changes. Forecast multiplier: {forecast.demand_multiplier}."
        ),
        expected_output="Inventory orders + (if Tier 1) staffing changes.",
    )
    comms_text = _execute_agent(
        comms_agent,
        description=(
            f"Draft owner-approval-required communications for the operational plan: {logistics_text}."
        ),
        expected_output="Communication drafts ending in [PENDING OWNER APPROVAL].",
    )
    ops_text = _execute_agent(
        ops_manager,
        description=(
            f"Merge the logistics plan and communications drafts into a single ActionProposal. "
            f"Logistics: {logistics_text}. Communications: {comms_text}. "
            "Set approval_required=True. Top 3 actions only. Plain-English summary."
        ),
        expected_output="A single ActionProposal in plain English with priority, summary, and confidence.",
    )

    return extract_action_proposal(raw_manager_text=ops_text, forecast=forecast)
