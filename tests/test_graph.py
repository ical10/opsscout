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
