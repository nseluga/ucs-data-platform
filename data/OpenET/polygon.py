import os
from dotenv import load_dotenv
import requests
import pandas as pd

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
  "geometry": [
    -121.00747,
    44.2442,
    -121.00747,
    44.24742,
    -121.00295,
    44.24742,
    -121.00295,
    44.24422
  ],
  "model": "SIMS",
  "variable": "ETo",
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
  df = pd.DataFrame(resp.json())  \
    .set_index("time")  \
    .rename(columns={args["variable"] : args["model"]})

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
