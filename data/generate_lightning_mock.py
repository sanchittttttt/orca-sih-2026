import json
import random

# Rough regional breakdown of the Indian coastline
regions = [
    "Gujarat Coast", "Konkan Coast", "Goa Coast", "Karnataka Coast",
    "Kerala Coast", "Tamil Nadu Coast", "Andhra Coast", "Odisha Coast",
    "West Bengal Coast", "Andaman & Nicobar"
]

alerts = []
for region in regions:
    alerts.append({
        "region": region,
        "lightning_alert": random.choice(["none", "moderate", "severe"]),
        "source": "SIMULATED - no free real-time lightning API found for India"
    })

with open("lightning_alerts.json", "w") as f:
    json.dump(alerts, f, indent=2)

print("Generated lightning_alerts.json (simulated)")