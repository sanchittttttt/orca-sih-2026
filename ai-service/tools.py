"""
Tool functions the agents call to retrieve REAL data. No LLM involvement here
— this file is the boundary between "the LLM reasons about what's needed" and
"real numbers come from somewhere verifiable."

Weather, marine, and cyclone data are called LIVE, per-query. Only PFZ and
lightning are read from files in the shared ../data/ folder (Module 1) —
there is only ONE copy of these files in the whole project, no duplication.
"""

import json
import os
from datetime import datetime, timedelta

import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def fetch_weather(lat: float, lon: float) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "hourly": "temperature_2m,precipitation_probability,windspeed_10m",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_marine(lat: float, lon: float) -> dict:
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "wave_height,wave_direction,wave_period,sea_surface_temperature",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def get_nearest_pfz(lat: float, lon: float, top_n: int = 3) -> list[dict]:
    path = os.path.join(DATA_DIR, "pfz_points.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        points = json.load(f)

    def dist(p: dict) -> float:
        return ((p["latitude"] - lat) ** 2 + (p["longitude"] - lon) ** 2) ** 0.5

    return sorted(points, key=dist)[:top_n]


def get_cyclone_alerts() -> list[dict]:
    url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    params = {
        "eventlist": "TC",
        "fromdate": (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%d"),
        "todate": datetime.utcnow().strftime("%Y-%m-%d"),
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    alerts = []
    for feature in data.get("features", []):
        coords = feature.get("geometry", {}).get("coordinates", [None, None])
        lon, lat = coords[0], coords[1]
        if lon is None or lat is None:
            continue
        if 0 <= lat <= 30 and 60 <= lon <= 100:
            props = feature.get("properties", {})
            alerts.append(
                {
                    "event_name": props.get("eventname") or props.get("name"),
                    "alert_level": props.get("alertlevel"),
                    "latitude": lat,
                    "longitude": lon,
                }
            )
    return alerts


def get_lightning_alerts() -> list[dict]:
    path = os.path.join(DATA_DIR, "lightning_alerts.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def compute_risk_score(
    wind_kmh: float,
    wave_height_m: float,
    rain_prob: float,
    lightning_level: str = "none",
    cyclone_level: str = "green",
) -> dict:
    """
    TEMPORARY local copy of the fixed risk formula, owned long-term by Module 3
    (Spring Boot Risk Engine + PostGIS). Kept mathematically identical to the
    playbook's formula so results stay consistent once that service replaces
    this call.
    """
    wind_score = min(wind_kmh / 60 * 100, 100)
    wave_score = min(wave_height_m / 5 * 100, 100)
    rain_score = rain_prob

    lightning_score = {"none": 0, "moderate": 50, "severe": 100}.get(lightning_level, 0)
    cyclone_score = {"green": 0, "orange": 60, "red": 100}.get(cyclone_level, 0)

    score = (
        wind_score * 0.25
        + wave_score * 0.25
        + rain_score * 0.15
        + lightning_score * 0.15
        + cyclone_score * 0.20
    )

    if score <= 30:
        level = "LOW"
    elif score <= 60:
        level = "MODERATE"
    elif score <= 80:
        level = "HIGH"
    else:
        level = "EXTREME"

    return {"score": round(score, 1), "level": level}
