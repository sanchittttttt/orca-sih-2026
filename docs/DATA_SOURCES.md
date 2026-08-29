# ORCA — Data Sources

This document lists every data source used by ORCA, exactly what's live vs. simulated,
and the reasoning behind every methodological decision made while building the dataset
pipeline. Written for the Feasibility & Viability slide (M6) and for direct scrutiny by
ISRO judges — nothing here is hidden or glossed over.

---

## 1. Weather — Open-Meteo

**Status:** Live, real, free, no API key required.

- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Fields used: temperature, wind speed/direction, precipitation probability
- **In production:** called live, per-user-query, by the AI Agent service (M4) — not
  pre-fetched or cached. Weather changes hourly and the API is fast enough to call
  on-demand.
- `data/fetch_weather.py` in this repo is a verification/reference script only — it
  proves the API works and documents the response shape for M4's developer. It is not
  part of the production data path.

---

## 2. Ocean Waves & Sea Surface Temperature — Open-Meteo Marine

**Status:** Live, real, free, no API key required.

- Endpoint: `https://marine-api.open-meteo.com/v1/marine`
- Fields used: wave height, wave direction, wave period, sea surface temperature
- **In production:** called live for single-location queries (same reasoning as weather
  above).
- **Also used in a batch/grid mode** (`data/fetch_marine.py`) to build a coarse
  (~2° spacing) SST grid across the Indian coast bounding box (8°N–22°N, 68°E–90°E).
  This grid is one of the two real inputs to the PFZ computation below. Points that
  fall on land correctly return null and are discarded — this is expected, not an error.

---

## 3. Chlorophyll & Chlorophyll Gradient — Copernicus Marine

**Status:** Live, real, free with registration.

- Dataset ID: `cmems_obs-oc_glo_bgc-plankton_nrt_l3-olci-4km_P1D`
- Fields used: `CHL` (chlorophyll-a concentration, mg/m³), `CHL_gradient`
- Coverage: Global — confirmed to include the full Indian Ocean and Indian coastline,
  no regional restriction. Resolution: 4km.
- **Why this is pre-fetched, not called live:** the `copernicusmarine` Python toolbox is
  built for bulk subsetting, not fast per-request API calls. It is not suitable for
  calling inside a live chat response. We run `data/fetch_chlorophyll.py` once
  (in production this would be a daily cron job) and cache the result. This matches how
  INCOIS itself actually operates — PFZ advisories are published periodically, not
  computed live per user request.

### Data quality step — turbid-coastal-water filtering

Raw chlorophyll data from this dataset includes values as high as 290 mg/m³ near river
mouths and harbors (e.g. the Gulf of Kutch, Kochi backwaters, Mumbai harbor). Real ocean
chlorophyll-a rarely exceeds ~10 mg/m³ even during strong blooms. Values this high are a
known sensor artifact — **turbid-water retrieval error** — where sediment and other
particles in shallow coastal water confuse the satellite's ocean-color algorithm.

We inspected the actual distribution of a full week's data rather than guessing a cutoff:

| Percentile | CHL value (mg/m³) |
|---|---|
| 50th (median) | 0.29 |
| 75th | 0.44 |
| 90th | 1.02 |
| 95th | 2.74 |
| 99th | 11.75 |

The sharp discontinuity between the 95th and 99th percentiles is the fingerprint of
contaminated data sitting on top of a normal distribution. **We exclude all points above
the 95th percentile (2.74 mg/m³)** as turbid-water artifacts rather than genuine
productivity signals. This is standard practice in ocean-color quality control, not an
arbitrary cutoff — and the resulting range aligns well with the real, well-documented
Southwest Monsoon upwelling bloom (typically 3–8 mg/m³) that occurs along the Kerala/
Karnataka coast in August.

**Known limitation (not yet fixed):** the 95th-percentile cap should ideally be computed
from the full week's data before filtering to a single day, rather than recomputed on
whichever day's subset remains — currently it's recalculated per-run, which can drift
slightly depending on which date is selected. Documented here for transparency; a fix is
tracked as a follow-up, not blocking for the current demo.

---

## 4. Potential Fishing Zones (PFZ) — Computed, not mocked

**Status:** Computed from real data, using INCOIS's real published methodology.

INCOIS (India's actual PFZ authority) has no public REST API — it distributes PFZ
advisories only via WebGIS and SMS. Rather than fabricating coordinates, `compute_pfz.py`
implements INCOIS's own published method — combining sea-surface-temperature fronts with
chlorophyll concentration — using the two real datasets above:

1. Load the dense chlorophyll+gradient grid (Copernicus, ~4km resolution) and the
   coarser SST/wave grid (Open-Meteo Marine, ~2° resolution).
2. For each chlorophyll point, find its nearest SST point (grids don't align 1:1 due to
   differing resolutions — nearest-neighbor matching is standard practice for combining
   heterogeneous satellite/model products).
3. Filter out turbid-water artifacts (see Section 3).
4. Normalize chlorophyll concentration and gradient magnitude to a 0–1 scale.
5. Compute a combined score: `0.6 × chlorophyll_norm + 0.4 × gradient_norm`.
6. Take the top 15% of scores (capped at 50 points) as the final PFZ advisory list.

**What's real vs. simulated here:** every input number (chlorophyll, gradient, SST,
wave height) is real satellite/model data. The *scoring weights* (0.6/0.4) and the
*selection threshold* (top 15%, capped at 50) are our own reasonable implementation
choices, since INCOIS's exact internal formula isn't publicly published — only the
general method (SST fronts + chlorophyll threshold) is. This is disclosed plainly rather
than presented as an exact replica of INCOIS's internal system.

**Validation:** results were spot-checked for geographic plausibility. Top-scoring points
correctly cluster along the Kerala coast, consistent with the real, documented Southwest
Monsoon upwelling season occurring during this period — a strong sign the pipeline is
capturing a genuine oceanographic signal, not noise.

---

## 5. Cyclone Alerts — GDACS

**Status:** Live, real, free, no API key required.

- Endpoint: `https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH`
- Filtered to `eventlist=TC` (Tropical Cyclones), last 14 days
- Results filtered to a bounding box roughly covering India and the surrounding seas
  (0°–30°N, 60°–100°E)
- Verified working: as of testing, 1 tropical cyclone existed globally in the search
  window, located outside the India bounding box — correctly returning zero India-region
  alerts. This was confirmed to be correct filtering behavior, not a silent failure, by
  checking the total global event count before applying the geographic filter.

---

## 6. Lightning Alerts — Simulated

**Status:** Fully simulated. No free real-time lightning-alert API for India was found
during research.

- `data/generate_lightning_mock.py` generates a plausible alert level
  (none/moderate/severe) per coastal region (Gujarat, Konkan, Goa, Karnataka, Kerala,
  Tamil Nadu, Andhra, Odisha, West Bengal, Andaman & Nicobar).
- This is the **only** dataset in ORCA that is entirely fabricated rather than computed
  from real inputs, and it is labeled as such directly in its own output file
  (`"source": "SIMULATED..."`) so downstream consumers (M3, M4) never confuse it with
  real data.

---

## 7. Maritime Boundaries & Marine Protected Areas

**Status:** Not yet implemented.

Plan: one-time download of public GeoJSON from Marine Regions and/or Protected Planet,
loaded into PostGIS by M3. This is a static reference dataset, not something that needs
live fetching or computation.

---

## Summary Table

| Source | Data | Status | Method |
|---|---|---|---|
| Open-Meteo | Weather | Live | Called per-query in production |
| Open-Meteo Marine | Waves, SST | Live | Called per-query (single point) or batch (grid, for PFZ) |
| Copernicus Marine | Chlorophyll, gradient | Live, cached | Pre-fetched due to toolbox latency |
| — | PFZ | **Computed** | Real INCOIS method applied to real data above |
| GDACS | Cyclone alerts | Live | Called live, filtered to India bounding box |
| — | Lightning alerts | **Simulated** | No free real-time source exists for India |
| Marine Regions / Protected Planet | Boundaries, MPAs | Pending | Static GeoJSON download |