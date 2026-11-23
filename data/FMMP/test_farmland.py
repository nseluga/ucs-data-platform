"""Run after `python farmland.py`:  pytest -q test_farmland.py"""
import glob, pytest, requests, geopandas as gpd

shp = sorted(glob.glob("farmland_*.shp"))[-1]
geojson = shp.replace(".shp", ".geojson")
BASE = "https://gis.conservation.ca.gov/server/rest/services/DLRP"


@pytest.fixture(scope="module")
def S(): return gpd.read_file(shp)

@pytest.fixture(scope="module")
def G(): return gpd.read_file(geojson)


def test_shp_matches_server(S):
  year = S.upd_year.iloc[0]
  for cls, n in S.groupby("polygon_ty").size().items():
    r = requests.get(f"{BASE}/CaliforniaImportantFarmland_{year}/FeatureServer/0/query",
                     params={"where": f"polygon_ty='{cls}'", "returnCountOnly": "true", "f": "json"})
    assert r.json()["count"] == n, cls


def test_shp_sane(S):
  assert S.crs.to_epsg() == 4326
  assert set(S.polygon_ty) == set("PSUGD")
  assert not S.isna().any().any() and not S.is_empty.any()


def test_geojson_equals_shp(S, G):
  assert len(S) == len(G) and list(S.columns) == list(G.columns) and S.crs == G.crs
  for c in S.columns.drop("geometry"):
    assert (S[c].values == G[c].values).all(), c
  # tolerance 1e-9 deg (~0.1 mm); normalize() ignores ring start/orientation differences
  assert S.geometry.normalize().geom_equals_exact(G.geometry.normalize(), 1e-9).all()
