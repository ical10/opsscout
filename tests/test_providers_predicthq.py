"""Tests for providers.predicthq — PredictHQ events adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

from providers import predicthq


def test_fetch_maps_events_to_fixture_shape(monkeypatch) -> None:
    monkeypatch.setenv("PHQ_TOKEN", "test-token-xyz")

    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json = MagicMock(return_value={
        "count": 1,
        "results": [
            {
                "id": "abc",
                "title": "Ubud Yoga Festival",
                "start": "2026-05-12T09:00:00Z",
                "end": "2026-05-14T17:00:00Z",
                "geo": {"geometry": {"coordinates": [115.262, -8.508]}},
                "category": "festivals",
                "phq_attendance": 4200,
                "rank": 67,
            }
        ],
    })
    captured: dict = {}

    def fake_get(url: str, params: dict, headers: dict, timeout: float):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        return fake_response

    monkeypatch.setattr("providers.predicthq.httpx.get", fake_get)

    business = {
        "business_id": "nusa_adventures",
        "latitude": -8.51,
        "longitude": 115.26,
        "address": "Bali",
    }
    result = predicthq.fetch(business)

    assert result["location"] == "Bali"
    events = result["events"]
    assert len(events) == 1
    assert events[0]["name"] == "Ubud Yoga Festival"
    assert events[0]["date"] == "2026-05-12"
    assert events[0]["estimated_attendance"] == 4200
    assert events[0]["category"] == "festivals"
    assert events[0]["source"] == "predicthq"
    assert captured["headers"]["Authorization"] == "Bearer test-token-xyz"


def test_fetch_without_phq_token_raises(monkeypatch) -> None:
    import pytest

    monkeypatch.delenv("PHQ_TOKEN", raising=False)
    business = {"business_id": "x", "latitude": 0.0, "longitude": 0.0}
    with pytest.raises(RuntimeError, match="PHQ_TOKEN"):
        predicthq.fetch(business)


def test_fetch_defaults_category_when_missing_and_handles_empty(monkeypatch) -> None:
    monkeypatch.setenv("PHQ_TOKEN", "tok")

    fake = MagicMock()
    fake.raise_for_status = MagicMock()
    fake.json = MagicMock(return_value={
        "count": 1,
        "results": [
            {"id": "x", "title": "T", "start": "2026-05-12T00:00:00Z", "end": "2026-05-12T00:00:00Z"},
        ],
    })
    monkeypatch.setattr("providers.predicthq.httpx.get", lambda *a, **k: fake)
    business = {"latitude": 0.0, "longitude": 0.0, "address": ""}
    result = predicthq.fetch(business)
    assert result["events"][0]["category"] == "unknown"

    fake.json = MagicMock(return_value={"count": 0, "results": []})
    assert predicthq.fetch(business)["events"] == []
