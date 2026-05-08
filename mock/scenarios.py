"""Scenario flag → fixture override layer (Slice 1).

Lets the Streamlit demo selector toggle between baked-in scenarios (storm,
quiet week, festival) without rewriting fixtures. For the hackathon path
the bare fixtures are enough; this is here so cs workers see the import
surface.
"""

from __future__ import annotations


def get_scenario(name: str) -> dict:
    raise NotImplementedError(
        "owned by Slice 1 — see docs/plans/slice-1-mcp-tools.md"
    )
