# ORCA — Data Sources

This document lists every data source used by ORCA, exactly what's live vs. simulated,
and the reasoning behind every methodological decision made while building the dataset
pipeline. Written for the Feasibility & Viability slide (M6) and for direct scrutiny by
ISRO judges — nothing here is hidden or glossed over.

---

## 1. Weather — Open-Meteo

**Status:** Live, real, free, no API key required.

- Endpoint: `https://api.open-meteo.com/v1/forecast`
- **In production:** called live, per-user-query, by the AI Agent service (`ai-service/tools.py`).
- `data/fetch_weather.py` is a verification/reference script only — proves the API works
  and documents the response shape. Not part of the production data path.

---

## 2. Ocean Waves & Sea Surface Temperature — Open-Meteo Marine

**Status:** Live, real, free, no API key required.

- Endpoint: `https://marine-api.open-meteo.com/v1/marine`
- **In production:** called live for single-location queries, same as weather.
- **Also used in a batch/grid mode** (`data/fetch_marine.py`) to build a coarse
  (~2° spacing) SST grid across the Indian coast bounding box. One of two real inputs
  to PFZ computation.

---

## 3. Chlorophyll & Chlorophyll Gradient — Copernicus Marine

**Status:** Live, real, free with registration. Pre-fetched/cached, not called live.

- Dataset ID: `cmems_obs-oc_glo_bgc-plankton_nrt_l3-olci-4km_P1D`
- Fields used: `CHL` (mg/m³), `CHL_gradient`
- Coverage: Global — confirmed to include the full Indian Ocean, 4km resolution.
- **Why pre-fetched:** the `copernicusmarine` toolbox is built for bulk subsetting, not
  fast per-request calls. Not suitable to call inside a live chat response. This matches
  how INCOIS itself operates — advisories are published periodically, not computed live.

### Data quality step — turbid-coastal-water filtering

Raw data includes values up to 290 mg/m³ near river mouths/harbors (Gulf of Kutch, Kochi
backwaters, Mumbai harbor). Real open-ocean chlorophyll rarely exceeds ~10 mg/m³ even
during strong blooms — this is a known sensor artifact, **turbid-water retrieval error**,
where coastal sediment confuses the satellite's ocean-color algorithm.

Distribution from a full week of real data:

| Percentile | CHL value (mg/m³) |
|---|---|
| 50th | 0.29 |
| 75th | 0.44 |
| 90th | 1.02 |
| 95th | 2.74 |
| 99th | 11.75 |

The sharp discontinuity between the 95th and 99th percentiles is the fingerprint of
contamination on top of a normal distribution. **We exclude all points above the 95th
percentile** — derived from the data itself, not an arbitrary guess. This range aligns
well with the real, documented Southwest Monsoon upwelling bloom (3-8 mg/m³) along the
Kerala/Karnataka coast in August.

**Fix applied:** the cap is computed on the FULL week's distribution *before* filtering
to a single day, not recalculated on an already-date-filtered subset — this was a
previously-known limitation, now corrected in `compute_pfz.py`.

---

## 4. Potential Fishing Zones (PFZ) — Computed, not mocked

**Status:** Computed from real data, using INCOIS's real published methodology.

INCOIS has no public REST API — it distributes advisories only via WebGIS/SMS. Rather
than fabricating coordinates, `compute_pfz.py` implements INCOIS's own published method
(SST fronts + chlorophyll concentration) using the two real datasets above:

1. Load the dense chlorophyll+gradient grid (Copernicus) and the coarser SST/wave grid
   (Open-Meteo Marine).
2. Filter chlorophyll to the full week's 95th-percentile cap (Section 3), then to the
   latest available date, for a single-day advisory.
3. For each chlorophyll point, find its nearest SST point (nearest-neighbor matching —
   standard practice for combining heterogeneous-resolution satellite/model products).
4. Normalize chlorophyll and gradient to 0-1, score = `0.6 × chl_norm + 0.4 × gradient_norm`.
5. Take the top 15% of scores, capped at 50 points, as the final advisory list.

**What's real vs. our own choice:** every input number (chlorophyll, gradient, SST, wave
height) is real satellite/model data. The scoring weights (0.6/0.4) and selection
threshold (top 15%/50) are our own reasonable implementation choices, since INCOIS's
exact internal formula isn't public — only the general method is. Disclosed plainly, not
presented as an exact replica of INCOIS's internal system.

**Validation:** top-scoring points cluster along the Kerala coast, consistent with the
real, documented Southwest Monsoon upwelling season occurring during this period — a
strong signal the pipeline captures genuine oceanographic signal, not noise.

---

## 5. Cyclone Alerts — GDACS

**Status:** Live, real, free, no API key required.

- Endpoint: `https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH`
- Filtered to `eventlist=TC`, last 14 days, bounding box (0-30°N, 60-100°E)
- **In production:** called live, per-query, directly by `ai-service/tools.py` — same
  reasoning as weather. `data/fetch_cyclone.py` is a reference/verification script only.
- Verified working: confirmed correctly returning 0 India-region alerts when 1 real
  global cyclone existed outside the bounding box — checked the total global count before
  applying the geographic filter to rule out silent failure.

---

## 6. Lightning Alerts — Simulated

**Status:** Fully simulated. No free real-time lightning-alert API for India was found.

- `data/generate_lightning_mock.py` generates a plausible alert level per coastal region.
- The **only** dataset in ORCA that is entirely fabricated, labeled as such in its own
  output (`"source": "SIMULATED..."`).

---

## 7. Maritime Boundaries & Marine Protected Areas

**Status:** Deferred as a stretch goal — not blocking MVP.

Real sources identified: Marine Regions (World EEZ v12, GeoPackage/Shapefile — no direct
GeoJSON, requires filtering to India via geopandas) and Protected Planet (free API,
`country=IND&marine=true&with_geometry=true`). Low demo-impact, independent of everything
else — revisit only if time remains near the deadline.

---

## Summary Table

| Source | Data | Status | Method |
|---|---|---|---|
| Open-Meteo | Weather | Live | Called per-query in production |
| Open-Meteo Marine | Waves, SST | Live | Called per-query, or batch for PFZ input |
| Copernicus Marine | Chlorophyll, gradient | Live, cached | Pre-fetched due to toolbox latency |
| — | PFZ | **Computed** | Real INCOIS method applied to real data |
| GDACS | Cyclone alerts | Live | Called live, per-query, filtered to India |
| — | Lightning alerts | **Simulated** | No free real-time source exists for India |
| Marine Regions / Protected Planet | Boundaries, MPAs | Pending | Static GeoJSON download |
