"""LangGraph state machine + PostgresSaver checkpointer (Slice 3).

6 nodes wrap the CrewAI agents and the dispatcher. The graph suspends at
`await_approval` (with state persisted via PostgresSaver) and resumes when
the owner approves or rejects in the Streamlit UI. `BusinessState` is the
TypedDict every node operates over.
"""

from __future__ import annotations

from typing import Any, TypedDict

from models import ActionProposal, DemandForecast


class BusinessState(TypedDict, total=False):
    business_id: str
    forecast: DemandForecast | None
    proposal: ActionProposal | None
    owner_approved: bool
    execution_log: list[dict[str, Any]]


def build_graph() -> Any:
    raise NotImplementedError(
        "owned by Slice 3 — see docs/plans/slice-3-crew-graph.md"
    )


def run_for_business(business_id: str) -> ActionProposal:
    raise NotImplementedError(
        "owned by Slice 3 — see docs/plans/slice-3-crew-graph.md"
    )
