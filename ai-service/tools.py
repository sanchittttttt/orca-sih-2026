"""
Tool functions the agents call to retrieve REAL data. No LLM involvement here —
this file is the boundary between "the LLM reasons about what's needed" and
"real numbers come from somewhere verifiable."

Weather, marine, and cyclone data are called LIVE, per-query — Open-Meteo and
GDACS are both fast/keyless enough for this. Only PFZ is read from a
precomputed file, because Copernicus (its real input) is too slow to call
live. This file points DATA_DIR at the top-level data/ folder (Module 1) —
there is only ONE copy of pfz_points.json / lightning_alerts.json in the whole
repo, so re-running compute_pfz.py in data/ is immediately picked up here with
no copying required.
"""

import json
import os
from datetime import datetime, timedelta

import requests

# Shared with Module 1 — do not duplicate this folder inside ai-service/
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
    """
    Reads Module 1's precomputed pfz_points.json directly from the shared
    data/ folder — real INCOIS-method computation over real satellite data.
    Re-run data/compute_pfz.py whenever you want fresh zones; no copying
    needed, this always reads the current file.
    """
    path = os.path.join(DATA_DIR, "pfz_points.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        points = json.load(f)

    def dist(p: dict) -> float:
        return ((p["latitude"] - lat) ** 2 + (p["longitude"] - lon) ** 2) ** 0.5

    return sorted(points, key=dist)[:top_n]


def get_cyclone_alerts() -> list[dict]:
    """
    Called LIVE, same reasoning as weather — GDACS is fast and keyless, no
    need to cache. Filters to a bounding box roughly covering India and
    surrounding seas (0-30N, 60-100E).
    """
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
    """
    Fully simulated (no free real-time source exists for India). Reads from
    the shared data/ folder, same file Module 1's generate_lightning_mock.py
    produces.
    """
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
    TEMPORARY local copy of the fixed risk formula. Owned long-term by Module 3
    (Spring Boot Risk Engine + PostGIS) — once that service exists, replace
    calls to this function with a REST call to its /internal/risk/score
    endpoint instead. Kept mathematically identical to the playbook's formula.

    score = wind*0.25 + wave*0.25 + rain*0.15 + lightning*0.15 + cyclone*0.20
    0-30 LOW, 31-60 MODERATE, 61-80 HIGH, 81-100 EXTREME
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
