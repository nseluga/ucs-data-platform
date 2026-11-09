import os
from dotenv import load_dotenv
import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

# load secrets from .env so the API key never lives in the code
load_dotenv()
API_KEY = os.environ["OPENET_API_KEY"]

# endpoint arguments
args = {
  "date_range": [
    "2021-01-01",
    "2021-12-31"
  ],
  "interval": "monthly",
  # a Prime Farmland polygon from FMMP (Fresno County, ~112 acres), so OpenET overlaps farmland
  "geometry": [
    -120.082102,
    36.087047,
    -120.091694,
    36.079649,
    -120.093123,
    36.079657,
    -120.093046,
    36.086956
  ],
  "model": "SIMS",
  "variable": "ET",
  "reference_et": "gridMET",
  "reducer": "mean",
  "units": "mm",
  "file_format": "JSON"
}


def query(args):
  """Query the OpenET API with via raster/timeseries/polygon endpoint"""

  # set your API key before making the request
  header = {"Authorization": API_KEY}

  # make request
  resp = requests.post(
      headers=header,
      json=args,
      url="https://openet-api.org/raster/timeseries/polygon"
  )

  # convert to dataframe structure
  # API names the column after the variable (lowercase), so name it after the model instead
  df = pd.DataFrame(resp.json())  \
    .set_index("time")  \
    .rename(columns=lambda _: args["model"])

  return df

# models of interest
models = ["Ensemble", "geeSEBAL", "SSEBop", "SIMS", "DisALEXI", "PTJPL", "eeMETRIC"]

dfs = []
for m in models:
    
    # update & query
    args.update({"model": m})
    dfs.append(query(args))

# combine results & export
df = pd.concat(dfs, axis=1)
print(df)

df.to_csv("openet.csv")

# attach the query polygon to every month: flat lon/lat list -> (lon, lat) pairs
# (shapely closes the ring itself)
coords = list(zip(args["geometry"][::2], args["geometry"][1::2]))
gdf = gpd.GeoDataFrame(df.reset_index(), geometry=[Polygon(coords)] * len(df), crs=4326)

gdf.to_file("openet.shp")
gdf.to_file("openet.geojson", driver="GeoJSON")
