API_KEY = "507f8740d56b68ba2c1d032c2c8a5a8F"

import requests

# set your API key before making the request
header = {"Authorization": API_KEY}

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

# query the api 
resp = requests.post(
    headers=header,
    json=args,
    url="https://openet-api.org/raster/timeseries/polygon"
)

print(resp.json())

# Output

# [{'time': '2021-01-01', 'eto': 34.813}, 
# {'time': '2021-02-01', 'eto': 37.959}, 
# {'time': '2021-03-01', 'eto': 72.688}, 
# {'time': '2021-04-01', 'eto': 109.62}, 
# {'time': '2021-05-01', 'eto': 132.212}, 
# {'time': '2021-06-01', 'eto': 187.495}, 
# {'time': '2021-07-01', 'eto': 203.199}, 
# {'time': '2021-08-01', 'eto': 161.826}, 
# {'time': '2021-09-01', 'eto': 108.796}, 
# {'time': '2021-10-01', 'eto': 65.536}, 
# {'time': '2021-11-01', 'eto': 44.059}, 
# {'time': '2021-12-01', 'eto': 27.996}]