from __future__ import annotations

import os

from crewai import Agent
from langchain_openai import ChatOpenAI

from mcp_tools import get_tool_result
from models import ActionProposal
from structured_outputs import extract_action_proposal, extract_demand_forecast

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
    forecast = extract_demand_forecast(
        raw_agent_text="",
        context={"business_id": business_id, "weather": weather, "events": events, "airbnb": airbnb},
    )
    get_tool_result("inventory", business_id)
    get_tool_result("calendar", business_id)
    return extract_action_proposal(raw_manager_text="", forecast=forecast)
