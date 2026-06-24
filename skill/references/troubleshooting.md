# Troubleshooting

Failure modes that have actually happened in this project, and how to
recover.

## ERA5 returns a ZIP, not a single NetCDF

CDS started shipping `reanalysis-era5-single-levels` requests as ZIPs in
late 2024. The ZIP contains two NetCDFs (one for `stepType=accum`
covering `tp`, one for `stepType=instant` covering everything else).
`prep_inputs.py` handles both layouts:

1. If the ZIP path exists → unzip into `data/era5_extracted/`, merge the
   two NCs.
2. If only one `*.nc` exists in `era5_extracted/` → open it directly.

Don't change the request to ask for a single file — that endpoint
sometimes regresses.

## CDS hangs forever in "queued"

If the ERA5 request sits in `queued`/`running` for more than ~30
minutes, the issue is on CDS's side. Don't kill the request; the file
will arrive eventually. The cache file (`era5_*.zip`) will be 0 bytes
while it waits.

Workarounds:
- Restart the script — it will pick up the existing request ID if you
  saved one (we don't save request IDs in this skill, so a restart
  re-submits the request).
- If CDS is fully down, fall back to ERA5-Land (different dataset name,
  hourly, 0.1° resolution) — but the variable names differ; you'll need
  to adjust `prep_inputs.py`.

## GloFAS request comes back empty (size < 1 kB)

Causes:
- `area` was given as `[N, S, W, E]` instead of `[N, W, S, E]` (CDS
  convention). The GloFAS endpoint silently returns an empty file in
  this case.
- The requested year is outside the consolidated dataset window. As of
  2025, GloFAS v4 consolidated covers 1950 onwards but the boundary
  shifts; check the EWDS catalogue page.

## HydroMT warns "nodata value missing for ... copdem30.vrt"

Harmless. The Copernicus DEM Cogs use NaN-as-nodata via internal
metadata that the VRT wrapper drops. HydroMT proceeds with the implicit
nodata.

## SFINCS run finishes with `nan` in `zs`

The default `max(zs - zb)` returns `nan` because cells where the model
has not yet processed water carry `nan` in `zs`. Use:

```python
zs_f = np.where(np.isfinite(zs), zs, zb[None, :, :])
h = np.maximum(zs_f - zb[None, :, :], 0)
h[:, msk == 0] = 0
```

Don't reduce with `np.nanmax` on `h` directly — it still propagates
`nan` through the mask boundary cells.

## "BLAS not initialised" / numpy.dot returns zeros (Windows)

Hits whenever the user's conda env has `mkl=2026.*` from miniforge.
Pinned to `libopenblas`/`openblas` in `sfincs-viz` for this reason. If
the user updates the env and starts hitting this, point them at their
own memory: `feedback_windows_blas.md`.

## `ffmpeg ... does not contain an image sequence pattern`

FFmpeg's `image2` muxer wants `%03d.png` style filenames when writing
multiple frames. For a single still, pass `-vframes 1` AND `-update 1`,
or just route through `Pillow.Image.save()` after grabbing a frame with
`imageio.imread`. The MP4-check extractor in `make_mp4_check.py` uses
the `-vframes 1` form.

## ESA WorldCover tile boundary at integer longitude

Tiles are 3° × 3° aligned to lat=39, 42, 45 and lon=21, 24, 27. A bbox
that ends *exactly* at 24°E (like 22.8–24.0) brushes the N39E024 tile.
`download_worldcover.py` defensively grabs every tile whose west edge is
< bbox.east, even if bbox.east lands on the boundary. Always build a
VRT — even single-tile bboxes use the VRT path so the data catalog
entry stays stable.

## HydroMT build fails with "EPSG:0" or empty CRS

The `region.bbox` value in `sfincs_build.yml` must be a flat list of
floats in `[west, south, east, north]` order (lon/lat, EPSG:4326). The
`crs:` key is the target UTM. Don't pass UTM coordinates in `bbox` —
HydroMT will fail silently or build a 0-cell grid.

## `gdalbuildvrt` not found

Make sure the config's `env.gdalbuildvrt` points at the conda env's
`Library/bin/gdalbuildvrt.exe`. Calling `gdalbuildvrt` from PATH on
Windows often picks up an older OSGeo4W or QGIS binary that may not
match the GDAL version rasterio is linked against. Always use the env's
binary.

## MP4 way too big / way too small

Defaults: libx264, `bitrate=4000 kbps`, `fps=12`, 14-second event. That
should land in 1.5-2.5 MB. If you're outside that range:

- Larger: bitrate too high, OR `canvas_width` too high (the source array
  size drives the codec's bit needs).
- Smaller: probably the MP4 wrote a header but the encode failed — check
  the ffmpeg log printed by `make_mp4.py`.

## `sfincs.exe` exits with code 1 immediately

Most common cause: the model directory has stale `sfincs_map.nc` or
`sfincs.log` from a previous run that the new run can't overwrite. The
binary silently exits. Fix: clear those two files before invoking,
which `run_sfincs.py` does by default.
