# Dataset & Data Integration (Module 1)

Real satellite/weather data for the Indian coast, plus honest simulation
where no real free source exists. See `DATA_SOURCES.md` for full methodology
and the live-vs-cached-vs-simulated breakdown.

## Setup

```bash
pip install requests pandas numpy copernicusmarine xarray netCDF4
copernicusmarine login   # one-time, needs a free account at data.marine.copernicus.eu
```

## Scripts, in the order you'd typically run them

| Script | What it does | Output |
|---|---|---|
| `fetch_weather.py` | Reference only — verifies Open-Meteo works | `weather_snapshot.json` |
| `fetch_marine.py` | Grid-fetches SST + waves across the Indian coast | `marine_snapshot.json` |
| `fetch_chlorophyll.py` | Pulls real chlorophyll+gradient from Copernicus Marine | `chlorophyll_snapshot.nc`, `.csv` |
| `compute_pfz.py` | Computes PFZ zones using INCOIS's real method on the two files above | `pfz_points.json` |
| `fetch_cyclone.py` | Reference only — verifies GDACS works | `cyclone_alerts.json` |
| `generate_lightning_mock.py` | Fully simulated — no real source exists | `lightning_alerts.json` |

## Important: what's live vs. cached in production

- **Weather, marine, and cyclone data are called LIVE by the AI service** — the
  `fetch_weather.py` and `fetch_cyclone.py` scripts here are reference/verification
  only, not part of the production data path.
- **Chlorophyll and PFZ are genuinely cached** — re-run `fetch_chlorophyll.py` then
  `compute_pfz.py` whenever you want fresh zones (once before a demo is plenty).
  The AI service (`ai-service/`) reads `pfz_points.json` directly from this folder —
  no need to copy it anywhere.

See `DATA_SOURCES.md` for the full reasoning, including the chlorophyll outlier
filtering methodology and its validation against the real Southwest Monsoon
upwelling season.
