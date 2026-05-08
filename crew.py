"""5-agent CrewAI crew (Slice 3).

The agents — Forecaster, DemandModeler, LogisticsAgent, CommsAgent,
OpsManager — are instantiated with role/goal/backstory verbatim from spec
§6. `run_crew` orchestrates them sequentially and returns a validated
ActionProposal that is then handed to the LangGraph state machine for
human-in-the-loop approval.
"""

from __future__ import annotations

from models import ActionProposal


def run_crew(business_id: str) -> ActionProposal:
    raise NotImplementedError(
        "owned by Slice 3 — see docs/plans/slice-3-crew-graph.md"
    )
