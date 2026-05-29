# Environment setup

The pipeline assumes the user has the `sfincs-viz` conda env from the
ELKAK project. Default paths (all overridable via the YAML config's
`env:` block):

| Tool | Default path |
|---|---|
| Python | `C:/Users/vaspapa/AppData/Local/miniforge3/envs/sfincs-viz/python.exe` |
| HydroMT CLI | `C:/Users/vaspapa/AppData/Local/miniforge3/envs/sfincs-viz/Scripts/hydromt.exe` |
| SFINCS binary | `C:/Users/vaspapa/Desktop/ELKAK/implementation/SFINCS_bin/SFINCS_v2.3.0_mt_Faber_release_exe/sfincs.exe` |
| `gdalbuildvrt` | `C:/Users/vaspapa/AppData/Local/miniforge3/envs/sfincs-viz/Library/bin/gdalbuildvrt.exe` |
| GDAL_DATA | `C:/Users/vaspapa/AppData/Local/miniforge3/envs/sfincs-viz/Library/share/gdal` |
| CDS / EWDS key | `~/.cdsapirc` (used as-is for CDS; same `key:` field re-used for EWDS) |

## Python packages required in `sfincs-viz`

- `cdsapi` (CDS + EWDS clients)
- `hydromt`, `hydromt_sfincs`
- `xarray`, `netCDF4`, `numpy`, `pyproj`, `pyogrio`, `shapely`, `geopandas`, `rasterio`
- `matplotlib`, `Pillow`, `imageio_ffmpeg`
- `PyYAML`

If any of these are missing in the env the user gives you, **don't
`pip install`** — surface it to the user. Their env is pinned for a
reason (OpenBLAS pin to avoid mkl-2026 BLAS bug; see
`feedback_windows_blas.md` in their memory).

## CDS vs EWDS

| Endpoint | URL | Dataset |
|---|---|---|
| CDS | `https://cds.climate.copernicus.eu/api` | `reanalysis-era5-single-levels` (ERA5 hourly) |
| EWDS | `https://ewds.climate.copernicus.eu/api` | `cems-glofas-historical` (GloFAS v4 daily) |

Both accept the same API key from `~/.cdsapirc`. `download_era5.py` uses
the default CDS client. `download_glofas.py` reads the key from
`~/.cdsapirc` and instantiates `cdsapi.Client(url="...", key=key)`
explicitly pointing at EWDS.

## GDAL on Windows

Multiple pipeline scripts set `os.environ["GDAL_DATA"]` before importing
`rasterio` / `pyogrio` to silence the "Cannot find gdalvrt.xsd" warning.
If `GDAL_DATA` is missing, rasterio still works but emits noisy warnings
and `pyogrio` can fail to read shapefile CRS info on some systems.

The `_common.py` helper sets `GDAL_DATA` from the config.

## Disk space

A typical EMSR run drops:

| Path | Size |
|---|---|
| `data/copdem30/` | 200-300 MB (6 tiles) |
| `data/esa_worldcover/` | 100-150 MB (1-2 tiles) |
| `data/era5_*.nc` | < 1 MB |
| `data/glofas_*.nc` | < 1 MB |
| `data/ems_polygons/` | 50-100 MB |
| `data/basemap_satellite.png` | 5-7 MB |
| `data/tile_cache_esri_z12/` | 10-15 MB |
| `model/sfincs_subgrid.nc` | 60-130 MB |
| `model/sfincs_map.nc` | 50-120 MB |

Total: ~500 MB-1 GB per event. The skill never deletes existing files
without explicit user permission.
