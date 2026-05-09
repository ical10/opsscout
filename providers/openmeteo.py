from __future__ import annotations

import httpx

ENDPOINT = "https://api.open-meteo.com/v1/forecast"
DAILY_VARS = "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,wind_speed_10m_max"

_WMO: dict[int, str] = {
    0: "clear",
    1: "partly_cloudy", 2: "partly_cloudy", 3: "partly_cloudy",
    45: "fog", 48: "fog",
    51: "light_rain", 53: "light_rain", 55: "light_rain",
    56: "light_rain", 57: "light_rain",
    61: "rain", 63: "rain", 65: "rain",
    66: "rain", 67: "rain",
    71: "snow", 73: "snow", 75: "snow", 77: "snow",
    80: "heavy_rain", 81: "heavy_rain", 82: "heavy_rain",
    85: "snow", 86: "snow",
    95: "thunderstorm", 96: "thunderstorm", 99: "thunderstorm",
}


def fetch(business: dict) -> dict:
    params = {
        "latitude": business["latitude"],
        "longitude": business["longitude"],
        "daily": DAILY_VARS,
        "timezone": "auto",
    }
    response = httpx.get(ENDPOINT, params=params, timeout=15.0)
    response.raise_for_status()
    daily = response.json()["daily"]

    forecast = [
        {
            "date": daily["time"][i],
            "condition": _WMO.get(daily["weather_code"][i], "clear"),
            "temperature_c": round((daily["temperature_2m_max"][i] + daily["temperature_2m_min"][i]) / 2, 1),
            "precipitation_mm": daily["precipitation_sum"][i],
            "wind_kph": daily["wind_speed_10m_max"][i],
            "sea_state": "calm",
            "confidence": 0.85,
        }
        for i in range(len(daily["time"]))
    ]

    return {
        "zones": {
            "default": {
                "location": business.get("address", ""),
                "forecast": forecast,
            }
        },
        "source": "openmeteo",
    }
