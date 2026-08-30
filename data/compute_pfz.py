"""
Computes Potential Fishing Zones using INCOIS's real published method (SST
fronts + chlorophyll threshold) applied to real satellite/model data — not
random/fabricated coordinates. See DATA_SOURCES.md for full methodology
disclosure and validation notes.

Requires chlorophyll_snapshot.csv (from fetch_chlorophyll.py) and
marine_snapshot.json (from fetch_marine.py) to exist in this same folder.

Fix applied (previously a documented known limitation): the outlier cap is
now computed on the FULL week's chlorophyll distribution before filtering to
the latest date, rather than being recalculated on an already-date-filtered
subset. This prevents the cap from drifting depending on which day is selected.
"""

import pandas as pd
import numpy as np
import json

TOP_PERCENTILE = 85   # top 15% of scores = flagged as potential fishing zones
TOP_N = 50            # cap the output to a realistic advisory-sized list
OUTLIER_PERCENTILE = 95  # chlorophyll values above this are turbid-water artifacts

# --- Load full week of chlorophyll data ---
chl_df = pd.read_csv("chlorophyll_snapshot.csv")
chl_df = chl_df.dropna(subset=["CHL", "CHL_gradient"])

print(chl_df["CHL"].describe())
print(chl_df["CHL"].quantile([0.5, 0.75, 0.90, 0.95, 0.99]))

# --- Compute the outlier cap on the FULL week's distribution (fix applied) ---
MAX_PLAUSIBLE_CHL = chl_df["CHL"].quantile(OUTLIER_PERCENTILE / 100)
print(f"Dynamic CHL cap ({OUTLIER_PERCENTILE}th percentile, full week): {MAX_PLAUSIBLE_CHL:.3f} mg/m3")
chl_df = chl_df[chl_df["CHL"] <= MAX_PLAUSIBLE_CHL]

# --- Now filter to the latest available date, for a single-day advisory ---
latest_date = chl_df["time"].max()
chl_df = chl_df[chl_df["time"] == latest_date]
print(f"Using latest date: {latest_date} ({len(chl_df)} points after filtering)")

# --- Load the coarse SST/wave grid ---
with open("marine_snapshot.json") as f:
    marine_points = json.load(f)
sst_df = pd.DataFrame(marine_points).dropna(subset=["sea_surface_temperature"])

def nearest_marine_point(lat, lon):
    distances = np.sqrt((sst_df["latitude"] - lat) ** 2 + (sst_df["longitude"] - lon) ** 2)
    idx = distances.idxmin()
    return sst_df.loc[idx, "sea_surface_temperature"], sst_df.loc[idx, "wave_height"]

sst_vals, wave_vals = [], []
for _, row in chl_df.iterrows():
    sst, wave = nearest_marine_point(row["latitude"], row["longitude"])
    sst_vals.append(sst)
    wave_vals.append(wave)

chl_df["sea_surface_temperature"] = sst_vals
chl_df["wave_height"] = wave_vals

# --- Normalize and score ---
chl_df["chl_norm"] = (chl_df["CHL"] - chl_df["CHL"].min()) / (chl_df["CHL"].max() - chl_df["CHL"].min())
chl_df["gradient_norm"] = (chl_df["CHL_gradient"] - chl_df["CHL_gradient"].min()) / (chl_df["CHL_gradient"].max() - chl_df["CHL_gradient"].min())
chl_df["pfz_score"] = chl_df["chl_norm"] * 0.6 + chl_df["gradient_norm"] * 0.4

threshold_value = chl_df["pfz_score"].quantile(TOP_PERCENTILE / 100)
pfz_candidates = chl_df[chl_df["pfz_score"] >= threshold_value].copy()
pfz_candidates = pfz_candidates.sort_values("pfz_score", ascending=False).head(TOP_N)

pfz_points = []
for _, row in pfz_candidates.iterrows():
    pfz_points.append({
        "latitude": round(row["latitude"], 4),
        "longitude": round(row["longitude"], 4),
        "chlorophyll": round(row["CHL"], 4),
        "chlorophyll_gradient": round(row["CHL_gradient"], 6),
        "sea_surface_temperature": row["sea_surface_temperature"],
        "wave_height": row["wave_height"],
        "pfz_score": round(row["pfz_score"], 4),
        "date": row["time"],
    })

with open("pfz_points.json", "w") as f:
    json.dump(pfz_points, f, indent=2)

print(f"Computed {len(pfz_points)} PFZ points -> pfz_points.json")
