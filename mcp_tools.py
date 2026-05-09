"""Mock-aware MCP dispatcher (Slice 1).

`get_tool_result` is the single funnel for every external data lookup. In
DEMO_MODE=true (the hackathon default) it reads JSON fixtures from
`mock/fixtures/<business_id>/<tool>.json`. Production path (real MCP
servers + OAuth) is out of scope until Slice 5.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "mock" / "fixtures"


def get_tool_result(
    tool: str,
    business_id: str,
    params: dict | None = None,
) -> dict:
    if os.getenv("DEMO_MODE", "true").lower() != "true":
        raise NotImplementedError(
            "Production MCP path is out of scope until Slice 5."
        )
    fixture_path = FIXTURES_DIR / business_id / f"{tool}.json"
    return json.loads(fixture_path.read_text())
