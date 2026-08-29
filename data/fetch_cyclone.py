import requests
import json
from datetime import datetime, timedelta

url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

params = {
    "eventlist": "TC",  # Tropical Cyclones only
    "fromdate": (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%d"),
    "todate": datetime.utcnow().strftime("%Y-%m-%d"),
}

response = requests.get(url, params=params)
data = response.json()
print(f"Total global TC events in range: {len(data.get('features', []))}")

# India-ish bounding box: filter events whose coordinates fall roughly here
LAT_MIN, LAT_MAX = 0, 30
LON_MIN, LON_MAX = 60, 100

india_alerts = []
for feature in data.get("features", []):
    coords = feature.get("geometry", {}).get("coordinates", [None, None])
    lon, lat = coords[0], coords[1]
    if lon is None or lat is None:
        continue
    if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
        props = feature.get("properties", {})
        india_alerts.append({
            "event_name": props.get("eventname") or props.get("name"),
            "alert_level": props.get("alertlevel"),
            "latitude": lat,
            "longitude": lon,
            "from_date": props.get("fromdate"),
            "to_date": props.get("todate"),
        })

with open("cyclone_alerts.json", "w") as f:
    json.dump(india_alerts, f, indent=2)

print(f"Found {len(india_alerts)} cyclone alert(s) near India -> cyclone_alerts.json")
print(json.dumps(india_alerts, indent=2))