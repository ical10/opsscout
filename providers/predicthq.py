from __future__ import annotations

import os
from datetime import date, timedelta

import httpx

ENDPOINT = "https://api.predicthq.com/v1/events/"
RADIUS_KM = 10
HORIZON_DAYS = 7


def fetch(business: dict) -> dict:
    token = os.getenv("PHQ_TOKEN")
    if not token:
        raise RuntimeError(
            "PHQ_TOKEN is not set — required for PredictHQ events. "
            "Set it in .env or fall back to DEMO_MODE=true."
        )

    today = date.today()
    end = today + timedelta(days=HORIZON_DAYS)
    params = {
        "within": f"{RADIUS_KM}km@{business['latitude']},{business['longitude']}",
        "active.gte": today.isoformat(),
        "active.lte": end.isoformat(),
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(ENDPOINT, params=params, headers=headers, timeout=15.0)
    response.raise_for_status()

    events = []
    for raw in response.json().get("results", []):
        events.append({
            "name": raw["title"],
            "date": raw["start"][:10],
            "end_date": raw.get("end", "")[:10],
            "estimated_attendance": raw.get("phq_attendance"),
            "distance_m": 0,
            "category": raw.get("category"),
            "visitor_profile": None,
            "source": "predicthq",
        })

    return {
        "location": business.get("address", ""),
        "events": events,
    }
