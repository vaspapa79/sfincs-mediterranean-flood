# Copernicus EMS — vector products

## URL pattern

```
https://cems-mapping-website.s3.eu-west-1.amazonaws.com/static/activations/
  {EVENT_ID}/{EVENT_ID}_{AOI}_{ITERATION}_vector.zip
```

Example:

```
https://cems-mapping-website.s3.eu-west-1.amazonaws.com/static/activations/
  EMSR122/EMSR122_01STRYMONAS_DELINEATION_OVERVIEW-MONIT02_v1_vector.zip
```

Each ZIP unpacks to a directory with shapefiles:

- `*area_of_interest.shp` — the AOI rectangle
- `*hydrography_poly.shp` — permanent water bodies (channels, lakes)
- `*hydrography_l.shp` — permanent streams (lines)
- `*crisis_information_poly.shp` — **observed-flood polygons** (MONIT iterations only)
- `*observed_event_a.shp` — alternate name in some older activations
- plus auxiliary administrative + transport layers

## Schema gotchas

- **Old (pre-2018) activations** (EMSR122, EMSR163, …) — only the
  DELINEATION_MONIT iterations carry observed-flood polygons in
  `*crisis_information_poly.shp`. REFERENCE_OVERVIEW iterations have only
  the AOI + permanent hydrography (no observed flood).
- **Newer activations** sometimes ship observed flood in
  `*observed_event_a.shp` or `*flooded_area_poly.shp` instead — check the
  shapefile names after the first extract.
- **CRS** varies — some shapefiles ship in EPSG:32634, others in
  EPSG:4326 or the country's local CRS. `download_ems.py` reads each
  shapefile's CRS via `pyogrio.read_info()` and reprojects to the
  config's target UTM via pyproj before merging.

## Finding AOIs for a new activation

Browse `https://mapping.emergency.copernicus.eu/activations/{EVENT_ID}/`
and read the right-hand panel — each "Map" listed there corresponds to
an AOI. The AOI slug is the part between the event ID and the iteration
name in the ZIP filename.

For Storm Daniel (EMSR692, September 2023, Greece) the AOIs include:
`01KARDITSA`, `02LARISSA`, `03VOLOS`, `04MAGNESIA`, … plus a unified
overview. The full list is documented in the Pineios reproduction
(`implementation/testcase/download_ems.py`).

## Iteration naming

`v1` and `v2` refer to versioning within the same iteration. Newer
versions supersede older ones. The skill downloads every listed
iteration and lets the merge step deduplicate at the polygon level
(union of all geometries).

Typical naming pattern:

- `REFERENCE_OVERVIEW_v{N}` — pre-event reference (AOI + hydrography only)
- `DELINEATION_OVERVIEW_v{N}` — first delineation (AOI + hydrography +
  sometimes observed-flood)
- `DELINEATION_OVERVIEW-MONIT01_v{N}` through `MONIT03_v{N}` —
  monitoring iterations, **these carry the observed-flood polygons**

## Merge convention

`download_ems.py` writes
`data/ems_polygons/EMSR{id}_observed_flood_all.gpkg` in the target UTM:

- One row per source shapefile, with a `source` column
- All polygons in `*crisis_information_poly.shp` from MONIT iterations
- Reprojected to the model UTM zone

Downstream scripts (`qc_alignment.py`, `make_animation.py`, `make_mp4.py`)
read the gpkg + the AOI shapefiles + the hydrography shapefiles directly
via `rglob`.
