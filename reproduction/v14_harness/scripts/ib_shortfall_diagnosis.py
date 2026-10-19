"""CODE-13 — diagnosis of the ~10 % inverse-barometer shortfall seen in the one-day Pineios slice (report only).

Hypotheses tested on the kept slice outputs (no new run):
  H1 meteo timing: SFINCS holds/updates the pressure field at dtwnd intervals -> compare the modelled boundary
     level with the expectation computed from the pressure LAGGED by 0..60 min (nearest and bilinear sampling).
  H2 dry sea plane: the boundary feeds a dry 0-m plane -> the weakly reflective flux lowers the level. Volume
     balance of the plane (dV/dt minus rain) gives the inflow, converted to the level deficit
     (zsb - zs_i) = Q / (L sqrt(g h)) of the weakly reflective formulation.
  H3 amplitude/offset: least-squares fit modelled = a * expected + b.
Usage: python -I ib_shortfall_diagnosis.py --model <slice model dir> --out-json <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

RHOW, G, PREF = 1024.0, 9.81, 101325.0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    a = ap.parse_args()
    import pandas as pd
    import xarray as xr
    ds = xr.open_dataset(a.model / "sfincs_map.nc")
    msk = ds["msk"].values; zb = ds["zb"].values; zs = ds["zs"].values; tmap = pd.to_datetime(ds["time"].values)
    inp = ds["inp"].attrs; dx, dy = float(inp["dx"]), float(inp["dy"])
    rows, cols = np.where(msk == 2)
    xs, ys = ds["x"].values, ds["y"].values
    cx, cy = (xs[rows, cols], ys[rows, cols]) if xs.ndim == 2 else (xs[cols], ys[rows])
    pr = xr.open_dataset(a.model / "press_2d.nc"); pvar = [v for v in pr.data_vars if pr[v].ndim == 3][0]; pda = pr[pvar]
    mod = zs[:, rows, cols]
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "model": str(a.model), "n_msk2": int(rows.size),
           "n_times": int(tmap.size), "dtwnd_s": float(inp.get("dtwnd", np.nan)), "btfilter_s": float(inp.get("btfilter", np.nan)), "H1_lag": {}, "H3_fit": {}}
    for sampling in ("nearest", "bilinear"):
        for lag_min in (-30, -15, 0, 15, 30, 45, 60):
            tq = tmap - pd.Timedelta(minutes=lag_min)
            pt = pda.interp(time=tq.values, method="linear")
            if sampling == "nearest":
                px = pt.sel(x=xr.DataArray(cx, dims="pt"), y=xr.DataArray(cy, dims="pt"), method="nearest").values
            else:
                px = pt.interp(x=xr.DataArray(cx, dims="pt"), y=xr.DataArray(cy, dims="pt"), method="linear").values
            exp = (PREF - px) / (RHOW * G)
            v = np.isfinite(mod) & np.isfinite(exp)
            d = mod[v] - exp[v]
            out["H1_lag"][f"{sampling}_lag{lag_min}"] = {"mean_diff_m": round(float(d.mean()), 5), "rmse_m": round(float(np.sqrt((d ** 2).mean())), 5),
                                                          "max_abs_m": round(float(np.abs(d).max()), 5), "corr": round(float(np.corrcoef(mod[v], exp[v])[0, 1]), 5)}
            if lag_min == 0:
                A = np.vstack([exp[v], np.ones(v.sum())]).T
                coef, *_ = np.linalg.lstsq(A, mod[v], rcond=None)
                out["H3_fit"][sampling] = {"slope_a": round(float(coef[0]), 4), "offset_b_m": round(float(coef[1]), 5)}
    # H4: registration of the pressure grid inside SFINCS — expectation with the sampling point shifted by half a
    # netamp cell in x and/or y (bilinear, no lag)
    out["H4_half_cell_shift"] = {}
    pdx = float(abs(pda.x.values[1] - pda.x.values[0])); pdy = float(abs(pda.y.values[1] - pda.y.values[0]))
    pt0 = pda.interp(time=tmap.values, method="linear")
    for sx in (-0.5, 0.0, 0.5):
        for sy in (-0.5, 0.0, 0.5):
            px = pt0.interp(x=xr.DataArray(cx + sx * pdx, dims="pt"), y=xr.DataArray(cy + sy * pdy, dims="pt"), method="linear").values
            exp = (PREF - px) / (RHOW * G); v = np.isfinite(mod) & np.isfinite(exp); d = mod[v] - exp[v]
            out["H4_half_cell_shift"][f"dx{sx:+.1f}_dy{sy:+.1f}"] = {"mean_diff_m": round(float(d.mean()), 5), "rmse_m": round(float(np.sqrt((d ** 2).mean())), 5), "corr": round(float(np.corrcoef(mod[v], exp[v])[0, 1]), 5)}
    out["netamp_cell_m"] = [pdx, pdy]
    # H2: plane volume balance (msk=1 cells with zb <= 0 = the active GLO-30 sea plane)
    plane = (msk == 1) & (zb <= 0)
    h = np.where(np.isfinite(zs), np.maximum(zs - zb[None], 0.0), 0.0)
    V = (h[:, plane]).sum(axis=1) * dx * dy                                    # m3 per output time
    # rain on the plane (written precip_2d.nc, mm/h, block-left rates), integrated between output times
    rp = xr.open_dataset(a.model / "precip_2d.nc"); rvar = [v for v in rp.data_vars if rp[v].ndim == 3][0]; rda = rp[rvar]
    prow, pcol = np.where(plane)
    pxs, pys = (xs[prow, pcol], ys[prow, pcol]) if xs.ndim == 2 else (xs[pcol], ys[prow])
    rain_pt = rda.sel(x=xr.DataArray(pxs, dims="pt"), y=xr.DataArray(pys, dims="pt"), method="nearest")
    rt = pd.to_datetime(rda["time"].values)
    rain_vol = []
    for i in range(1, tmap.size):
        sel = (rt >= tmap[i - 1]) & (rt < tmap[i])
        if sel.any():
            step_h = (rt[1] - rt[0]).total_seconds() / 3600.0
            rain_vol.append(float((rain_pt.isel(time=np.where(sel)[0]).values.sum()) * step_h / 1000.0 * dx * dy))
        else:
            rain_vol.append(0.0)
    dVdt = np.diff(V) / np.diff(tmap.values).astype("timedelta64[s]").astype(float)   # m3/s
    Q_in = dVdt - np.array(rain_vol) / np.diff(tmap.values).astype("timedelta64[s]").astype(float)
    L = rows.size * dx
    hb = np.nanmean(np.where(np.isfinite(mod), mod - zb[rows, cols][None], np.nan), axis=1)   # boundary depth per time
    hb_mid = 0.5 * (hb[1:] + hb[:-1])
    deficit = Q_in / (L * np.sqrt(G * np.maximum(hb_mid, 1e-3)))
    out["H2_plane"] = {"plane_cells": int(plane.sum()), "plane_km2": round(float(plane.sum() * dx * dy / 1e6), 1), "boundary_length_km": round(L / 1000, 1),
                       "volume_Mm3_first_last": [round(V[0] / 1e6, 3), round(V[-1] / 1e6, 3)],
                       "rain_on_plane_Mm3_total": round(float(np.sum(rain_vol)) / 1e6, 3),
                       "net_inflow_m3s_mean": round(float(np.nanmean(Q_in)), 1), "net_inflow_m3s_max": round(float(np.nanmax(Q_in)), 1),
                       "boundary_depth_m_mean": round(float(np.nanmean(hb)), 4),
                       "predicted_deficit_m_mean": round(float(np.nanmean(deficit)), 5), "predicted_deficit_m_max": round(float(np.nanmax(deficit)), 5),
                       "hourly": [{"t": str(tmap[i + 1])[:16], "Q_in_m3s": round(float(Q_in[i]), 1), "deficit_m": round(float(deficit[i]), 5)} for i in range(0, len(Q_in), 6)]}
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("H1_lag", "H3_fit", "H4_half_cell_shift")}, indent=1, default=float))
    print(json.dumps({k: v for k, v in out["H2_plane"].items() if k != "hourly"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
