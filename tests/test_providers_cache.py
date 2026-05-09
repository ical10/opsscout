"""Tests for providers.cache — read-through file cache for live-provider responses."""

from __future__ import annotations

from pathlib import Path

from providers import cache


def test_read_miss_returns_none(tmp_path: Path) -> None:
    assert cache.read("openmeteo__nusa_adventures__2026-05-10", cache_dir=tmp_path) is None


def test_write_then_read_round_trips(tmp_path: Path) -> None:
    payload = {"source": "openmeteo", "daily": {"time": ["2026-05-10"]}}
    cache.write("openmeteo__nusa_adventures__2026-05-10", payload, cache_dir=tmp_path)

    got = cache.read("openmeteo__nusa_adventures__2026-05-10", cache_dir=tmp_path)
    assert got == payload
