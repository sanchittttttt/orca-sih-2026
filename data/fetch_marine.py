import requests
import json
import time

url = "https://marine-api.open-meteo.com/v1/marine"

# A grid of points across the Indian coast bounding box
# (8N-22N, 68E-90E), spaced roughly every 2 degrees
latitudes = [8, 10, 12, 14, 16, 18, 20, 22]
longitudes = [68, 72, 76, 80, 84, 88]

all_points = []

for lat in latitudes:
    for lon in longitudes:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "wave_height,wave_direction,wave_period,sea_surface_temperature"
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            all_points.append({
                "latitude": lat,
                "longitude": lon,
                "wave_height": current.get("wave_height"),
                "wave_direction": current.get("wave_direction"),
                "wave_period": current.get("wave_period"),
                "sea_surface_temperature": current.get("sea_surface_temperature"),
            })
        time.sleep(0.2)  # be polite to the free API, avoid hammering it

with open("marine_snapshot.json", "w") as f:
    json.dump(all_points, f, indent=2)

print(f"Done! Fetched {len(all_points)} points -> marine_snapshot.json")