"""
Reference/verification script only — NOT part of the production data path.

Confirms Open-Meteo works and documents the response shape. In production, the
AI Agent Service (ai-service/tools.py) calls Open-Meteo LIVE, per-user-query,
directly — it does not read this script's output file.
"""

import requests
import json

url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": 16.99,      # Ratnagiri, a coastal town
    "longitude": 73.31,
    "current_weather": True,
    "hourly": "temperature_2m,precipitation_probability,windspeed_10m"
}

response = requests.get(url, params=params)
data = response.json()

with open("weather_snapshot.json", "w") as f:
    json.dump(data, f, indent=2)

print("Done! Check weather_snapshot.json")
