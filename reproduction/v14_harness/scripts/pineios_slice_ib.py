"""CODE-12 A2 test — one-day Pineios slice (NO scoring): does the harness-v1.4 water-level boundary track
the inverse barometer -dp/(rho g) from the ERA5 MSLP forcing on a real published domain?

The as-run Pineios enhanced model (D:/ELKAK/implementation/pineios_sfincs_enhanced/model) is COPIED to a
scratch directory (the record is not touched); the v1.4 post-build step (build_model.waterlevel_bnd_points
+ write_waterlevel_bnd) adds sfincs.bnd / sfincs.bzs (0 m); sfincs.inp gets pavbnd = 101325, the one-day
window and 10-min map output; SFINCS runs; the modelled zs at every msk = 2 cell and output time is compared
with (pavbnd - p_atm)/(rhow g) using the model's own press_2d.nc sampled at the cell (nearest) and linearly
interpolated in time. Nothing is validated against EMS polygons.

Usage: python -I pineios_slice_ib.py --repo <worktree> --src D:/ELKAK/implementation/pineios_sfincs_enhanced/model
       --work <scratch dir> --day 2023-09-05 --out-json <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

RHOW, G, PREF = 1024.0, 9.81, 101325.0
COPY = ("sfincs.inp", "sfincs.ind", "sfincs.msk", "sfincs_subgrid.nc", "precip_2d.nc", "press_2d.nc", "wind_2d.nc",
        "sfincs.src", "sfincs.dis")


def _set_inp(txt: str, key: str, val: str) -> str:
    lines, done = [], False
    for ln in txt.splitlines():
        if ln.split("=")[0].strip() == key:
            lines.append(f"{key:<20} = {val}"); done = True
        else:
            lines.append(ln)
    if not done:
        lines.append(f"{key:<20} = {val}")
    return "\n".join(lines) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--day", default="2023-09-05")
    ap.add_argument("--out-json", required=True, type=Path)
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts"))
    import xarray as xr
    from _common import _load_machine_override
    import build_model
    from hydromt_sfincs import SfincsModel

    env = _load_machine_override()["env"]
    model = a.work / "model"
    if model.exists():
        shutil.rmtree(model)
    model.mkdir(parents=True)
    for f in COPY:
        if (a.src / f).exists():
            shutil.copy2(a.src / f, model / f)
    # v1.4 post-build step on the real mask
    mod = SfincsModel(root=str(model), mode="r")
    mod.read_config(); mod.read_grid()
    gdf = build_model.waterlevel_bnd_points(mod.mask, build_model.BND_SPACING_M)
    n_bnd = build_model.write_waterlevel_bnd(model, gdf, tref=mod.config["tref"], tstop=mod.config["tstop"])
    day = dt.datetime.fromisoformat(a.day)
    txt = (model / "sfincs.inp").read_text()
    txt = _set_inp(txt, "pavbnd", f"{PREF:.0f}")
    txt = _set_inp(txt, "tstart", day.strftime("%Y%m%d %H%M%S"))
    txt = _set_inp(txt, "tstop", (day + dt.timedelta(days=1)).strftime("%Y%m%d %H%M%S"))
    txt = _set_inp(txt, "dtout", "600")
    txt = _set_inp(txt, "dtmaxout", "86400")
    (model / "sfincs.inp").write_text(txt)
    t0 = time.time()
    run = subprocess.run([env["sfincs_exe"]], cwd=str(model), capture_output=True, text=True)
    wall = time.time() - t0
    (a.work / "sfincs_run.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    ds = xr.open_dataset(model / "sfincs_map.nc")
    msk = ds["msk"].values; zb = ds["zb"].values
    zs = ds["zs"].values                                   # (time, y, x)
    tmap = ds["time"].values
    # pressure at the msk=2 cells from the model's own netamp file (nearest cell), linear in time
    pr = xr.open_dataset(model / "press_2d.nc")
    pvar = [v for v in pr.data_vars if pr[v].ndim == 3][0]
    pda = pr[pvar]
    pt = pr["time"]
    rows, cols = np.where(msk == 2)
    xs, ys = ds["x"].values, ds["y"].values
    if xs.ndim == 2:
        cx, cy = xs[rows, cols], ys[rows, cols]
    else:
        cx, cy = xs[cols], ys[rows]
    px = pda.interp(time=tmap, method="linear").sel(x=xr.DataArray(cx, dims="pt"), y=xr.DataArray(cy, dims="pt"), method="nearest").values
    expected = (PREF - px) / (RHOW * G)                    # (time, pt)
    modelled = zs[:, rows, cols]
    valid = np.isfinite(modelled)
    diff = np.where(valid, modelled - expected, np.nan)
    rep = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source_model": str(a.src), "work": str(model),
           "slice": [day.isoformat(), (day + dt.timedelta(days=1)).isoformat()], "scoring": "none",
           "n_bnd_points": int(n_bnd), "msk2_cells": int(rows.size), "msk2_zb_min_max": [float(np.nanmin(zb[msk == 2])), float(np.nanmax(zb[msk == 2]))],
           "pavbnd_pa": PREF, "rhow": RHOW, "sfincs_wall_s": round(wall, 1), "n_output_times": int(tmap.size),
           "boundary_pressure_hpa_min_max": [float(np.nanmin(px)) / 100, float(np.nanmax(px)) / 100],
           "expected_ib_m_min_max": [float(np.nanmin(expected)), float(np.nanmax(expected))],
           "modelled_zs_min_max": [float(np.nanmin(modelled)), float(np.nanmax(modelled))],
           "boundary_wet_fraction": float(valid.mean()),
           "diff_mean_m": float(np.nanmean(diff)), "diff_rmse_m": float(np.sqrt(np.nanmean(diff ** 2))), "diff_max_abs_m": float(np.nanmax(np.abs(diff))),
           "corr_modelled_vs_expected": float(np.corrcoef(modelled[valid], expected[valid])[0, 1]),
           "series_hourly": [{"time": str(tmap[i])[:16], "expected_mean_m": round(float(np.nanmean(expected[i])), 4),
                              "modelled_mean_m": (None if not valid[i].any() else round(float(np.nanmean(modelled[i])), 4))}
                             for i in range(0, tmap.size, 6)],
           "sfincs_log_tail": run.stdout.splitlines()[-8:]}
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k not in ("series_hourly", "sfincs_log_tail")}, indent=1))
    for s in rep["series_hourly"]:
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
