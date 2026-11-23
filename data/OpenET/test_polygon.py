"""Run after `python polygon.py`:  pytest -q test_polygon.py"""
import numpy as np, pandas as pd, pytest, geopandas as gpd

MODELS = ["Ensemble", "geeSEBAL", "SSEBop", "SIMS", "DisALEXI", "PTJPL", "eeMETRIC"]


@pytest.fixture(scope="module")
def C(): return pd.read_csv("openet.csv", index_col="time")

@pytest.fixture(scope="module")
def S(): return gpd.read_file("openet.shp")

@pytest.fixture(scope="module")
def G(): return gpd.read_file("openet.geojson")


def test_csv_matches_shp(C, S):
  # catches renamed/truncated columns, dropped rows and altered values
  assert list(C.columns) == MODELS and list(S.columns) == ["time"] + MODELS + ["geometry"]
  assert list(S.time) == list(C.index)
  for m in MODELS:
    assert np.allclose(S[m], C[m]), m


def test_shp_sane(S):
  assert S.crs.to_epsg() == 4326
  assert not S.isna().any().any() and not S.is_empty.any() and S.is_valid.all()
  # bounds of the query polygon (minx, miny, maxx, maxy) catch swapped lon/lat
  assert np.allclose(S.total_bounds, [-120.093123, 36.079649, -120.082102, 36.087047])


def test_geojson_equals_shp(S, G):
  assert len(S) == len(G) and list(S.columns) == list(G.columns) and S.crs == G.crs
  # compare as text: geojson reader parses the time strings into dates, shp keeps them as text
  for c in S.columns.drop("geometry"):
    assert (S[c].astype(str).values == G[c].astype(str).values).all(), c
  # tolerance 1e-9 deg (~0.1 mm); normalize() ignores ring start/orientation differences
  assert S.geometry.normalize().geom_equals_exact(G.geometry.normalize(), 1e-9).all()
