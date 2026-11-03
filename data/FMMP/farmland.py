from urllib.parse import urlencode
import requests
import geopandas as gpd

# public ArcGIS server, so no API key needed
BASE = "https://gis.conservation.ca.gov/server/rest/services/DLRP"

# endpoint arguments
args = {
  # P = Prime Farmland, S = Farmland of Statewide Importance, U = Unique Farmland,
  # G = Grazing Land, D = Urban and Built-up Land
  "where": "polygon_ty IN ('P', 'S', 'U', 'G', 'D')",
  "outFields": "county_nam,County,polygon_ty,polygon_ac,upd_year",
  "orderByFields": "OBJECTID",
  "outSR": 4326,
  "f": "json"
}


def latest_year():
  """Find the newest year with a CaliforniaImportantFarmland_<year> service"""

  # list every service in the DLRP folder
  resp = requests.get(BASE, params={"f": "json"})
  resp.raise_for_status()

  # keep names ending in a 4-digit year & take the newest
  return max(
      int(s["name"][-4:])
      for s in resp.json()["services"]
      if "ImportantFarmland_" in s["name"] and s["name"][-4:].isdigit()
  )


def query(year):
  """Query one year's farmland layer via the FeatureServer query endpoint"""

  # build request url
  url = f"{BASE}/CaliforniaImportantFarmland_{year}/FeatureServer/0/query?{urlencode(args)}"

  # GDAL's ESRIJSON driver pages past the server's 2000-record limit itself
  gdf = gpd.read_file("ESRIJSON:" + url)

  return gdf


# find most recent year & query
year = latest_year()
gdf = query(year)

# summarize acres per land class & export
print(gdf.groupby("polygon_ty")["polygon_ac"].sum())

gdf.to_file(f"farmland_{year}.shp")
gdf.to_file(f"farmland_{year}.geojson", driver="GeoJSON")
