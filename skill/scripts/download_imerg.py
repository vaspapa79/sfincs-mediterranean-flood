"""Pull GPM IMERG Final-Run half-hourly precipitation for the event window.

GPM IMERG (~0.1 deg, 30 min) resolves Mediterranean convective storms
that ERA5 (25 km, hourly) smears out. Needed for events where the actual
storm was sub-synoptic in scale — e.g. EMSR257 Mandra (Pateras Mt
convective burst, ~300 mm in 8 h that ERA5 reduces to ~5 mm/h peak).

Triggers only when `rain_source: imerg_half_hourly` in the event YAML.
Otherwise this script is a no-op (the pipeline falls back to ERA5).

Auth: NASA Earthdata login via ~/_netrc (machine urs.earthdata.nasa.gov).

Downloads the raw HDF5 granules to data/imerg_hdf5/ (cached; skips files
already present) then subsets to the event bbox and writes
data/imerg_<event_slug>.nc with a single variable `precip` in mm/h,
dims (time, latitude, longitude), CRS EPSG:4326.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import xarray as xr

from _common import load_config, ensure_dir


def main():
    cfg = load_config()
    rain_source = cfg.raw.get("rain_source", "era5_hourly")
    if rain_source != "imerg_half_hourly":
        print(f"rain_source={rain_source!r} (not imerg_half_hourly) — skipping IMERG")
        return 0

    out = cfg.paths["data_dir"] / f"imerg_{cfg.event_slug}.nc"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 1024:
        print(f"already present: {out} ({out.stat().st_size/1e6:.2f} MB)")
        return 0

    import earthaccess

    auth = earthaccess.login(strategy="netrc")
    if not auth.authenticated:
        sys.exit("Earthdata auth failed — check ~/_netrc machine "
                 "urs.earthdata.nasa.gov entry")
    print(f"Earthdata auth OK as {auth.username}")

    # Use a tight bbox + buffer to keep the request small.
    b = cfg.bbox
    buf = float(b.get("era5_buffer_deg", 0.2))
    bbox = (float(b["west"]) - buf, float(b["south"]) - buf,
            float(b["east"]) + buf, float(b["north"]) + buf)

    t0 = cfg.tref.isoformat()
    t1 = cfg.tstop.isoformat()
    print(f"IMERG search: {t0} -> {t1}  bbox={bbox}")

    results = earthaccess.search_data(
        short_name="GPM_3IMERGHH",
        version="07",
        temporal=(t0, t1),
        bounding_box=bbox,
    )
    print(f"found {len(results)} half-hourly granules")
    if not results:
        sys.exit("no IMERG granules found — check time range / bbox / Earthdata access")

    # Download to local HDF5 cache dir (skips already-present files).
    hdf5_dir = cfg.paths["data_dir"] / "imerg_hdf5"
    hdf5_dir.mkdir(parents=True, exist_ok=True)

    # Check which granules need downloading.
    to_download = []
    local_files = []
    for granule in results:
        # Filename is the last component of the data-link URL
        fname = granule.data_links()[0].split("/")[-1]
        local = hdf5_dir / fname
        if local.exists() and local.stat().st_size > 1024:
            local_files.append(local)
        else:
            to_download.append(granule)

    print(f"cached: {len(local_files)}/{len(results)}  to download: {len(to_download)}")
    if to_download:
        downloaded = earthaccess.download(to_download, str(hdf5_dir))
        # earthaccess.download returns list of local paths
        local_files += [Path(p) for p in downloaded]

    local_files = sorted(local_files)
    print(f"opening {len(local_files)} local HDF5 files from {hdf5_dir}")

    # Open from disk — much more reliable than fsspec streaming.
    ds = xr.open_mfdataset([str(f) for f in local_files], group="Grid",
                           combine="nested", concat_dim="time",
                           chunks={"time": 24}, parallel=False,
                           engine="h5netcdf")
    # Subset bbox
    ds = ds.sel(lon=slice(bbox[0], bbox[2]),
                lat=slice(bbox[1], bbox[3]))
    # Pick the calibrated precipitation variable
    pvar = None
    for cand in ("precipitation", "precipitationCal", "precip_cal"):
        if cand in ds.data_vars:
            pvar = cand
            break
    if pvar is None:
        sys.exit(f"no precipitation variable in IMERG dataset; vars={list(ds.data_vars)}")

    pr = ds[pvar].load()
    # IMERG dims: (time, lon, lat) — we want (time, latitude, longitude)
    if set(pr.dims) >= {"lon", "lat"}:
        pr = pr.transpose("time", "lat", "lon")
        pr = pr.rename({"lat": "latitude", "lon": "longitude"})
    pr.attrs["units"] = "mm/h"
    pr.attrs["long_name"] = "Precipitation (IMERG Final V07 calibrated)"
    pr = pr.where(pr >= 0, 0.0)

    out_ds = xr.Dataset({"precip": pr})
    out_ds.attrs["source"] = "GPM IMERG Final V07 half-hourly"
    out_ds.attrs["spatial_resolution"] = "0.1 deg"
    out_ds.attrs["temporal_resolution"] = "30 min"
    out_ds.to_netcdf(out, engine="h5netcdf")
    print(f"wrote: {out}  ({out.stat().st_size/1e6:.2f} MB)  "
          f"time steps: {pr.sizes['time']}  "
          f"basin-mean rain: {float(pr.mean()):.3f} mm/h  "
          f"peak rain: {float(pr.max()):.2f} mm/h")
    return 0


if __name__ == "__main__":
    sys.exit(main())
