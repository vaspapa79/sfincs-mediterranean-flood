"""Sample GloFAS v4 reanalysis at the named src points in
upstream_q.src_points and write data/q_outlet.csv (hourly columns per
point), used by build_model.inject_q_forcing.

Adapted from implementation/strymonas_forecast_v2/scripts/prep_q_at_outlet.py
— this version is the historical analogue (uses the event-window GloFAS
hindcast cached by download_glofas.py, not a same-season climatology
proxy). Interpolates daily GloFAS to hourly time steps with a step-fill.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from _common import load_config


def main():
    cfg = load_config()
    if not cfg.upstream_q["enabled"] or not cfg.upstream_q["src_points"]:
        print("upstream_q.enabled=false (or no src_points) — skipping Q at outlets")
        return 0

    data = cfg.paths["data_dir"]
    gf = data / f"glofas_{cfg.event_slug}_clean.nc"
    if not gf.exists():
        # Fall back to the raw download path
        gf = data / f"glofas_{cfg.event_slug}.nc"
    if not gf.exists():
        sys.exit(f"missing GloFAS hindcast at {gf} — run download_glofas.py + "
                 f"prep_inputs.py first")

    ds = xr.open_dataset(gf)
    if "valid_time" in ds.coords:
        ds = ds.rename({"valid_time": "time"})
    qvar = "discharge" if "discharge" in ds else (
        "dis24" if "dis24" in ds else list(ds.data_vars)[0]
    )
    print(f"GloFAS var: {qvar}  dims: {dict(ds.sizes)}")
    print(f"  time: {ds.time.values[0]} .. {ds.time.values[-1]} ({ds.time.size} steps)")

    samples = {}
    for sp in cfg.upstream_q["src_points"]:
        lat_t, lon_t = float(sp["lat"]), float(sp["lon"])
        sub = ds.sel(latitude=slice(lat_t + 0.1, lat_t - 0.1),
                     longitude=slice(lon_t - 0.1, lon_t + 0.1))
        qmat = sub[qvar].mean("time").values
        qmat = np.where(np.isfinite(qmat), qmat, 0.0)
        if qmat.size == 0 or qmat.max() <= 0:
            print(f"  WARN: no GloFAS channel found near ({lat_t}, {lon_t}); "
                  f"using global mean as fallback")
            q_series = np.full(ds.time.size, float(ds[qvar].mean()))
            picked = (lat_t, lon_t, float(q_series.mean()))
        else:
            i_up, j_up = np.unravel_index(int(np.argmax(qmat)), qmat.shape)
            q_series = sub[qvar].isel(latitude=i_up, longitude=j_up).values
            q_series = np.where(np.isfinite(q_series), q_series, 0.0)
            picked = (float(sub.latitude[i_up]), float(sub.longitude[j_up]),
                      float(q_series.mean()))
        print(f"  {sp['name']}: picked GloFAS cell at "
              f"({picked[0]:.3f}, {picked[1]:.3f})  mean Q = {picked[2]:.1f} m^3/s")
        samples[sp["name"]] = q_series

    gf_times = pd.to_datetime(ds.time.values)

    hours = pd.date_range(cfg.tref, cfg.tstop, freq="h")
    df = pd.DataFrame(index=hours)

    # hydromt convention: integer src IDs 1-based, in src_points order
    src_id = 1
    for name, q_series in samples.items():
        col = np.zeros(len(hours), dtype=np.float64)
        for i, ts in enumerate(hours):
            k = int(np.argmin(np.abs(gf_times - ts)))
            col[i] = float(q_series[k])
        df[str(src_id)] = col
        src_id += 1

    csv_out = data / "q_outlet.csv"
    df.to_csv(csv_out, index_label="time")
    print(f"wrote: {csv_out}  ({csv_out.stat().st_size/1024:.0f} kB)  "
          f"hours={len(df)}  cols={list(df.columns)}")

    for col in df.columns:
        v = df[col].values
        print(f"  src#{col}: mean={v.mean():.1f}  median={np.median(v):.1f}  "
              f"min={v.min():.1f}  max={v.max():.1f}  m^3/s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
