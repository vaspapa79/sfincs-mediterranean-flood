# Event config schema

Every script in `scripts/` accepts `--config path/to/event.yaml`. The
config has the following structure. Fields marked **required** must be
present; others have sensible defaults.

```yaml
event:
  id: EMSR122            # optional — null/empty for non-EMS events
  name: Strymonas        # short event label, used in titles
  slug: strymonas        # filesystem-safe; defaults to lowercase(name)
  date: 2015-03-31       # required — ISO 8601 calendar date of the event
  location: "Central Macedonia, Greece"  # human-readable for the docs
  reason: "Heavy rainfall + Kerkini Lake spillway"  # one-liner cause

window:
  spinup_days: 1         # default 1
  pre_event_days: 3      # default 3 (days before event in simulation)
  post_event_days: 3     # default 3 (days after event in simulation)
  # The derived timestamps are:
  #   tref   = date - pre_event_days - spinup_days
  #   tstart = date - pre_event_days
  #   tstop  = date + post_event_days

bbox:                    # required — HydroMT convention [W, S, E, N]
  west: 22.8
  south: 40.6
  east: 24.0
  north: 41.4
  era5_buffer_deg: 0.2   # default 0.2 — added to bbox for ERA5/GloFAS download

crs:
  epsg: 32634            # required — UTM zone for the model

grid:
  res: 150               # default 150 (m)
  rotated: false         # default false
  subgrid_pixels: 4      # default 4 (effective res = res/subgrid_pixels)
  manning_land: 0.04     # default 0.04
  manning_sea: 0.02      # default 0.02
  zmin: -2               # default -2
  zmax: 250              # default 250
  fill_area_km2: 20      # default 20
  drop_area_km2: 5       # default 5

paths:
  # required — where the model + data live
  work_dir: C:/Users/vaspapa/Desktop/ELKAK/implementation/emsr122_sfincs
  # required — where the deliverable folder lands
  deliverable_dir: C:/Users/vaspapa/Desktop/ELKAK/deliverable_strimonas_emsr122
  # optional — where to put the zip archives (defaults to ELKAK/)
  zip_dir: C:/Users/vaspapa/Desktop/ELKAK
  # optional — manning lookup CSV (defaults to the one bundled with the skill)
  manning_lookup: null
  # optional — where ERA5/GloFAS extracted files go
  era5_extracted_dir: null  # defaults to work_dir/data/era5_extracted
  glofas_extracted_dir: null

env:
  python: C:/Users/vaspapa/AppData/Local/miniforge3/envs/sfincs-viz/python.exe
  hydromt: C:/Users/vaspapa/AppData/Local/miniforge3/envs/sfincs-viz/Scripts/hydromt.exe
  sfincs_exe: C:/Users/vaspapa/Desktop/ELKAK/implementation/SFINCS_bin/SFINCS_v2.3.0_mt_Faber_release_exe/sfincs.exe
  gdal_data: C:/Users/vaspapa/AppData/Local/miniforge3/envs/sfincs-viz/Library/share/gdal
  gdalbuildvrt: C:/Users/vaspapa/AppData/Local/miniforge3/envs/sfincs-viz/Library/bin/gdalbuildvrt.exe
  cds_key_file: ~/.cdsapirc

ems:
  # required only if event.id is set
  # The skill expects URLs of the form:
  #   {base}/{event_id}/{event_id}_{aoi_slug}_{iteration}_vector.zip
  base_url: https://cems-mapping-website.s3.eu-west-1.amazonaws.com/static/activations
  aois:
    - 01STRYMONAS
    - 02BALTOTOPI
    - 03ACHINOS
    - 04MAVROTHALASSA
  iterations:
    - REFERENCE_OVERVIEW_v2
    - DELINEATION_OVERVIEW_v2
    - DELINEATION_OVERVIEW-MONIT01_v2
    - DELINEATION_OVERVIEW-MONIT01_v1
    - DELINEATION_OVERVIEW-MONIT02_v1
    - DELINEATION_OVERVIEW-MONIT02_v2
    - DELINEATION_OVERVIEW-MONIT03_v1
    # Not every AOI has every iteration; missing ones are silently skipped.

# Animation defaults
animation:
  canvas_width: 920      # default 920 (animation HTML / MP4 canvas in px)
  basemap_zoom: 12       # default 12 — Esri imagery zoom level
  basemap_buffer_m: 3000 # default 3000 — buffer around model bbox in metres
  mp4:
    fps: 12
    dpi: 110
    bitrate_kbps: 4000
  cities:                # optional list of {name, lat, lon} markers
    - {name: Serres, lat: 41.0853, lon: 23.5483}
    - {name: Sidirokastro, lat: 41.2347, lon: 23.3897}
    - {name: Nigrita, lat: 40.9036, lon: 23.4956}
    - {name: Amfipoli, lat: 40.8167, lon: 23.8500}
    - {name: Kerkini Lake, lat: 41.21, lon: 23.13}
    - {name: Thessaloniki, lat: 40.6401, lon: 22.9444}
  glofas_reach:          # optional sub-box for the GloFAS peak Q stat
    lat_min: 40.7
    lat_max: 41.3
    lon_min: 23.2
    lon_max: 23.8
```

## Derived values

The pipeline computes these at run time and surfaces them in the docs:

- `tref`, `tstart`, `tstop` — from `event.date` + `window.*`
- `era5_area` — `[north+buf, west-buf, south-buf, east+buf]` (CDS NWSE)
- `dem_tiles` — every 1° tile intersecting the bbox (e.g. `N40E022`)
- `worldcover_tiles` — every 3° tile (`N39E021`, `N39E024`, …)
- `effective_res` — `grid.res / grid.subgrid_pixels`

## Non-EMS events

If `event.id` is null, set `ems` to `{}` and skip `download_ems.py`. The
animation will still render — it will just have no observed-flood overlay,
no AOI rectangles, and no permanent-hydrography overlay. `qc_alignment.py`
emits a basemap-only QC figure in that case.
