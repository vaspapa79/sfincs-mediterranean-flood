"""Sample GloFAS v4 reanalysis at the named src points in
upstream_q.src_points and write data/q_outlet.csv (hourly columns per
point) + data/q_outlet_cells.json (the GloFAS cell behind every column),
used by build_model.inject_q_forcing.

Adapted from implementation/strymonas_forecast_v2/scripts/prep_q_at_outlet.py
— this version is the historical analogue (uses the event-window GloFAS
hindcast cached by download_glofas.py, not a same-season climatology
proxy). Interpolates daily GloFAS to hourly time steps with a step-fill.

Cell rule (unchanged since v1.0): for every named point the cell with the
largest time-mean discharge inside the +-WINDOW_HALF_DEG window — the river
cell nearest to the point. Harness v1.4.1 (D7, 2026-10-20): the window is
selected with coordinate masks, so the latitude order of the GloFAS file no
longer matters (the label slice `slice(lat + 0.1, lat - 0.1)` was empty on an
ascending axis — the Pineios file — and the script silently fell back to the
domain-mean discharge, a constant 11.589 m3/s at every source); a window
without a channel is now a hard error (NoChannelError), never a fallback.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from _common import load_config

WINDOW_HALF_DEG = 0.1
EDGE_TOL_DEG = 1e-4          # ~10 m: float32 coordinates (ulp 4e-6 deg at 40 deg, 1.5e-5 at 180 deg) put a centre exactly on the window edge inside


class NoChannelError(RuntimeError):
    """No GloFAS cell with positive discharge inside the search window of a named point (v1.4.1: hard error, no fallback)."""


def open_glofas(path: Path) -> xr.DataArray:
    ds = xr.open_dataset(path)
    if "valid_time" in ds.coords:
        ds = ds.rename({"valid_time": "time"})
    qvar = "discharge" if "discharge" in ds else ("dis24" if "dis24" in ds else list(ds.data_vars)[0])
    return ds[qvar]


def select_window_cell(da: xr.DataArray, lon: float, lat: float, half: float = WINDOW_HALF_DEG):
    """Series, (lon, lat) and window size of the max-mean-discharge cell within +-half deg of (lon, lat).

    Coordinate masks instead of label slices: identical to the historical selection on a descending latitude axis
    (inclusive bounds, same argmax order), and the same cells on an ascending one. Raises NoChannelError when the window
    holds no cell or no positive discharge.
    """
    la = np.asarray(da["latitude"].values, dtype=float)
    lo = np.asarray(da["longitude"].values, dtype=float)
    # inclusive window with a 1e-4 deg tolerance: GloFAS coordinates are float32 (39.81f = 39.81000137), and a cell centre
    # exactly half a window away from the point (0.1 deg grid, 2-decimal points) must be inside on every machine
    ii = np.where((la >= lat - half - EDGE_TOL_DEG) & (la <= lat + half + EDGE_TOL_DEG))[0]
    jj = np.where((lo >= lon - half - EDGE_TOL_DEG) & (lo <= lon + half + EDGE_TOL_DEG))[0]
    n = int(ii.size * jj.size)
    if n == 0:
        raise NoChannelError(f"no GloFAS cell within +-{half} deg of ({lat}, {lon}); file covers lat {la.min()}..{la.max()}, lon {lo.min()}..{lo.max()}")
    sub = da.isel(latitude=ii, longitude=jj)
    qmat = np.asarray(sub.mean("time").values, dtype=float)
    qmat = np.where(np.isfinite(qmat), qmat, 0.0)
    if qmat.max() <= 0:
        raise NoChannelError(f"no GloFAS channel (positive discharge) within +-{half} deg of ({lat}, {lon}): {n} cells, all <= 0")
    i, j = np.unravel_index(int(np.argmax(qmat)), qmat.shape)
    series = np.asarray(sub.isel(latitude=i, longitude=j).values, dtype=float)
    series = np.where(np.isfinite(series), series, 0.0)
    return series, (round(float(sub.longitude[j]), 3), round(float(sub.latitude[i]), 3)), n


def step_fill(times, series, tref, tstop):
    """Hourly steps tref..tstop, each taking the value of the GloFAS step nearest in time (the historical filling)."""
    hours = pd.date_range(tref, tstop, freq="h")
    gf_times = pd.to_datetime(times)
    col = np.zeros(len(hours), dtype=np.float64)
    for i, ts in enumerate(hours):
        k = int(np.argmin(np.abs(gf_times - ts)))
        col[i] = float(series[k])
    return hours, col


def sample_points(da: xr.DataArray, src_points, tref, tstop, half: float = WINDOW_HALF_DEG):
    """One hourly column per named point (hydromt convention: integer src IDs 1-based, in src_points order) + a report
    of the cell behind every column. Any point without a channel aborts the sampling (NoChannelError)."""
    lat = np.asarray(da["latitude"].values, dtype=float)
    rep = {"window_half_deg": half, "latitude_order": ("ascending" if lat[-1] > lat[0] else "descending"),
           "glofas_time": [str(da.time.values[0])[:19], str(da.time.values[-1])[:19]], "points": [], "duplicate_cells": []}
    hours = pd.date_range(tref, tstop, freq="h")
    df = pd.DataFrame(index=hours)
    cells: dict[tuple, list[str]] = {}
    for src_id, sp in enumerate(src_points, start=1):
        lon_t, lat_t = float(sp["lon"]), float(sp["lat"])
        half_p = float(sp.get("window_deg", half))        # optional per-point half-width (e.g. one cell next to a larger river)
        series, cell, n = select_window_cell(da, lon_t, lat_t, half_p)
        _, col = step_fill(da.time.values, series, tref, tstop)
        df[str(src_id)] = col
        rep["points"].append({"id": src_id, "name": sp["name"], "named_lonlat": [lon_t, lat_t], "window_half_deg": half_p, "cell_lonlat": list(cell), "window_cells": n,
                              "cell_mean_m3s": round(float(series.mean()), 3), "cell_peak_m3s": round(float(series.max()), 3),
                              "column_peak_m3s": round(float(col.max()), 3), "column_mean_m3s": round(float(col.mean()), 3)})
        cells.setdefault(cell, []).append(sp["name"])
    rep["duplicate_cells"] = [{"cell_lonlat": list(c), "points": names} for c, names in cells.items() if len(names) > 1]
    return df, rep


def write_outputs(data_dir: Path, df: pd.DataFrame, rep: dict):
    csv_out = data_dir / "q_outlet.csv"
    df.to_csv(csv_out, index_label="time")
    js_out = data_dir / "q_outlet_cells.json"
    js_out.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return csv_out, js_out


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

    da = open_glofas(gf)
    print(f"GloFAS var: {da.name}  dims: {dict(da.sizes)}")
    print(f"  time: {da.time.values[0]} .. {da.time.values[-1]} ({da.time.size} steps)")

    try:
        df, rep = sample_points(da, cfg.upstream_q["src_points"], cfg.tref, cfg.tstop)
    except NoChannelError as e:
        sys.exit(f"prep_q_at_outlets: {e} — refusing to write q_outlet.csv (harness v1.4.1, D7: no domain-mean fallback)")
    for p in rep["points"]:
        print(f"  {p['name']}: picked GloFAS cell at ({p['cell_lonlat'][1]:.3f}, {p['cell_lonlat'][0]:.3f}) "
              f"of {p['window_cells']} in the window  mean Q = {p['cell_mean_m3s']:.1f} m^3/s  peak {p['cell_peak_m3s']:.1f}")
    for d in rep["duplicate_cells"]:
        print(f"  WARN: points {d['points']} resolve to the same GloFAS cell {d['cell_lonlat']} — their discharge is injected twice")

    csv_out, js_out = write_outputs(data, df, rep)
    print(f"wrote: {csv_out}  ({csv_out.stat().st_size/1024:.0f} kB)  "
          f"hours={len(df)}  cols={list(df.columns)}; cells -> {js_out.name}")

    for col in df.columns:
        v = df[col].values
        print(f"  src#{col}: mean={v.mean():.1f}  median={np.median(v):.1f}  "
              f"min={v.min():.1f}  max={v.max():.1f}  m^3/s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
