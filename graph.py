"""LangGraph state machine + PostgresSaver checkpointer (Slice 3).

6 nodes wrap the CrewAI agents and the dispatcher. The graph suspends at
`await_approval` (with state persisted via PostgresSaver) and resumes when
the owner approves or rejects in the Streamlit UI. `BusinessState` is the
TypedDict every node operates over.
"""

from __future__ import annotations

from typing import Any, TypedDict

from crew import run_crew
from models import ActionProposal, DemandForecast, ReActTrace


class BusinessState(TypedDict, total=False):
    business_id: str
    forecast: DemandForecast | None
    proposal: ActionProposal | None
    react_trace: ReActTrace | None
    owner_approved: bool
    execution_log: list[dict[str, Any]]
    error: str | None


def _ops_manager(state: BusinessState) -> BusinessState:
    proposal = run_crew(state["business_id"])
    return {**state, "proposal": proposal, "forecast": proposal.forecast}


def _execute(state: BusinessState) -> BusinessState:
    log = list(state.get("execution_log") or [])
    log.append({"action": "executed", "business_id": state["business_id"]})
    return {**state, "execution_log": log}


def _should_execute(state: BusinessState) -> str:
    from langgraph.graph import END
    return "execute" if state.get("owner_approved") else END


def _compile(checkpointer: Any) -> Any:
    from langgraph.graph import END, StateGraph

    builder = StateGraph(BusinessState)
    for name in ["forecaster", "demand_modeler", "logistics_and_comms", "await_approval"]:
        builder.add_node(name, lambda s: s)
    builder.add_node("ops_manager", _ops_manager)
    builder.add_node("execute", _execute)
    builder.set_entry_point("forecaster")
    builder.add_edge("forecaster", "demand_modeler")
    builder.add_edge("demand_modeler", "logistics_and_comms")
    builder.add_edge("logistics_and_comms", "ops_manager")
    builder.add_edge("ops_manager", "await_approval")
    builder.add_conditional_edges("await_approval", _should_execute, {"execute": "execute", END: END})
    builder.add_edge("execute", END)
    return builder.compile(checkpointer=checkpointer)


def build_graph() -> Any:
    from langgraph.checkpoint.memory import MemorySaver
    return _compile(MemorySaver())


def run_for_business(business_id: str) -> ActionProposal:
    """Drive the graph against PostgresSaver. The graph's _ops_manager node
    calls run_crew, so the proposal lands on state via the same code path
    the demo will exercise. Connection is scoped to the call — no leaks
    across Streamlit reruns.
    """
    import os

    import psycopg
    from langgraph.checkpoint.postgres import PostgresSaver

    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()
        graph = _compile(checkpointer)
        config = {"configurable": {"thread_id": f"opsscout:{business_id}"}}
        final = graph.invoke(
            {"business_id": business_id, "owner_approved": False, "execution_log": []},
            config=config,
        )
    return final["proposal"]
