"""Gauge-based bias correction of IMERG for small-catchment convective events.

Background
----------
IMERG Final V07 at 0.1° resolution (~11 km) is too coarse to resolve
intense convective cells over small (<25 km²) catchments. For the
Mandra 2017 event, gauge data (Diakakis 2019) show 158--300 mm 24-h
totals over the Pateras Mt watershed, while IMERG records only
~30 mm domain-mean for the same period. The Nov 16-17 IMERG peak
corresponds to a different synoptic system.

Method
------
Apply a multiplicative scaling factor over the EVENT WINDOW only, so the
IMERG watershed-mean total matches the gauge-based 24-h target. The
Nov 16-17 period (different system, well-resolved by IMERG) is left
untouched. This is a "magnitude-preserving spatial pattern" correction;
references: Nikolopoulos et al. 2013, Anagnostou et al. 2009.

Usage
-----
    python bias_correct_imerg.py --config <config.yaml> \\
        --target-mm 200 \\
        --event-start "2017-11-14 00:00" \\
        --event-end "2017-11-15 23:30" \\
        --watershed-bbox 23.40,38.05,23.55,38.15
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import xarray as xr

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))
from _common import load_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--target-mm", type=float, default=200.0,
                    help="Gauge-based 24-h watershed catchment-mean target (mm)")
    ap.add_argument("--event-start", required=True,
                    help="Event window start (UTC), e.g. '2017-11-14 00:00'")
    ap.add_argument("--event-end", required=True,
                    help="Event window end (UTC), e.g. '2017-11-15 23:30'")
    ap.add_argument("--watershed-bbox", required=True,
                    help="Watershed bbox 'minlon,minlat,maxlon,maxlat'")
    args, _ = ap.parse_known_args()

    sys.argv = [sys.argv[0], "--config", str(args.config)]
    cfg = load_config()
    slug = cfg.event_slug
    imerg_path = cfg.paths["data_dir"] / f"imerg_{slug}.nc"
    if not imerg_path.exists():
        sys.exit(f"IMERG file missing: {imerg_path}")

    # If a backup exists, use it as input to keep correction idempotent
    backup = imerg_path.with_suffix(".raw.nc")
    src_path = backup if backup.exists() else imerg_path
    print(f"loading: {src_path}")
    # engine="h5netcdf" preloads h5py so subsequent writes don't fail with
    # "No module named h5py" (see project memory feedback_netcdf4_dll.md)
    ds = xr.open_dataset(src_path, engine="h5netcdf").load()
    ds.close()

    # Parse watershed bbox
    mn_lon, mn_lat, mx_lon, mx_lat = (float(x) for x in args.watershed_bbox.split(","))
    ws_mask = ((ds.longitude >= mn_lon) & (ds.longitude <= mx_lon)
               & (ds.latitude >= mn_lat) & (ds.latitude <= mx_lat))
    # xarray broadcasts to (longitude, latitude) ordering; transpose so the
    # numpy mask matches the (lat, lon) layout of precip[t, :, :].
    ws_mask = ws_mask.transpose("latitude", "longitude")
    n_ws = int(ws_mask.sum())
    if n_ws < 1:
        sys.exit(f"No IMERG cells in watershed bbox {args.watershed_bbox}")
    print(f"watershed cells: {n_ws}")

    # Parse event window
    ev_start = np.datetime64(args.event_start.replace(" ", "T"))
    ev_end = np.datetime64(args.event_end.replace(" ", "T"))

    # Find time mask for event window
    times = ds["time"].values
    # Convert to numpy datetime64 if needed
    if hasattr(times[0], "isoformat"):
        times_np = np.array([np.datetime64(t.isoformat()) for t in times])
    else:
        times_np = times.astype("datetime64[ns]")
    in_event = (times_np >= ev_start) & (times_np <= ev_end)
    n_ev = int(in_event.sum())
    print(f"event-window timesteps: {n_ev}  ({args.event_start} to {args.event_end})")

    # Time step in hours (assume 30 min for IMERG half-hourly)
    if len(times_np) > 1:
        dt_h = float((times_np[1] - times_np[0]) / np.timedelta64(1, "h"))
    else:
        dt_h = 0.5
    print(f"dt = {dt_h:.2f} h")

    # Current IMERG watershed-mean total over event window
    p = ds["precip"].values  # (time, lat, lon)
    # Average over watershed cells
    p_ws = np.where(ws_mask.values[None, :, :], p, np.nan)
    p_ws_mean = np.nanmean(p_ws, axis=(1, 2))  # time series (mm/h)
    current_total = float(np.nansum(p_ws_mean[in_event]) * dt_h)
    print(f"current IMERG watershed-mean total over event window: {current_total:.2f} mm")

    if current_total < 0.1:
        sys.exit("Current IMERG total too small; cannot compute scaling factor")

    # Scaling factor
    scale = args.target_mm / current_total
    print(f"target: {args.target_mm} mm  ->  scaling factor = {scale:.3f}x")

    # Apply scaling ONLY to event window timesteps (preserves Nov 16-17 IMERG)
    p_scaled = p.copy()
    p_scaled[in_event, :, :] = p_scaled[in_event, :, :] * scale

    # Verify
    p_ws_scaled = np.where(ws_mask.values[None, :, :], p_scaled, np.nan)
    p_ws_scaled_mean = np.nanmean(p_ws_scaled, axis=(1, 2))
    new_total = float(np.nansum(p_ws_scaled_mean[in_event]) * dt_h)
    print(f"after scaling: watershed-mean total over event window = {new_total:.2f} mm")
    print(f"max-cell peak before: {float(np.nanmax(p[in_event])):.2f} mm/h")
    print(f"max-cell peak after:  {float(np.nanmax(p_scaled[in_event])):.2f} mm/h")

    # Backup original (only if not already present)
    if not backup.exists():
        ds.to_netcdf(backup, engine="h5netcdf")
        print(f"backup written: {backup}")

    # Convert times to numpy datetime64 with proleptic_gregorian calendar
    # to prevent SFINCS from misinterpreting (cf. precip_2d.nc calendar=julian
    # caused 13-day offset, suppressing all rainfall in the simulation window).
    try:
        times_std = np.array([np.datetime64(t.isoformat()) for t in times_np]
                             if hasattr(times_np[0], "isoformat")
                             else times_np, dtype="datetime64[ns]")
    except Exception:
        times_std = times_np.astype("datetime64[ns]")

    # Write corrected
    ds_out = ds.copy()
    ds_out["precip"] = (("time", "latitude", "longitude"), p_scaled)
    ds_out = ds_out.assign_coords(time=times_std)
    ds_out["precip"].attrs["units"] = "mm/h"
    ds_out["precip"].attrs["long_name"] = "Gauge-bias-corrected IMERG precipitation"
    ds_out.attrs["bias_correction"] = (
        f"Multiplicative scaling {scale:.3f}x applied to event window "
        f"{args.event_start} to {args.event_end} so watershed bbox "
        f"({args.watershed_bbox}) 24-h total matches {args.target_mm} mm "
        f"gauge-based estimate"
    )
    ds_out.attrs["bias_correction_reference"] = (
        "Diakakis et al. 2019; Nikolopoulos et al. 2013; Anagnostou et al. 2009"
    )

    # Force standard calendar by setting encoding explicitly
    encoding = {"time": {"units": "minutes since 2017-01-01 00:00:00",
                          "calendar": "proleptic_gregorian",
                          "dtype": "float64"}}
    ds_out.to_netcdf(imerg_path, engine="h5netcdf", mode="w", encoding=encoding)
    print(f"wrote: {imerg_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
