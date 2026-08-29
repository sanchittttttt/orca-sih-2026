import copernicusmarine
import xarray as xr
from datetime import datetime, timedelta

# Last 7 days, up to today
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

# Convert to CSV so other modules (Spring Boot, Python agent) don't need
# to deal with NetCDF at all
ds = xr.open_dataset(output_nc)
df = ds.to_dataframe().reset_index()
df = df.dropna(subset=["CHL"])  # drop cloud-covered / no-data points

csv_path = "chlorophyll_snapshot.csv"
df.to_csv(csv_path, index=False)

print(f"Converted -> {csv_path}")
print(df.head())