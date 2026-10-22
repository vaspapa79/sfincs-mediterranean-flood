"""CODE-19 A2 — the inverse-barometer boundary as realised: for the canonical enhanced run of each event, the maximum water level
reached at the water-level boundary cells (msk = 2) over the simulated window, read from sfincs_map.nc (zs, hourly output; the
boundary series the harness writes is bzs = 0 m, so the level at those cells is the IB term the solver adds), beside the expected
IB from the pressure forcing sampled at the same cells, (pavbnd - p) / (rho g), and the event-mean offset recorded in
reproduction/v14_harness/A2_pavbnd_reference.json. Zero compute: no SFINCS run, no scoring.

Usage (sfincs-viz env): python -I code19_a2_ib_boundary.py --repo <worktree>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import numpy as np

RUNS = [("pineios", "pineios_enhanced_v142"), ("mandra", "mandra_enhanced"), ("strymonas", "strymonas_enhanced_postD6_v142"),
        ("valencia", "valencia_enhanced_164_v142"), ("emilia", "emilia_enhanced_8aoi_v142"), ("crete", "crete_canonical_r2on")]
RHOW, G, PREF = 1024.0, 9.81, 101325.0     # A2_pavbnd_reference.json (rhow, g) and sfincs.inp pavbnd


def ib_m(p_pa, pref: float = PREF, rhow: float = RHOW, g: float = G):
    """Inverse-barometer rise (m) of a boundary at pressure p relative to the reference pavbnd: (pref - p) / (rho g)."""
    return (pref - np.asarray(p_pa, dtype=float)) / (rhow * g)


def nearest_index(axis, values):
    a = np.asarray(axis, dtype=float); order = np.argsort(a); s = a[order]
    v = np.asarray(values, dtype=float)
    j = np.clip(np.searchsorted(s, v), 1, len(s) - 1)
    pick = np.where(np.abs(v - s[j - 1]) <= np.abs(s[j] - v), j - 1, j)
    return order[pick]


def decode(var):
    import netCDF4
    d = netCDF4.num2date(var[:], var.units, only_use_cftime_datetimes=False, only_use_python_datetimes=True)
    return np.array([np.datetime64(x) for x in d], dtype="datetime64[s]")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    a = ap.parse_args()
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    import netCDF4
    from _common import load_config

    ref = json.loads((repo / "reproduction" / "v14_harness" / "A2_pavbnd_reference.json").read_text(encoding="utf-8"))
    assert ref["rhow"] == RHOW and ref["g"] == G and ref["pref_pa"] == PREF, (ref["rhow"], ref["g"], ref["pref_pa"])
    out_dir = repo / "reproduction" / "v14_rerun" / "code19"; out_dir.mkdir(parents=True, exist_ok=True)
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/code19_a2_ib_boundary.py",
           "definition": "realised = max over the simulated window and the msk = 2 cells of zs in sfincs_map.nc (hourly output; dry cells are fill); expected = max of "
                         "(pavbnd - p) / (rho g) with p = press_2d.nc sampled at the msk = 2 cells (nearest forcing node); rho 1024, g 9.81, pavbnd from sfincs.inp",
           "rhow": RHOW, "g": G, "events": []}
    for event, run in RUNS:
        cfg = load_config(["--config", str(repo / "reproduction" / "v14_rerun" / "configs" / f"{run}.yaml")])
        model = cfg.paths["model_dir"]
        inp = {k.strip(): v.strip() for k, v in (ln.split("=", 1) for ln in (model / "sfincs.inp").read_text(encoding="utf-8").splitlines() if "=" in ln)}
        pavbnd = float(inp.get("pavbnd", "nan"))
        n_bnd = sum(1 for ln in (model / "sfincs.bnd").read_text(encoding="utf-8").splitlines() if ln.strip()) if (model / "sfincs.bnd").exists() else 0
        bzs_vals = []
        if (model / "sfincs.bzs").exists():
            for ln in (model / "sfincs.bzs").read_text(encoding="utf-8").splitlines():
                parts = ln.split()
                if len(parts) > 1:
                    bzs_vals += [float(v) for v in parts[1:]]
        ds = netCDF4.Dataset(model / "sfincs_map.nc")
        msk = np.asarray(ds.variables["msk"][:]); x = np.asarray(ds.variables["x"][:]); y = np.asarray(ds.variables["y"][:])
        times = decode(ds.variables["time"])
        ii, jj = np.nonzero(msk == 2)
        tstart, tstop = np.datetime64(cfg.tstart, "s"), np.datetime64(cfg.tstop, "s")
        zs_max, t_max, c_max = -np.inf, None, None
        step_max, step_mean, wet_frac = [], [], []
        zsv = ds.variables["zs"]
        for k in range(len(times)):
            if times[k] < tstart or times[k] > tstop:
                continue
            slab = zsv[k]
            vals = np.ma.filled(np.ma.asarray(slab)[ii, jj].astype(float), np.nan)
            ok = np.isfinite(vals)
            wet_frac.append(float(ok.mean()))
            if ok.any():
                m = np.nanmax(vals); step_max.append(float(m)); step_mean.append(float(np.nanmean(vals)))
                if m > zs_max:
                    zs_max, t_max = float(m), str(times[k]); q = int(np.nanargmax(vals)); c_max = [float(x[ii[q], jj[q]]), float(y[ii[q], jj[q]])]
            else:
                step_max.append(float("nan")); step_mean.append(float("nan"))
        ds.close()
        pds = netCDF4.Dataset(model / "press_2d.nc")
        px, py = np.asarray(pds.variables["x"][:]), np.asarray(pds.variables["y"][:])
        pt = decode(pds.variables["time"])
        pvar = next(v for v in pds.variables if "press" in v.lower())
        P = np.asarray(pds.variables[pvar][:]).astype(float)
        pds.close()
        ix, iy = nearest_index(px, x[ii, jj]), nearest_index(py, y[ii, jj])
        sel = (pt >= tstart) & (pt <= tstop)
        pb = P[sel][:, iy, ix]
        ib = ib_m(pb, pref=pavbnd)
        q = np.unravel_index(np.nanargmax(ib), ib.shape)
        rec_ref = next((e for e in ref["events"] if cfg.event_id in e["label"]), None)
        ev = {"event": event, "run": run, "model_dir": str(model), "pavbnd_pa": pavbnd, "bnd_points": n_bnd, "bzs_values_all_zero": bool(bzs_vals) and all(v == 0.0 for v in bzs_vals),
              "msk2_cells": int(len(ii)), "output_steps_in_window": int(len(step_max)), "simulated": [str(tstart), str(tstop)],
              "realised_zs_max_m": None if not np.isfinite(zs_max) else round(zs_max, 4), "realised_zs_max_time": t_max, "realised_zs_max_cell_xy": c_max,
              "realised_time_mean_of_boundary_max_m": float(np.nanmean(step_max)) if step_max else None, "realised_max_of_boundary_mean_m": float(np.nanmax(step_mean)) if step_mean else None,
              "boundary_wet_fraction_mean": float(np.mean(wet_frac)) if wet_frac else None,
              "expected_ib_max_m": round(float(ib[q]), 4), "expected_ib_max_time": str(pt[sel][q[0]]), "expected_ib_min_m": round(float(np.nanmin(ib)), 4),
              "expected_ib_window_mean_m": round(float(np.nanmean(ib)), 4), "pressure_min_at_boundary_hpa": round(float(np.nanmin(pb)) / 100.0, 2),
              "reference_record": None if rec_ref is None else {k: rec_ref[k] for k in ("label", "mslp_mean_pa", "ib_offset_at_mean_m", "ib_at_domainmean_min_m", "mslp_domainmean_min_time")}}
        ev["realised_over_expected"] = round(ev["realised_zs_max_m"] / ev["expected_ib_max_m"], 3) if ev["realised_zs_max_m"] is not None and ev["expected_ib_max_m"] else None
        out["events"].append(ev)
        print(f"{event} ({run}): msk2 {ev['msk2_cells']} / bnd {n_bnd} / pavbnd {pavbnd:.0f}; realised zs max {ev['realised_zs_max_m']} m at {t_max}; expected IB max {ev['expected_ib_max_m']} m at "
              f"{ev['expected_ib_max_time']} (p min {ev['pressure_min_at_boundary_hpa']} hPa); window-mean expected IB {ev['expected_ib_window_mean_m']} m; "
              f"reference offset {None if rec_ref is None else rec_ref['ib_offset_at_mean_m']} m", flush=True)
    (out_dir / "a2_ib_boundary.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", out_dir / "a2_ib_boundary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
