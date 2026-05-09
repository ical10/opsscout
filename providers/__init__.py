"""Real-data providers used when DEMO_MODE=false.

Each provider returns dicts in the same shape as the corresponding fixture
under ``mock/fixtures/<business>/<tool>.json`` so the dispatcher contract
is preserved end-to-end.
"""

from __future__ import annotations
