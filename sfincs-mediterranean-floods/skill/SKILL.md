---
name: sfincs-flood-reproduction
description: End-to-end SFINCS flood reproduction pipeline for rainfall-driven historical floods with Copernicus EMS validation. Triggers whenever the user mentions reproducing or simulating a flood event with SFINCS, an EMSR* activation (e.g. EMSR122 Strymonas, EMSR692 Storm Daniel / Pineios), or wants to set up "rain-on-grid" SFINCS for any region + date window + bbox. Also triggers for phrasings like "redo the flood pipeline for X", "build a SFINCS model for this flood", "validate SFINCS against Copernicus EMS observations", "generate the flood animation and deliverable", or "rerun with a different bbox/dates". Use it when the user supplies an EMS code OR a bbox + event date and expects the full chain (ERA5 + GloFAS + Copernicus DEM + ESA WorldCover + HydroMT-SFINCS build + SFINCS run + EMS validation + HTML + MP4 + deliverable folder + zip archives).
---

# SFINCS flood reproduction pipeline

This skill automates the full chain the user has been running for the
ELKAK project (Storm Daniel / Pineios and EMSR122 / Strymonas): pull
forcings + topography + land-use + EMS polygons, build the SFINCS model
with HydroMT, run the binary, produce a QC figure, an interactive HTML,
an MP4, and a self-contained deliverable folder + zip archives.

The pipeline is **rain-on-grid only** — there is no upstream Q boundary
in the default workflow. The animation is therefore a *terrain + low-lying-
area exposure* visualisation with the EMS polygons overlaid as ground
truth. If the event was actually driven by upstream discharge (e.g.
Strymonas, where Lake Kerkini was the main source), say so explicitly in
the results doc the skill writes.

## Inputs

The user gives you **one** of:

1. A YAML config file (preferred — reproducible, lives in
   `.claude/skills/sfincs-flood-reproduction/examples/` or alongside the
   model). Pass it through with `--config path/to/event.yaml`.
2. Free-text — EMS code, bbox, dates. Convert to a YAML config first
   (write it to `examples/<event>.yaml`), then invoke the scripts.

See `references/config_schema.md` for the full schema. Minimal example:

```yaml
event:
  id: EMSR122            # optional — null for non-EMS events
  name: Strymonas
  date: 2015-03-31
window:
  spinup_days: 1
  pre_event_days: 3
  post_event_days: 3
bbox: {west: 22.8, south: 40.6, east: 24.0, north: 41.4}
crs: {epsg: 32634}       # UTM zone the user wants
grid: {res: 150, subgrid_pixels: 4, manning_land: 0.04, manning_sea: 0.02}
paths:
  work_dir: C:/Users/vaspapa/Desktop/ELKAK/implementation/emsr122_sfincs
  deliverable_dir: C:/Users/vaspapa/Desktop/ELKAK/deliverable_strimonas_emsr122
```

## Workflow

Run scripts sequentially. Each script reads the same YAML config so you
can re-run individual steps without re-doing earlier ones — that matters
when ERA5 is slow or the SFINCS binary fails. All scripts live in
`scripts/`; invoke them with the user's `sfincs-viz` conda env Python:

```
$PY = C:/Users/vaspapa/AppData/Local/miniforge3/envs/sfincs-viz/python.exe
& $PY <skill>/scripts/<name>.py --config <event.yaml>
```

Replace `<skill>` with the absolute path to this skill directory.

### Step-by-step

1. **`download_ems.py`** — pulls EMS vector ZIPs for the activation,
   merges DELINEATION_MONIT crisis polygons into `EMSR<id>_observed_flood_all.gpkg`
   in the target UTM zone. Skip if `event.id` is null.
2. **`download_era5.py`** — CDS request for hourly precip + winds + MSLP
   over `bbox + 0.2° buffer`, full window `tref → tstop`. Caches to
   `data/era5_<event>.zip`.
3. **`download_glofas.py`** — EWDS request for daily Q over the same
   buffered bbox.
4. **`download_dem.py`** — fetches every Copernicus DEM 30 m 1° tile that
   intersects the bbox from the AWS Open Data bucket, builds
   `copdem30.vrt`.
5. **`download_worldcover.py`** — fetches every ESA WorldCover 10 m 3°
   tile that intersects the bbox, builds `esa_worldcover_2021.vrt`.
   Always wrap multiple tiles in a VRT — even bbox=24°E exactly straddles
   the N39E024 boundary.
6. **`prep_inputs.py`** — unzips/cleans ERA5 (rename to
   `precip/wind10_u/wind10_v/press_msl`, convert `tp` from m/h to mm/h),
   cleans GloFAS (`dis24 → discharge`), writes
   `data_catalog.yml` + a copy of `manning_lookup.csv`.
7. **`build_model.py`** — renders `sfincs_build.yml` from the template
   and invokes `hydromt build sfincs ./model -i sfincs_build.yml -d data_catalog.yml --fo -vv`.
8. **`run_sfincs.py`** — runs the SFINCS binary in `model/`, captures
   `sfincs_log.txt`.
9. **`fetch_basemap.py`** — fetches an Esri World Imagery z12 mosaic
   matched to the SFINCS UTM extent (with a 3 km buffer) and reprojects
   to EPSG = `crs.epsg`. Reads `model/sfincs_map.nc` to determine the
   exact UTM bbox, so it depends on step 8.
10. **`qc_alignment.py`** — overlays SFINCS `hmax`, EMS polygons, AOIs,
    hydrography, and the basemap into a static PNG.
11. **`make_animation.py`** — emits the self-contained HTML animation
    (~20 MB).
12. **`make_mp4.py`** — emits the libx264 MP4 with the side stats panel.
13. **`package_deliverable.py`** — copies MP4 + HTML + figures into the
    `deliverable_dir`, fills `README.md`, `methodology.md`, `results.md`
    from templates, builds `<EventID>_<Name>_SFINCS_deliverable.zip` and
    `<EventID>_<Name>_SFINCS_video_only.zip`.

For the common case ("run the whole pipeline"), use `run_pipeline.py`
which sequences all 13 steps with sensible defaults and resumable
caching.

### Re-running individual steps

If only the bbox changed but the event window didn't, delete the cached
ERA5/GloFAS netCDFs before re-running steps 2-3, then continue from
step 4. The download scripts skip if the cache file exists, so you
won't re-pay the CDS queue.

If only the visualisation changed, re-run steps 9-13 — they only depend
on `sfincs_map.nc` + EMS shapefiles + basemap.

## When to ask the user a question

Before running, confirm with the user when:

- **No EMS code is supplied but the user mentioned validation** — ask for
  the activation code, or whether they want to skip EMS overlays.
- **Bbox is ambiguous** — e.g. they said "the Strymonas region" without a
  number. Offer 1-2 candidate boxes and ask.
- **Their disk is tight** — a typical run drops 350-500 MB into
  `paths.work_dir/data/` and another 150-250 MB into `model/`. If they
  asked you to keep total footprint small, ask before downloading the
  basemap (~5 MB) and the WorldCover tiles (~55 MB each).
- **They asked for upstream Q forcing** — this skill does not add it;
  warn them and ask whether to proceed rain-on-grid or stop.

## Templates

Templates live in `templates/`. They are rendered with `string.Template`
(no external Jinja dep needed in the bundled env):

- `sfincs_build.yml.tmpl` — model setup for HydroMT-SFINCS
- `data_catalog.yml.tmpl` — data registry for HydroMT
- `README.md.tmpl` — top-level README in the deliverable folder
- `methodology.md.tmpl` — `4_docs/methodology.md`
- `results.md.tmpl` — `4_docs/results.md`

## Bundled assets

- `manning_lookup.csv` — ESA WorldCover class → Manning n (re-used across
  all events in this project; same values as `pineios_sfincs/manning_lookup.csv`)

## Reference docs (read on demand)

- `references/config_schema.md` — full YAML schema, defaults, examples.
- `references/ems_catalog.md` — Copernicus EMS S3 URL pattern, how to
  enumerate AOIs + monitoring iterations for a new activation, gotchas
  with the older (pre-2018) schema where REFERENCE-only products carry
  no observed-flood polygons.
- `references/environment_setup.md` — `sfincs-viz` conda env path,
  SFINCS binary location, CDS API key file, GDAL_DATA env var on
  Windows, OpenBLAS pinning to avoid the mkl-2026 BLAS bug.
- `references/troubleshooting.md` — common failure modes (ERA5 ZIP vs
  single-NC layout, CDS / EWDS endpoint distinction, GloFAS lat/lon vs
  ascending/descending order, HydroMT VRT nodata warning, SFINCS NaN in
  zs handling, ffmpeg single-image filename pattern, etc.)

## Things to NEVER do

- Don't run the SFINCS binary with `--no-verify` style flags — there
  aren't any, but resist the urge to wrap the run in a script that
  swallows non-zero exit codes. A SFINCS failure means *the model is
  broken*; surface it.
- Don't delete the CDS / EWDS cache files before checking with the user.
  ERA5 retrievals can sit in queue for hours and the user has explicit
  feedback about not destroying work in `~/.claude/memory/`.
- Don't write to the CDS API key file or modify `~/.cdsapirc`. Read it
  if the script needs the key (GloFAS via EWDS), never edit it.
- Don't try to `pip install` anything inside the `sfincs-viz` env —
  if a dep is missing, surface that to the user. Their conda env is
  pinned for a reason (see `feedback_windows_blas.md` in their memory).
