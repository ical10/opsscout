"""Tests for graph.py — LangGraph state machine + checkpointer."""

from __future__ import annotations


def test_build_graph_has_expected_nodes() -> None:
    from graph import build_graph

    graph = build_graph()
    nodes = set(graph.get_graph().nodes)
    expected = {
        "forecaster",
        "demand_modeler",
        "logistics_and_comms",
        "ops_manager",
        "await_approval",
        "execute",
    }
    assert expected <= nodes


def test_graph_skips_execute_until_owner_approved(monkeypatch) -> None:
    from graph import build_graph

    graph = build_graph()
    config = {"configurable": {"thread_id": "test-thread-1"}}

    initial = {"business_id": "nusa_adventures", "owner_approved": False, "execution_log": []}
    first = graph.invoke(initial, config=config)
    assert first.get("execution_log") == []

    second = graph.invoke({**first, "owner_approved": True}, config=config)
    assert len(second.get("execution_log") or []) >= 1
    assert second["execution_log"][-1]["action"] == "executed"
