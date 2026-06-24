"""Alternative GloFAS source: Open-Meteo Flood API (free, no auth).

Open-Meteo serves daily river discharge from GloFAS v4 directly via a
JSON HTTP API — same model, same product, just a different distribution
channel. We use it as a fallback when the EWDS / CDS queue for
``cems-glofas-historical`` is unreachable or stuck.

Writes ``data/glofas_<event_slug>.nc`` in the same coordinate layout as
the EWDS download (latitude × longitude × time, variable ``dis24``)
so that the downstream ``prep_q_at_outlets.py`` does not need
modification.

Trigger this script in place of ``download_glofas.py`` when CDS is
queue-stuck. The output NetCDF is bit-for-bit compatible from the
downstream pipeline's point of view — the only difference is the
distribution channel.

Usage:
    python download_glofas_openmeteo.py --config <event>.yaml
"""
from __future__ import annotations

import sys
import time
import urllib.request
import urllib.error
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from _common import load_config


OPEN_METEO_URL = "https://flood-api.open-meteo.com/v1/flood"


def _fetch_point(lat: float, lon: float, start: str, end: str,
                 retries: int = 3, pause: float = 0.5) -> tuple[list, list]:
    """Return (time_iso_list, q_m3s_list) for one grid point. Retries on transient HTTP errors."""
    qs = (f"?latitude={lat:.4f}&longitude={lon:.4f}"
          f"&daily=river_discharge&start_date={start}&end_date={end}")
    url = OPEN_METEO_URL + qs
    last_err = None
    for k in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                d = json.loads(r.read())
            daily = d.get("daily", {}) or {}
            return list(daily.get("time", [])), list(daily.get("river_discharge", []))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            last_err = e
            time.sleep(pause * (k + 1))
    raise RuntimeError(f"open-meteo failed after {retries} retries for "
                       f"({lat},{lon}): {last_err}")


def main():
    cfg = load_config()
    out = cfg.paths["data_dir"] / f"glofas_{cfg.event_slug}.nc"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 1024:
        print(f"already present: {out} ({out.stat().st_size/1e6:.1f} MB)")
        return 0

    # Build a 0.1deg regular grid over the bbox + buffer.
    b = cfg.bbox
    buf = float(b.get("era5_buffer_deg", 0.2))
    west, south = float(b["west"]) - buf, float(b["south"]) - buf
    east, north = float(b["east"]) + buf, float(b["north"]) + buf
    step = 0.1
    lons = np.round(np.arange(west, east + step / 2, step), 2)
    lats = np.round(np.arange(south, north + step / 2, step), 2)
    print(f"Open-Meteo Flood grid: {len(lons)} lons x {len(lats)} lats "
          f"= {len(lons)*len(lats)} points  range=({lons[0]:.2f}..{lons[-1]:.2f}, "
          f"{lats[0]:.2f}..{lats[-1]:.2f})")

    start = cfg.tref.date().isoformat()
    end = cfg.tstop.date().isoformat()
    print(f"time window: {start} -> {end}")

    # Probe one point to learn the time axis length
    sample_times, sample_q = _fetch_point(float(lats[0]), float(lons[0]), start, end)
    nt = len(sample_times)
    if nt == 0:
        sys.exit("Open-Meteo returned no time steps for the probe point.")
    print(f"days returned: {nt}  ({sample_times[0]} .. {sample_times[-1]})")

    # Allocate the discharge cube
    Q = np.full((nt, len(lats), len(lons)), np.nan, dtype=np.float32)

    n_total = len(lats) * len(lons)
    n_done = 0
    t0 = time.time()
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            ts, qs = _fetch_point(float(lat), float(lon), start, end)
            if len(qs) == nt:
                Q[:, i, j] = np.array([q if q is not None else np.nan for q in qs],
                                       dtype=np.float32)
            n_done += 1
            if n_done % 25 == 0 or n_done == n_total:
                elapsed = time.time() - t0
                rate = n_done / max(elapsed, 1e-6)
                eta = (n_total - n_done) / max(rate, 1e-6)
                print(f"  {n_done:4d}/{n_total}  rate={rate:5.1f} pt/s  "
                      f"ETA={eta:5.0f}s", flush=True)

    # Build the xarray dataset, matching the EWDS GloFAS shape
    # (time, latitude, longitude) with variable name 'dis24'.
    time_coord = pd.to_datetime(sample_times)
    ds = xr.Dataset(
        data_vars={
            "dis24": (("time", "latitude", "longitude"), Q,
                       {"units": "m3 s-1",
                        "long_name": "Mean river discharge in the last 24h",
                        "source": "Open-Meteo Flood API (GloFAS v4 reanalysis)"}),
        },
        coords={
            "time": ("time", time_coord),
            "latitude": ("latitude", lats.astype(np.float32),
                          {"units": "degrees_north", "standard_name": "latitude"}),
            "longitude": ("longitude", lons.astype(np.float32),
                          {"units": "degrees_east", "standard_name": "longitude"}),
        },
        attrs={
            "Conventions": "CF-1.8",
            "title": "GloFAS-v4 daily river discharge via Open-Meteo Flood API",
            "history": f"Downloaded by download_glofas_openmeteo.py for {cfg.event_label}",
            "source_distribution": "https://flood-api.open-meteo.com/v1/flood",
        },
    )
    # Write with h5netcdf because the sfincs-viz env has the netCDF4 DLL
    # issue when calling python.exe directly (see [[feedback-netcdf4-dll]]).
    ds.to_netcdf(out, engine="h5netcdf", mode="w")
    sz = out.stat().st_size / 1024
    finite = int(np.isfinite(Q).sum())
    print(f"wrote: {out} ({sz:.0f} kB)  finite cells: {finite}/{Q.size}  "
          f"peak Q (any cell, any day): {np.nanmax(Q):.1f} m3/s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
