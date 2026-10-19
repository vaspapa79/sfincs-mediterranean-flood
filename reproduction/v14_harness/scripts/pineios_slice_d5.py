"""GO-C / D5 test (ii) — the one-day Pineios boundary slice re-run with the meteo grids aligned (NO scoring).

Takes the CODE-12 slice model (copy of the as-run Pineios enhanced model with the v1.4 bnd/bzs, pavbnd = 101325,
one-day window, 10-min output; see pineios_slice_ib.py), copies it, aligns precip_2d/press_2d/wind_2d with
build_model.align_meteo_grid_file, runs SFINCS and compares the modelled boundary level with
(pavbnd - p)/(rhow g), p from the ORIGINAL (unaligned, cell-centre) press_2d.nc of the as-run model sampled at the
msk = 2 cell centres (bilinear and nearest), linear in time. The ~10 % shortfall of CODE-12 must vanish.

Usage: python -I pineios_slice_d5.py --repo <worktree> --src <slice model dir> --ref-model <as-run model dir>
       --work <scratch dir> --prev-json <pineios_slice_ib_result.json> --out-json <...>
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


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--ref-model", required=True, type=Path)
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--prev-json", type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts"))
    import pandas as pd
    import xarray as xr
    from _common import _load_machine_override
    import build_model

    env = _load_machine_override()["env"]
    model = a.work / "model"
    if model.exists():
        shutil.rmtree(model)
    model.mkdir(parents=True)
    for f in a.src.iterdir():
        if f.is_file() and f.name not in ("sfincs_map.nc", "sfincs.log", "sfincs_log.txt", "hydromt.log"):
            shutil.copy2(f, model / f.name)
    reps = [build_model.align_meteo_grid_file(model / f) for f in ("precip_2d.nc", "press_2d.nc", "wind_2d.nc")]
    t0 = time.time()
    run = subprocess.run([env["sfincs_exe"]], cwd=str(model), capture_output=True, text=True)
    wall = time.time() - t0
    (a.work / "sfincs_run.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    ds = xr.open_dataset(model / "sfincs_map.nc")
    msk = ds["msk"].values
    zs = ds["zs"].values
    tmap = pd.to_datetime(ds["time"].values)
    rows, cols = np.where(msk == 2)
    xs, ys = ds["x"].values, ds["y"].values
    cx, cy = (xs[rows, cols], ys[rows, cols]) if xs.ndim == 2 else (xs[cols], ys[rows])
    pr = xr.open_dataset(a.ref_model / "press_2d.nc")
    pvar = [v for v in pr.data_vars if pr[v].ndim == 3][0]
    pt = pr[pvar].interp(time=tmap.values, method="linear")
    mod = zs[:, rows, cols]
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "scoring": "none", "slice_model_src": str(a.src),
           "reference_press_2d": str(a.ref_model / "press_2d.nc"), "work": str(model), "alignment": reps,
           "n_msk2": int(rows.size), "n_output_times": int(tmap.size), "sfincs_wall_s": round(wall, 1),
           "boundary_wet_fraction": float(np.isfinite(mod).mean()), "modelled_zs_min_max": [float(np.nanmin(mod)), float(np.nanmax(mod))]}
    for sampling in ("bilinear", "nearest"):
        if sampling == "bilinear":
            px = pt.interp(x=xr.DataArray(cx, dims="pt"), y=xr.DataArray(cy, dims="pt"), method="linear").values
        else:
            px = pt.sel(x=xr.DataArray(cx, dims="pt"), y=xr.DataArray(cy, dims="pt"), method="nearest").values
        exp = (PREF - px) / (RHOW * G)
        v = np.isfinite(mod) & np.isfinite(exp)
        d = mod[v] - exp[v]
        A = np.vstack([exp[v], np.ones(v.sum())]).T
        coef, *_ = np.linalg.lstsq(A, mod[v], rcond=None)
        out[f"after_{sampling}"] = {"mean_diff_m": float(d.mean()), "rmse_m": float(np.sqrt((d ** 2).mean())), "max_abs_m": float(np.abs(d).max()),
                                    "corr": float(np.corrcoef(mod[v], exp[v])[0, 1]), "fit_slope": float(coef[0]), "fit_offset_m": float(coef[1]),
                                    "expected_ib_m_min_max": [float(np.nanmin(exp)), float(np.nanmax(exp))]}
    if a.prev_json and a.prev_json.exists():
        prev = json.loads(a.prev_json.read_text(encoding="utf-8"))
        out["before_nearest_CODE12"] = {k: prev[k] for k in ("utc", "diff_mean_m", "diff_rmse_m", "diff_max_abs_m", "corr_modelled_vs_expected", "modelled_zs_min_max", "expected_ib_m_min_max")}
    out["series_hourly"] = [{"time": str(tmap[i])[:16], "modelled_mean_m": (None if not np.isfinite(mod[i]).any() else round(float(np.nanmean(mod[i])), 4))}
                            for i in range(0, tmap.size, 6)]
    out["sfincs_log_tail"] = run.stdout.splitlines()[-6:]
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k not in ("series_hourly", "sfincs_log_tail", "alignment")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
