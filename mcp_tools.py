"""Mock-aware MCP dispatcher (Slice 1).

`get_tool_result` is the single funnel for every external data lookup. In
DEMO_MODE=true (the hackathon default) it reads JSON fixtures from
`mock/fixtures/<business_id>/<tool>.json`. Production path (real MCP
servers + OAuth) is out of scope until Slice 5.
"""

from __future__ import annotations


def get_tool_result(
    tool: str,
    business_id: str,
    params: dict | None = None,
) -> dict:
    raise NotImplementedError(
        "owned by Slice 1 — see docs/plans/slice-1-mcp-tools.md"
    )
