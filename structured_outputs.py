"""OpenAI-SDK-driven structured output extractors (Slice 2).

Every LLM extraction in OpsScout flows through `client.beta.chat.completions.parse()`
with a Pydantic schema. These three functions are the only place that wiring
lives — agents and graph nodes call them, never the OpenAI client directly.
"""

from __future__ import annotations

import os

from openai import OpenAI

from models import ActionProposal, DemandForecast, ReActStep

_client = OpenAI(
    base_url=os.getenv("AMD_VLLM_BASE_URL", "http://localhost:8000/v1"),
    api_key="not-needed",
)

_MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"


def extract_demand_forecast(
    raw_agent_text: str,
    context: dict,
) -> DemandForecast:
    completion = _client.beta.chat.completions.parse(
        model=_MODEL,
        messages=[
            {"role": "system", "content": "Extract the demand forecast into the schema. Use null when unknown."},
            {"role": "user", "content": f"Business context: {context}\n\nAnalysis:\n{raw_agent_text}"},
        ],
        response_format=DemandForecast,
        temperature=0.0,
    )
    return completion.choices[0].message.parsed


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
