"""Phase 3 (GO Phases 3-5, 2026-10-19) — MANIFEST row 14 / inventory 5a under harness v1.4: rebuild the Pineios discharge
forcing the way the published audit re-run did (CODE-8 `_glofas.py`): for every upstream_q source the GloFAS v4 series
of the cell NEAREST to the injection point (src_lon/src_lat, else lon/lat), interpolated linearly to the hourly SFINCS
steps, and the source re-snapped to the lowest-zb model cell within +-ncells cells of the injection point.

Why outside the pipeline: `prep_q_at_outlets.py` samples GloFAS with `sel(latitude=slice(lat+0.1, lat-0.1))`, which is
empty when the GloFAS file has an ascending latitude axis (the Pineios file does) and then falls back to the domain-mean
discharge (11.589 m3/s at every source and hour — the published canonical run and every pipeline Pineios run carry this
constant). Reported as a defect (no fix without the author's go); this script only reproduces the audit's post-build patch.

Usage: python -I rebuild_pineios_q.py --config <run yaml> --model <model dir> --out-json <...> [--ncells 10]
Writes sfincs.dis / sfincs.src (the pipeline files are kept as *.pipeline) and a JSON report; sfincs.inp is not touched.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import numpy as np


def nearest_series(da, lon: float, lat: float):
    """GloFAS series of the cell nearest to (lon, lat); independent of the latitude order of the file."""
    pt = da.sel(latitude=lat, longitude=lon, method="nearest")
    return np.asarray(pt.values, dtype=float), (float(pt.longitude), float(pt.latitude))


def hourly_linear(times, values, tref: dt.datetime, tstop: dt.datetime):
    """Linear interpolation of a (daily) series to the hourly steps tref..tstop; end values held outside the series."""
    import pandas as pd
    hours = pd.date_range(tref, tstop, freq="h")
    ts = pd.to_datetime(times)
    x = (ts - pd.Timestamp(tref)).total_seconds().values.astype(float)
    xh = (hours - pd.Timestamp(tref)).total_seconds().values.astype(float)
    return hours, np.interp(xh, x, np.asarray(values, dtype=float))


def snap_to_lowest_zb(x: float, y: float, dep: np.ndarray, transform, ncells: int = 10):
    """Centre of the lowest finite-zb cell within +-ncells (rows/cols) of the cell containing (x, y)."""
    from rasterio.transform import rowcol, xy
    r0, c0 = rowcol(transform, x, y)
    r0, c0 = int(r0), int(c0)
    rs, re = max(0, r0 - ncells), min(dep.shape[0], r0 + ncells + 1)
    cs, ce = max(0, c0 - ncells), min(dep.shape[1], c0 + ncells + 1)
    win = np.array(dep[rs:re, cs:ce], dtype=float)
    if not np.isfinite(win).any():
        raise ValueError("no finite zb in the search window")
    k = np.nanargmin(win)
    r, c = rs + k // win.shape[1], cs + k % win.shape[1]
    if np.isfinite(dep[r0, c0]) and dep[r0, c0] <= win.flat[k]:
        r, c = r0, c0                                      # nothing lower than the injection cell itself: do not move
    xs, ys = xy(transform, r, c)
    return float(xs), float(ys), float(dep[r, c]), (int(r), int(c))


def write_dis(path: Path, tref: dt.datetime, hours, cols) -> None:
    with open(path, "w") as f:
        for i, ts in enumerate(hours):
            t_sec = (ts.to_pydatetime() - tref).total_seconds()
            f.write(f"{t_sec:.0f}  " + "  ".join(f"{float(c[i]):.2f}" for c in cols) + "\n")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--ncells", type=int, default=10)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts"))
    from _common import load_config
    import pyproj
    import rasterio
    import xarray as xr
    cfg = load_config(["--config", str(a.config)])
    data = cfg.paths["data_dir"]
    gf = data / f"glofas_{cfg.event_slug}_clean.nc"
    ds = xr.open_dataset(gf)
    if "valid_time" in ds.coords:
        ds = ds.rename({"valid_time": "time"})
    var = "discharge" if "discharge" in ds else ("dis24" if "dis24" in ds else list(ds.data_vars)[0])
    da = ds[var]
    with rasterio.open(a.model / "gis" / "dep.tif") as src:
        dep = src.read(1).astype(float)
        if src.nodata is not None:
            dep[dep == src.nodata] = np.nan
        tr = src.transform
    to_utm = pyproj.Transformer.from_crs(4326, cfg.epsg, always_xy=True)
    pipeline_dis = np.loadtxt(a.model / "sfincs.dis") if (a.model / "sfincs.dis").exists() else None
    rep = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "glofas_file": str(gf), "glofas_var": var,
           "glofas_latitude_first_last": [float(da.latitude.values[0]), float(da.latitude.values[-1])],
           "glofas_time_first_last": [str(da.time.values[0])[:19], str(da.time.values[-1])[:19]], "ncells": a.ncells,
           "pipeline_dis_constant_value": (float(pipeline_dis[:, 1:].mean()) if pipeline_dis is not None and pipeline_dis[:, 1:].std() < 1e-9 else None),
           "sources": []}
    cols, src_lines = [], []
    hours = None
    for sp in cfg.upstream_q["src_points"]:
        lon, lat = float(sp.get("src_lon", sp["lon"])), float(sp.get("src_lat", sp["lat"]))
        series, cell = nearest_series(da, lon, lat)
        series = np.where(np.isfinite(series), series, 0.0)
        hours, hourly = hourly_linear(da.time.values, series, cfg.tref, cfg.tstop)
        cols.append(hourly)
        x0, y0 = to_utm.transform(lon, lat)
        xs, ys, zb, rc = snap_to_lowest_zb(x0, y0, dep, tr, a.ncells)
        src_lines.append((xs, ys))
        rep["sources"].append({"name": sp["name"], "injection_lonlat": [lon, lat], "glofas_cell_lonlat": list(cell),
                               "daily_peak_m3s": float(series.max()), "daily_mean_m3s": float(series.mean()),
                               "hourly_peak_m3s": float(hourly.max()), "injection_xy_pipeline": [round(x0, 2), round(y0, 2)],
                               "snapped_xy": [round(xs, 2), round(ys, 2)], "snapped_zb_m": round(zb, 2),
                               "shift_m": [round(xs - x0, 1), round(ys - y0, 1)]})
    for name in ("sfincs.dis", "sfincs.src"):
        p = a.model / name
        if p.exists() and not (a.model / f"{name}.pipeline").exists():
            shutil.copy2(p, a.model / f"{name}.pipeline")
    write_dis(a.model / "sfincs.dis", cfg.tref, hours, cols)
    with open(a.model / "sfincs.src", "w") as f:
        for xs, ys in src_lines:
            f.write(f"{xs:.2f}  {ys:.2f}\n")
    total = np.sum(cols, axis=0)
    rep["combined_hourly_peak_m3s"] = float(total.max()); rep["n_hours"] = int(len(hours))
    rep["sum_of_source_peaks_m3s"] = float(sum(c.max() for c in cols))
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
