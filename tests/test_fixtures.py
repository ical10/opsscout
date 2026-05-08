"""Validate that every business fixture file parses and exposes the expected top-level keys."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

BUSINESSES = ["nusa_adventures", "kopi_nusa_cafe"]

FIXTURE_FILES = [
    ("business.json", ["business_id", "tier"]),
    ("weather.json", ["source"]),
    ("airbnb.json", ["results", "source"]),
    ("events.json", ["events"]),
    ("inventory.json", ["items", "source"]),
    ("calendar.json", ["staff_availability", "source"]),
]


@pytest.mark.parametrize("business_id", BUSINESSES)
@pytest.mark.parametrize("filename,expected_keys", FIXTURE_FILES)
def test_fixture_parses_and_has_keys(
    business_id: str,
    filename: str,
    expected_keys: list[str],
    fixtures_dir: Path,
) -> None:
    path = fixtures_dir / business_id / filename
    assert path.exists(), f"missing fixture: {path}"
    data = json.loads(path.read_text())
    assert isinstance(data, dict), f"{path} did not parse to a dict"
    for key in expected_keys:
        assert key in data, f"{path} missing top-level key: {key}"
