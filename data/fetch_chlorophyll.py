"""
Pulls real chlorophyll + chlorophyll-gradient data from Copernicus Marine for
the Indian coast bounding box. Pre-fetched/cached deliberately, NOT called
live — the copernicusmarine toolbox is built for bulk subsetting, too slow to
call inside a live chat response. Re-run this whenever you want fresh PFZ
zones (once before a demo is plenty).

Dataset: cmems_obs-oc_glo_bgc-plankton_nrt_l3-olci-4km_P1D (global coverage,
confirmed to include the Indian Ocean, 4km resolution).

Requires: `copernicusmarine login` to have been run once already (see
data/README.md).
"""

import copernicusmarine
import xarray as xr
from datetime import datetime, timedelta

end_date = datetime.utcnow()
start_date = end_date - timedelta(days=7)

output_nc = "chlorophyll_snapshot.nc"

copernicusmarine.subset(
    dataset_id="cmems_obs-oc_glo_bgc-plankton_nrt_l3-olci-4km_P1D",
    variables=["CHL", "CHL_gradient"],
    minimum_longitude=68,
    maximum_longitude=90,
    minimum_latitude=8,
    maximum_latitude=22,
    start_datetime=start_date.strftime("%Y-%m-%dT00:00:00"),
    end_datetime=end_date.strftime("%Y-%m-%dT00:00:00"),
    output_filename=output_nc,
)

print(f"Downloaded -> {output_nc}")

ds = xr.open_dataset(output_nc)
df = ds.to_dataframe().reset_index()
df = df.dropna(subset=["CHL"])  # drop cloud-covered / no-data points

csv_path = "chlorophyll_snapshot.csv"
df.to_csv(csv_path, index=False)

print(f"Converted -> {csv_path}")
print(df.head())
