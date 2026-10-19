"""D6 on an event, from the INPUTS only (no run, no score): which active cells of a CN-on model cross Ia = 0.2 S during
the simulation and so become unbounded sinks under storecumprcp = 0, and when.

cumprcp per cell is reproduced the way SFINCS v2.3.0 builds it: the netampr file's first x/y is taken as the lower-left
corner (sfincs_ncinput.F90:606-610) and values are bilinear between cell centres at x(1) + dx/2 + (ix-1) dx,
y(1) + dy/2 + ... (sfincs_meteo.f90:1109-1110), rates are block-constant over each file interval (amprblock = 1), and
accumulation starts at tstart (sfincs_meteo.f90:1266). S per cell = sfincs.scs [inch] x 0.0254 (sfincs_domain.f90:2190).
Usage: python -I d6_sink_cells.py --model <dir> [--model <dir> ...] --labels a,b --window x0,x1,y0,y1 --out-json <...>
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


def cumprcp_series(model: Path, xc, yc, tstart, tstop):
    """Cumulative rain [m] at the cell centres (xc, yc) at each file time stamp within [tstart, tstop]."""
    import netCDF4
    import pandas as pd
    nc = netCDF4.Dataset(model / "precip_2d.nc")
    var = [v for v in nc.variables if nc[v].ndim == 3][0]
    px = nc["x"][:].astype(float); py = nc["y"][:].astype(float)
    t = pd.to_datetime(netCDF4.num2date(nc["time"][:], nc["time"].units, only_use_cftime_datetimes=False, only_use_python_datetimes=True))
    data = nc[var][:].filled(0.0).astype(float)
    nc.close()
    dx = px[1] - px[0]; dy = py[1] - py[0]
    # SFINCS placement: value (row j, col i) sits at (px[0] + dx/2 + i dx, py[0] + dy/2 + j dy)
    gx = px + dx / 2.0; gy = py + dy / 2.0
    order = np.argsort(gy)
    gy_s = gy[order]; data_s = data[:, order, :]
    fx = np.interp(xc, gx, np.arange(gx.size)); fy = np.interp(yc, gy_s, np.arange(gy_s.size))
    ix = np.clip(np.floor(fx).astype(int), 0, gx.size - 2); iy = np.clip(np.floor(fy).astype(int), 0, gy_s.size - 2)
    wx = fx - ix; wy = fy - iy
    def at(frame):
        return ((1 - wx) * (1 - wy) * frame[iy, ix] + wx * (1 - wy) * frame[iy, ix + 1]
                + (1 - wx) * wy * frame[iy + 1, ix] + wx * wy * frame[iy + 1, ix + 1])
    step_h = (t[1] - t[0]).total_seconds() / 3600.0
    cum = np.zeros(xc.size); times, cums = [], []
    for k in range(len(t)):
        t0, t1 = t[k], t[k] + pd.Timedelta(hours=step_h)
        lo, hi = max(t0, tstart), min(t1, tstop)
        if hi > lo:
            cum = cum + at(data_s[k]) * (hi - lo).total_seconds() / 3600.0 / 1000.0      # mm/h -> m
        if t1 >= tstart and t0 <= tstop:
            times.append(min(t1, tstop)); cums.append(cum.copy())
    return times, np.array(cums)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", required=True, type=Path)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--window", default="", help="x0,x1,y0,y1 [m] sub-region reported separately")
    ap.add_argument("--out-json", required=True, type=Path)
    a = ap.parse_args()
    import pandas as pd
    import xarray as xr
    from hydromt_sfincs import utils
    labels = a.labels.split(",")
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "rule": "sink cell = active cell with cumulative rain > 0.2 S (SFINCS 'cna', storecumprcp = 0)",
           "window_m": a.window, "models": {}}
    win = [float(v) for v in a.window.split(",")] if a.window else None
    for lab, model in zip(labels, a.model):
        d = inp_dict(model)
        tstart = pd.to_datetime(d["tstart"], format="%Y%m%d %H%M%S"); tstop = pd.to_datetime(d["tstop"], format="%Y%m%d %H%M%S")
        ds = xr.open_dataset(model / "sfincs_map.nc")
        msk = ds["msk"].values; x2 = ds["x"].values; y2 = ds["y"].values; zb = ds["zb"].values
        ind = utils.read_binary_map_index(model / "sfincs.ind")
        scs = utils.read_binary_map(model / "sfincs.scs", ind, msk.shape, mv=np.nan, dtype="f4")
        # sfincs.ind/scs are on the south-up grid like the map output (both written by hydromt/SFINCS, y ascending)
        act = msk > 0
        S = scs[act] * 0.0254; Ia = 0.2 * S
        times, cums = cumprcp_series(model, x2[act], y2[act], tstart, tstop)
        crossed = cums > Ia[None, :]
        first = np.full(Ia.size, np.nan)
        any_c = crossed.any(axis=0)
        first[any_c] = np.argmax(crossed[:, any_c], axis=0)
        cell_km2 = float(inp_dict(model)["dx"]) * float(inp_dict(model)["dy"]) / 1e6
        hrs = np.array([(tt - tstart).total_seconds() / 3600.0 for tt in times])
        rec = {"model": str(model), "tstart": str(tstart), "tstop": str(tstop), "active_cells": int(act.sum()), "S_mm_median": round(float(np.nanmedian(S) * 1000), 1),
               "cumprcp_end_mm_mean": round(float(np.nanmean(cums[-1]) * 1000), 1),
               "sink_cells_end": int(any_c.sum()), "sink_km2_end": round(float(any_c.sum() * cell_km2), 1), "sink_share_end": round(float(any_c.mean()), 4),
               "sink_km2_by_day": {f"day{k}": round(float(((cums[np.searchsorted(hrs, 24 * k) - 1] if 24 * k <= hrs[-1] else cums[-1]) > Ia).sum() * cell_km2), 1)
                                  for k in range(1, int(np.ceil(hrs[-1] / 24)) + 1)}}
        if win:
            xs, ys = x2[act], y2[act]
            sel = (xs >= win[0]) & (xs < win[1]) & (ys >= win[2]) & (ys < win[3])
            rec["window"] = {"active_cells": int(sel.sum()), "sink_cells_end": int((any_c & sel).sum()), "sink_share_end": round(float((any_c & sel).sum() / max(sel.sum(), 1)), 4),
                             "cumprcp_end_mm_mean": round(float(np.nanmean(cums[-1][sel]) * 1000), 1), "Ia_mm_median": round(float(np.nanmedian(Ia[sel]) * 1000), 1),
                             "first_crossing_hours_median": (None if not (any_c & sel).any() else round(float(np.median(hrs[first[any_c & sel].astype(int)])), 1))}
        out["models"][lab] = rec
        ds.close()
        print(lab, json.dumps(rec, indent=1))
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
