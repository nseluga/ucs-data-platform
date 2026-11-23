# UCS Data Platform: Target Schema (MVP draft)

Draft for team review. Choices made are in section 8. Assumptions that need confirming are in section 9 and are referenced inline as (A1), (A2), and so on.

## 1. What this schema is for

The MVP map and the later report both read the same thing: **for a community, the fixed MTRS squares ("sections") around it, and a few values per section per layer.** Sections are fixed, and communities can share them.

There are two forms of data:

| Form | What it is | Who reads it |
|---|---|---|
| **Polygon form** | Each source layer cleaned into one standard feature table (FMMP polygons, crop fields, Williamson Act parcels, OpenET fields). | The pipeline only. Too big for the browser (FMMP 2022 alone is 407 MB / 92,827 polygons as GeoJSON). |
| **Section form** | Small tables keyed by `section_id`: values per section per layer, plus a community-to-section crosswalk. | The frontend and the report. |

Polygon form is the source of truth. Section form is always derived from it. Community boundaries stay as polygons and are served as-is. They are not converted to sections.

## 2. Conventions (apply to every table)

- **Source CRSs differ.** DPR sections are EPSG:3310, the DWR DAC layers, Land IQ and Williamson Act are served in EPSG:3857, and TIGER is probably EPSG:4269. Reproject on load.
- **Geometry is stored in EPSG:4326** (lon/lat).
- **Area and overlap math is done in EPSG:3310** (California Albers, equal-area). Never compute acres or overlap in degrees or in 3857, which stretches area.
- **Acres are recomputed** from geometry (`area_acres`), not taken from the source's `polygon_ac`, `ACRES` or `Acreage`.
- **Every derived row carries lineage:** `layer_id` + `edition` point at a row in `layer_registry`, which holds source, retrieval date, status and disclaimer.
- **IDs are text**, never numbers (section IDs have letters, GEOIDs have leading zeros).
- **Missing coverage is explicit:** if a source has no data for a place (FMMP 2022 is missing counties), the row exists with `coverage_pct` below 100 or 0, so the UI can say "no data" instead of showing empty.
- **Zero is not missing.** DWR stores median income as 0 where data is not available. Load those as null.

## 3. Tables

### 3.1 `layer_registry` (one row per layer edition)

Also serves as the index of files.

| Column | Type | Example | Notes |
|---|---|---|---|
| `layer_id` | text, PK part | `fmmp` | stable slug |
| `edition` | text, PK part | `2022` | year, or `2021-01..2021-12` for OpenET pulls |
| `status` | enum | `final` \| `provisional` | Land IQ 2024 is provisional while 2023 is final |
| `ds_id` | text | `5` | row in the UCS dataset sheet; null for reference layers |
| `name` | text | `Important Farmland (FMMP)` | |
| `source_org`, `source_url` | text | CA Dept of Conservation | |
| `native_geometry` | enum | `polygon` \| `parcel` \| `field` \| `section` | what the raw data is |
| `level` | enum | `section` \| `community` | where it is shown (A5) |
| `retrieved_at` | timestamp | | set by the pipeline run |
| `refresh` | text | `biennial` | informational |
| `license`, `coverage_note` | text | `CC BY` | see A10 |
| `raw_path`, `processed_path` | text | `raw/fmmp/2022/2026-11-23/` | S3 keys |
| `disclaimer_en`, `disclaimer_es` | text | "General planning use only" | English and Spanish |

### 3.2 `section` (reference, loaded once)

One row per MTRS section. This is the fixed spatial unit everything rolls up to.

| Column | Type | Notes |
|---|---|---|
| `section_id` | text, PK | The 9-character `MTRS` code from DPR, for example `H19N01W32` (meridian H, township 19N, range 01W, section 32). See A1 for the format question. |
| `meridian`, `township`, `range`, `section_no` | text/int | parsed from the id (DPR also supplies them as `BASE_LN_ME`, `TOWNSHIP`, `RANGE`, `SECTION`) |
| `counties` | text list | county codes the section touches. A section can cross county lines. |
| `area_acres` | float | usually about 640 but varies, so store it |
| `geometry` | polygon | |

Source: DPR PLSNET layer 1, "Sections no County (MTRS)", 158,680 features, one per section. DPR layer 0 has 164,639 features because it splits sections at county lines and keys them by an 11-character `CO_MTRS` such as `08H19N01W32`. We use layer 1 so one square has one id. Layer 0 is only needed to fill `counties`.

### 3.3 `community` (reference, one row per community)

Holds everything that belongs to the whole community, not to a square: DAC status, population, median household income.

| Column | Type | Notes |
|---|---|---|
| `community_id` | text, PK | GEOID. 7 characters for a place (`0666140`), 11 for a tract, 12 for a block group. See A2. |
| `community_level` | enum | `place` \| `tract` \| `block_group` |
| `name` | text | DWR `PlaceNames`, for example "San Fernando city" (tracts and block groups have no name) |
| `dac_status` | enum | `dac` \| `sdac` \| `not_dac` \| `unknown`. Kept separate from "is a community". |
| `population`, `households`, `median_hh_income` | int | from `Pop23`, `HH23`, `MHI23`; income is null when DWR gives 0 |
| `acs_period` | text | `2019-2023` (ACS 5-year) |
| `county_fips` | text | |
| `geometry` | polygon/multipolygon | official boundary, shown as a polygon |
| `source_edition` | text | which community file version |

`dac_status` is set as in D8.

### 3.4 `community_section` (the crosswalk)

Many-to-many. A section can appear under several communities, and a community has many sections.

| Column | Type | Notes |
|---|---|---|
| `community_id` | text, PK part | |
| `section_id` | text, PK part | |
| `zone` | enum | `core` (section overlaps the community) \| `buffer` (section only touches the buffer). See A3. |
| `overlap_pct` | float | share of the **section's** area covered by the community |
| `is_primary` | bool | true for the community with the largest overlap when two share a section |

Rows below a minimum `overlap_pct` are dropped. The threshold is a pipeline config parameter, not hard-coded (A4).

### 3.5 `section_values` (long format, all layers)

One row per section per layer per measure. A new layer needs no new columns.

| Column | Type | Notes |
|---|---|---|
| `layer_id`, `edition` | text | FK to `layer_registry` |
| `section_id` | text | FK to `section` |
| `variable` | text | what is measured: `acres`, `pct_of_section`, `et_mm_mean`, ... |
| `category` | text, nullable | class code within the layer: FMMP `P`, Land IQ crop class, Williamson Act `Prime` |
| `period` | text, nullable | `2021-07` for monthly OpenET, null for static layers |
| `value` | float | |
| `unit` | text | `acres`, `percent`, `mm` |
| `coverage_pct` | float | share of the section the source actually covers (0 for missing counties) |

Primary key: `(layer_id, edition, section_id, variable, category, period)`.

### 3.6 `categories` (small lookup, for labels)

`(layer_id, category, label_en, label_es, color)`. Keeps raw codes like `P` or `polygon_ty` out of the UI and puts Spanish labels in one place.

### 3.7 Polygon form: `features` (one standard table per layer edition, pipeline only)

| Column | Type | Notes |
|---|---|---|
| `feature_id` | text | source id (Land IQ `UniqueID`, Williamson Act `APN_Number`, OpenET field id), or generated and stable within an edition |
| `layer_id`, `edition` | text | |
| `category` | text | normalized class (FMMP `polygon_ty`, Land IQ crop class, Williamson Act `WA_Type`); null for OpenET |
| `share_pct` | float | Land IQ only: the field's share for this class (`PCNT1` to `PCNT4`). 100 elsewhere. |
| `area_acres` | float | recomputed in EPSG:3310 |
| `attrs` | json | any extra source columns we keep; for OpenET, the monthly ET values |
| `geometry` | polygon/multipolygon | repaired and valid (no self-intersections), EPSG:4326 |

## 4. How polygon form becomes section form

One rule per kind of variable:

| Kind | Layers | Rule |
|---|---|---|
| Category area | FMMP, Land IQ crops, Williamson Act | Intersect features with `section`; sum the overlap area by `category`; `pct_of_section` = that sum / section area; `coverage_pct` = covered area / section area. For Land IQ, one field holds up to four crops, so each class gets `overlap_area × share_pct / 100`. |
| Continuous measure | OpenET | Store OpenET's own field polygons with their monthly ET in `features`. A section's value is the area-weighted mean over the fields that overlap it (also min and max). Units stay in mm; acre-feet is a separate variable computed from area. See A6. |
| Pre-aggregated | CalPIP pesticide (Core phase) | Already at section level; just reshape into `section_values`. |

Community-level data (DAC status, income) never goes through this step.

**OpenET limits that shape this.** The batch endpoints (`multipolygon`) have been disabled since API v3.2.2 (2026-08-11), so the raster route takes one polygon per request. The free tier allows 100 requests a month and 50,000 acres per request. Linking an Earth Engine account raises that to 400 requests. At that rate, one request per section covers only 100 to 400 sections a month, so per-section queries cannot cover the state. The geodatabase route returns OpenET's fixed field polygons: one call lists the field ids inside an area, then ET is fetched per field id (100 ids per query, 400 with a linked account). Prior-month data is ready by about the 5th.

## 5. MVP dataset mapping

MVP layers are sheet IDs 1, 2, 4, 5, 6 and 8, plus the MTRS squares, which the sheet does not list.

| DS | Layer | Lands in | How we pull it | Gotchas |
|---|---|---|---|---|
| (ref) | MTRS sections, DPR PLSNET | `section` | ArcGIS REST layer 1, 2,000 rows per page, about 80 pages; also a statewide shapefile zip. EPSG:3310. | DPR says the data is "valid only for DPR-specific reporting purposes" (A10). Grant areas may use synthetic grid sections. BLM's national PLSS is an alternative but uses different ids and has no MTRS string. |
| 1 | DWR DAC tool (2023, ACS 2019-2023) | `community` | ArcGIS REST on the CNRA-hosted copies (place, tract, block group, county), 2,000 rows per page, JSON or GeoJSON, no key. Bulk shapefile/GeoJSON/CSV downloads also exist. Service CRS 3857. | `DAC23` is Y/N only. Tract and block group ids are `GEOID20` (2020 vintage). Income 0 means no data. The DAC app page is a JS shell with no data links. |
| 2 | Census TIGER/Line 2026 | `community` (name and county lookup only) | `www2.census.gov/geo/tiger/TIGER2026/<LAYER>/tl_2026_06_<name>.zip`, shapefile. Place 9.9 MB, tract 32.5 MB, block group 52.8 MB (state files); county is national, 83 MB, filter `STATEFP=06`. | No demographics inside. Boundaries are 2026 and DWR's are 2020, so join by GEOID, never by geometry. `NAME` is "San Fernando", `NAMELSAD` is "San Fernando city". |
| 4 | Land IQ crop mapping (DWR statewide) | `features` then `section_values` | CKAN API `package_show?id=statewide-crop-mapping`, then per-year shapefile/GDB zips of about 100-240 MB, or an ArcGIS MapServer (2023: 446,914 fields, 2,000 per page, about 225 pages, EPSG:3857). | Newest final is 2023, 2024 is provisional. No year field inside the data, so we set `edition` ourselves. Column names drift between years. Up to four crops per field (`CLASS1-4`, `PCNT1-4`). |
| 5 | FMMP Important Farmland | `features` then `section_values` | `farmland.py` over ArcGIS REST. Writes `county_nam, County, polygon_ty, polygon_ac, upd_year` (92,827 polygons, 45 county codes in 2022). | Map `polygon_ty` to `category`, recompute acres, record the edition, record missing counties. |
| 6 | Williamson Act | `features` then `section_values` | Statewide parcel FeatureServer, layer 9: 123,980 parcels, EPSG:3857. One service per year (2021-2025). No bulk zip found. | `County_Cit` is inconsistent and mixes cities with counties, so derive county by geometry. Some `Year` values are blank. Some counties are stale or missing. |
| 8 | OpenET | `features` (fields) then `section_values` (`et_mm_*`) | OpenET geodatabase endpoints (section 4). `polygon.py` today writes one hard-coded polygon, 12 monthly rows, 7 model columns side by side. | Store geometry once and values long (`period`, `model` become rows). Recent months can be revised for up to 6 months. |

## 6. S3 layout

Two folders: an ingest side that is never edited, and a processed side the frontend reads.

```
s3://<bucket>/
  raw/<layer_id>/<edition>/<retrieved_date>/...        # untouched downloads, never overwritten
  processed/
    reference/section.geojson
    reference/community.geojson
    reference/community_section.json
    features/<layer_id>/<edition>.parquet              # polygon form, pipeline only
    values/<layer_id>/<edition>.json                   # section_values slice (statewide)
    values/by_community/<layer_id>/<community_id>.json # serving view, optional (A8)
  catalog/layer_registry.json                          # index of everything above
```

A run writes a new `raw/` path, builds the new `processed/` files, and updates `catalog/layer_registry.json` last. Rerunning the same edition rewrites the same keys, so runs are idempotent.

## 7. Example rows

Values are illustrative. The ids follow the real formats.

```json
{"layer_id": "fmmp", "edition": "2022", "section_id": "H19N01W32",
 "variable": "acres", "category": "P", "period": null,
 "value": 412.6, "unit": "acres", "coverage_pct": 100.0}
```

```json
{"community_id": "0666140", "section_id": "H19N01W32",
 "zone": "core", "overlap_pct": 38.5, "is_primary": true}
```

## 8. Decisions made

- **D1. Storage and math CRS.** Store geometry in EPSG:4326. Do all area and overlap math in EPSG:3310.
- **D2. Acres.** Recompute from geometry. Ignore the source's acre columns.
- **D3. Polygon form first.** Polygon form is the source of truth. Section form is derived from it. Communities are not converted to sections.
- **D4. Section ID.** Use DPR layer 1's 9-character `MTRS` code, one id per square, not split by county.
- **D5. Long format.** `section_values` is one long table, so a new layer needs no new columns.
- **D6. Missing data.** Missing coverage gets a row with `coverage_pct` below 100. Income 0 becomes null.
- **D7. Land IQ crops.** A field's acres are split across its up to four crops by `share_pct`.
- **D8. DAC status.** `dac` is DWR's `DAC23 = Y`. `sdac` is computed from `median_hh_income` below 60% of statewide median household income. `unknown` is DWR's "Data Not Available".
- **D9. Layer choice per source.** Williamson Act county comes from geometry, not `County_Cit`. Community names use the `NAMELSAD` style. Community joins use GEOID, not geometry.
- **D10. S3.** Two folders (`raw/` never edited, `processed/` read by the frontend), with the catalog updated last so runs are idempotent.

## 9. Assumptions to confirm

1. **A1. Section ID format.** The schema assumes DPR's `H19N01W32`. The team's prototype shows IDs like `MDM-T15S-R39E-27`. Which one does the UCS section key use, and does it list each square once or once per county? If it is the prototype format, `section_id` changes and DPR codes are converted once.
2. **A2. Community level.** The schema assumes place-level communities (the prototype examples are cities). Are tracts and block groups needed? Is the DWR 2023 file the canonical community list, or the file UCS sent with extra communities?
3. **A3. Buffer.** The schema assumes buffers are squares around a community. Is that sections that touch the boundary, every section within 1 mile, or a round buffer polygon?
4. **A4. Overlap rules.** The schema assumes a minimum overlap percent drops a section, and that the largest overlap decides the primary community. What is the percent?
5. **A5. Section vs community level.** The schema assumes FMMP, crops and Williamson Act are section-level and DAC data is community-level. OpenET and Williamson Act need confirming.
6. **A6. OpenET route.** The schema assumes OpenET's own field polygons are rolled up to sections. The alternatives are one query per section (does not fit the quota) or live click and draw (one request per click). Does UCS have, or can it request, a higher quota?
7. **A7. History.** The schema assumes monthly OpenET series over several years and the latest edition of the other layers. How many OpenET years and which older editions do we keep?
8. **A8. Frontend reads.** The schema assumes static JSON files from S3. Statewide `values` files may be too big for a browser, so per-community files may be needed.
9. **A9. Report.** The schema assumes the report is not in the MVP, so `by_community` and the report templates wait.
10. **A10. Licenses.** DWR's data is CC BY on data.gov, but its item text says "For Official Use Only". DPR limits its sections to DPR reporting. Land IQ states no license. Are we allowed to republish these as a public layer?
11. **A11. SDAC cutoff.** The statewide median household income for the 60% line is not in any DWR document. The DWR tract data suggests a DAC cutoff near $77,060, which would put the 60% line near $57,800. Confirm the figure, or drop the computed `sdac` value and show DWR's Y/N only.
12. **A12. Reference layers.** The Kaweah example uses streams, Corcoran Clay and GSAs. If those are in the MVP, the schema needs line geometry.
13. **A13. Section shading.** The bivariate map needs one number per layer per section. The schema assumes the user picks one category and we shade by its `pct_of_section`.
