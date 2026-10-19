"""Checkpoint 4b — water balance of a curve-number run with storecumprcp = 1 (harness v1.4 + D6). No scoring.

Terms over the simulated window (tstart -> tstop), all in Mm3:
  rain          = sum over active cells of cumprcp x cell area            (map output, written because of the flag)
  infiltration  = sum of cuminf x cell area
  discharge     = trapezoid of sfincs.dis over [tstart, tstop] (seconds since tref)
  storage(t)    = sum over msk = 1 cells of the sub-grid volume at zs(t) (sfincs_subgrid.nc z_zmin/z_zmax/z_volmax/z_level,
                  the inverse of SFINCS's own level-volume rule, sfincs_continuity.f90 ~540-560). The msk = 2 ring is
                  excluded: SFINCS prescribes its level (zs(nmb) = zsb, sfincs_boundaries.f90:1073); reported separately.
  boundary net  = rain - infiltration + discharge - (storage(end) - storage(start))  (positive = net outflow to the sea)
Sink check: per cell the SCS abstraction I(P) = P - Q(P) with P = cumprcp and S from sfincs.scs; a cell is a sink if
cuminf exceeds I(P) or P by more than 0.1 mm (expected: none).
Usage: python -I cn_water_balance.py --model <dir> --out-json <...> [--window x0,x1,y0,y1]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np


def inp_dict(model: Path) -> dict:
    d = {}
    for ln in (model / "sfincs.inp").read_text().splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def subgrid_volume(zs_np, sg) -> np.ndarray:
    """Volume per active cell [m3] for water levels zs_np (np,), inverse of SFINCS's level interpolation."""
    zmin, zmax, volmax = sg["z_zmin"], sg["z_zmax"], sg["z_volmax"]
    zl = sg["z_level"]                                   # (np, nlevels): level at volume k * volmax / (nlevels - 1)
    nlev = zl.shape[1]
    dz = volmax / (nlev - 1)
    v = np.zeros_like(zs_np, dtype=float)
    ok = np.isfinite(zs_np)
    full = ok & (zs_np >= zmax)
    v[full] = volmax[full] + (zs_np[full] - zmax[full]) * sg["area"][full]
    part = ok & ~full & (zs_np > zmin)
    if part.any():
        z = zs_np[part]; L = zl[part]; dzv = dz[part]
        k = np.clip((L <= z[:, None]).sum(axis=1) - 1, 0, nlev - 2)
        lo = L[np.arange(L.shape[0]), k]; hi = L[np.arange(L.shape[0]), k + 1]
        frac = np.where(hi > lo, (z - lo) / (hi - lo), 1.0)
        v[part] = (k + np.clip(frac, 0, 1)) * dzv
    return v


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--window", default="700000,748000,4515000,4550000", help="x0,x1,y0,y1 [m]: floodplain window reported separately")
    a = ap.parse_args()
    import pandas as pd
    import xarray as xr
    from hydromt_sfincs import utils
    d = inp_dict(a.model)
    tref = pd.to_datetime(d["tref"], format="%Y%m%d %H%M%S"); tstart = pd.to_datetime(d["tstart"], format="%Y%m%d %H%M%S")
    tstop = pd.to_datetime(d["tstop"], format="%Y%m%d %H%M%S")
    dx, dy = float(d["dx"]), float(d["dy"]); cell = dx * dy
    ds = xr.open_dataset(a.model / "sfincs_map.nc")
    msk = ds["msk"].values; nmax, mmax = msk.shape
    x2, y2 = ds["x"].values, ds["y"].values
    ind = utils.read_binary_map_index(a.model / "sfincs.ind")              # 0-based, column-major over (nmax, mmax)
    rows, cols = ind % nmax, ind // nmax
    sgd = xr.open_dataset(a.model / "sfincs_subgrid.nc")
    sg = {k: sgd[k].values.astype(float) for k in ("z_zmin", "z_zmax", "z_volmax")}
    sg["z_level"] = sgd["z_level"].values.astype(float)
    if sg["z_level"].shape[0] != ind.size:
        sg["z_level"] = sg["z_level"].T
    sg["area"] = np.full(ind.size, cell)
    sgd.close()
    zs = ds["zs"].values                                                     # (t, n, m)
    times = pd.to_datetime(ds["time"].values)
    interior = msk[rows, cols] == 1
    vols = [subgrid_volume(zs[i][rows, cols], sg) for i in range(len(times))]
    store = np.array([v[interior].sum() for v in vols]) / 1e6
    ring_store = np.array([v[~interior].sum() for v in vols]) / 1e6
    win = [float(v) for v in a.window.split(",")]
    inwin = (x2[rows, cols] >= win[0]) & (x2[rows, cols] < win[1]) & (y2[rows, cols] >= win[2]) & (y2[rows, cols] < win[3]) & interior
    vol_end = vols[-1]
    cumprcp = ds["cumprcp"].isel(timemax=-1).values[rows, cols]; cuminf = ds["cuminf"].isel(timemax=-1).values[rows, cols]
    scs = utils.read_binary_map(a.model / "sfincs.scs", ind, msk.shape, mv=np.nan, dtype="f4")
    S = scs[rows, cols].astype(float) * 0.0254                               # inch -> m, as sfincs_domain.f90:2192
    ia = 0.2 * S
    Iscs = np.where(cumprcp > ia, cumprcp - (cumprcp - ia) ** 2 / (cumprcp + 0.8 * S), cumprcp)
    excess = cuminf - np.minimum(Iscs, cumprcp)
    sink = excess > 1e-4
    dis = np.loadtxt(a.model / "sfincs.dis"); t = dis[:, 0]; q = dis[:, 1:].sum(axis=1)
    s0, s1 = (tstart - tref).total_seconds(), (tstop - tref).total_seconds()
    tt = np.unique(np.concatenate([[s0, s1], t[(t > s0) & (t < s1)]])); qq = np.interp(tt, t, q)
    Q = float(np.trapezoid(qq, tt)) / 1e6
    per_src = [float(np.trapezoid(np.interp(tt, t, dis[:, 1 + j]), tt)) / 1e6 for j in range(dis.shape[1] - 1)]
    rain = float(np.nansum(cumprcp) * cell) / 1e6; inf = float(np.nansum(cuminf) * cell) / 1e6
    hmax = (ds["zsmax"].max(dim="timemax").values - ds["zb"].values)
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "model": str(a.model),
           "window_utc": [str(tstart), str(tstop)], "storecumprcp": d.get("storecumprcp"), "active_cells": int(ind.size),
           "sink_check": {"cells_with_cuminf_above_scs_or_rain_by_0p1mm": int(sink.sum()), "share": float(sink.mean()),
                          "max_excess_mm": float(np.nanmax(excess) * 1000), "cells_past_Ia": int((cumprcp > ia).sum()),
                          "share_past_Ia": float((cumprcp > ia).mean())},
           "budget_Mm3": {"rain": round(rain, 2), "infiltration": round(inf, 2), "rain_runoff": round(rain - inf, 2),
                          "discharge_in": round(Q, 2), "discharge_per_source": [round(v, 2) for v in per_src],
                          "storage_start": round(float(store[0]), 2), "storage_end": round(float(store[-1]), 2),
                          "storage_max": round(float(store.max()), 2), "storage_max_time": str(times[int(store.argmax())]),
                          "boundary_net_outflow": round(rain - inf + Q - float(store[-1]) + float(store[0]), 2)},
           "storage_end_in_window_Mm3": round(float(vol_end[inwin].sum()) / 1e6, 2), "window_m": win,
           "ring_msk2_volume_Mm3_start_end": [round(float(ring_store[0]), 2), round(float(ring_store[-1]), 2)], "msk2_cells": int((~interior).sum()),
           "storage_daily_Mm3": {str(times[i])[:10]: round(float(store[i]), 1) for i in range(0, len(times), 24)},
           "rain_mm_mean": round(float(np.nanmean(cumprcp)) * 1000, 2), "infiltration_mm_mean": round(float(np.nanmean(cuminf)) * 1000, 2),
           "wet_h_gt_0p10_km2": round(float(np.nansum(np.where(np.isfinite(hmax), hmax, 0) > 0.10) * cell / 1e6), 1)}
    ds.close()
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
