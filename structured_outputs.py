"""OpenAI-SDK-driven structured output extractors (Slice 2).

Every LLM extraction in OpsScout flows through `client.beta.chat.completions.parse()`
with a Pydantic schema. These three functions are the only place that wiring
lives — agents and graph nodes call them, never the OpenAI client directly.
"""

from __future__ import annotations

from models import ActionProposal, DemandForecast, ReActStep


def extract_demand_forecast(
    raw_agent_text: str,
    context: dict,
) -> DemandForecast:
    raise NotImplementedError(
        "owned by Slice 2 — see docs/plans/slice-2-structured-outputs.md"
    )


def extract_action_proposal(
    raw_manager_text: str,
    forecast: DemandForecast,
) -> ActionProposal:
    raise NotImplementedError(
        "owned by Slice 2 — see docs/plans/slice-2-structured-outputs.md"
    )


def extract_react_step(
    agent_role: str,
    step_index: int,
    raw_step_text: str,
) -> ReActStep:
    raise NotImplementedError(
        "owned by Slice 2 — see docs/plans/slice-2-structured-outputs.md"
    )
