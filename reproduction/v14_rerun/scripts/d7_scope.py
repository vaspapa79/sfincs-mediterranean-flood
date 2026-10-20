"""CODE-14 A (2026-10-20) — D7 scope check, no runs. For every R3-on run (the v1.4 pipeline runs and the published v1.3 model
directories they stand beside) list, per source point, what was written to sfincs.dis — min / max / mean of the column, and
whether it is the domain-mean constant fallback, the pipeline's window-max series or the audit's nearest-cell rebuild —
against the GloFAS series of (i) the cell nearest to the named point (lon/lat), (ii) the cell nearest to the injection
point (src_lon/src_lat) when it differs, and (iii) the max-mean-discharge cell of the +-0.1 deg window around the named
point (the sampler's documented design, evaluated order-agnostically). The source position is checked against the
lowest-zb model cell within +-10 cells (rule R: "snapped to the lowest-z_b channel cell"). Post-processing only.

Usage: python -I d7_scope.py --repo <worktree> [--out-dir reproduction/v14_rerun/code14]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import numpy as np

V14 = Path("D:/ELKAK/implementation/v14")
IMPL = Path("D:/ELKAK/implementation")
NHESS = Path("D:/ELKAK/ELKAK2/NHESS")
HALF = 0.1                       # the sampler's window half-width (deg)
NCELLS = 10                      # lowest-zb search window (model cells), as rebuild_pineios_q.py

V14_RUNS = ["pineios_enhanced", "pineios_r2_220", "pineios_r2_295", "pineios_r2_510", "pineios_cn_on", "pineios_raw_imerg",
            "pineios_timevarying_q", "pineios_qinf5",
            "strymonas_enhanced", "strymonas_enhanced_postD6", "strymonas_abl_cnoff_q", "strymonas_v1_prefix_src", "strymonas_leadin7d",
            "valencia_enhanced_164", "valencia_raw_imerg", "emilia_enhanced_8aoi"]


def published_rows(repo: Path) -> list[dict]:
    ex = repo / "skill" / "examples"
    cfgs = repo / "reproduction" / "v14_rerun" / "configs"
    pin = IMPL / "pineios_sfincs_enhanced"
    return [
        {"run": "PUB pineios_sfincs_enhanced", "note": "v1.3 canonical (MANIFEST row 5)", "config": ex / "emsr692_pineios_enhanced.yaml", "data": pin / "data", "model": pin / "model"},
        {"run": "PUB pineios_sfincs_v3", "note": "v1.3 time-varying-Q audit (row 14)", "config": ex / "emsr692_pineios_enhanced.yaml", "data": pin / "data", "model": IMPL / "pineios_sfincs_v3" / "model"},
        {"run": "PUB pineios_sfincs_v4", "note": "v1.3 qinf 5 (row 15)", "config": ex / "emsr692_pineios_enhanced.yaml", "data": pin / "data", "model": IMPL / "pineios_sfincs_v4" / "model"},
        {"run": "PUB bias_sweep/pineios", "note": "v1.3 R2 sweep 510 mm (row 12)", "config": ex / "emsr692_pineios_enhanced.yaml", "data": pin / "data", "model": Path("D:/ELKAK/reproduction/bias_sweep/pineios/model")},
        {"run": "PUB emsr122_sfincs_v3", "note": "v1.3 canonical Strymonas (row 1)", "config": ex / "emsr122_strymonas_enhanced.yaml", "data": IMPL / "emsr122_sfincs_v3" / "data", "model": IMPL / "emsr122_sfincs_v3" / "model"},
        {"run": "PUB emsr122_sfincs_enhanced", "note": "v1.3 Strymonas v1, pre-fix src (row 13)", "config": cfgs / "strymonas_v1_prefix_src.yaml", "data": IMPL / "emsr122_sfincs_enhanced" / "data", "model": IMPL / "emsr122_sfincs_enhanced" / "model"},
        {"run": "PUB emsr122_sfincs_v4", "note": "v1.3 Table 12 CN off + Q (row 9)", "config": ex / "emsr122_strymonas_enhanced.yaml", "data": IMPL / "emsr122_sfincs_v3" / "data", "model": IMPL / "emsr122_sfincs_v4" / "model"},
        {"run": "PUB NHESS valencia rerun_v164", "note": "v1.3 Valencia 164 mm (row 8)", "config": ex / "emsr773_valencia_enhanced.yaml", "data": NHESS / "runs" / "valencia_emsr773" / "data",
         "model": NHESS / "R1_verification" / "task_valencia_anchor" / "rerun_v164" / "model"},
        {"run": "PUB NHESS emilia_emsr664", "note": "v1.3 Emilia (row 7)", "config": ex / "emsr664_emilia_romagna_enhanced.yaml", "data": NHESS / "runs" / "emilia_emsr664" / "data", "model": NHESS / "runs" / "emilia_emsr664" / "model"},
    ]


def open_glofas(data: Path, slug: str):
    import xarray as xr
    gf = data / f"glofas_{slug}_clean.nc"
    if not gf.exists():
        gf = data / f"glofas_{slug}.nc"
    ds = xr.open_dataset(gf)
    if "valid_time" in ds.coords:
        ds = ds.rename({"valid_time": "time"})
    var = "discharge" if "discharge" in ds else ("dis24" if "dis24" in ds else list(ds.data_vars)[0])
    return gf, ds[var]


def nearest(da, lon: float, lat: float):
    pt = da.sel(latitude=lat, longitude=lon, method="nearest")
    return np.nan_to_num(np.asarray(pt.values, dtype=float)), (round(float(pt.longitude), 3), round(float(pt.latitude), 3))


def literal_slice_size(da, lon: float, lat: float) -> int:
    """The sampler's own selection, as written: empty on an ascending latitude axis."""
    sub = da.sel(latitude=slice(lat + HALF, lat - HALF), longitude=slice(lon - HALF, lon + HALF))
    return int(sub.sizes["latitude"] * sub.sizes["longitude"])


def window_max(da, lon: float, lat: float):
    """Max-mean-discharge cell of the +-HALF deg window, independent of the coordinate order."""
    la, lo = da["latitude"], da["longitude"]
    sub = da.where((la >= lat - HALF) & (la <= lat + HALF) & (lo >= lon - HALF) & (lo <= lon + HALF), drop=True)
    if sub.size == 0:
        return None
    qmat = np.nan_to_num(sub.mean("time").values)
    if qmat.size == 0 or qmat.max() <= 0:
        return None
    i, j = np.unravel_index(int(np.argmax(qmat)), qmat.shape)
    ser = np.nan_to_num(np.asarray(sub.isel(latitude=i, longitude=j).values, dtype=float))
    return ser, (round(float(sub.latitude[i]), 3), round(float(sub.longitude[j]), 3))[::-1], int(qmat.size)


def step_fill(times, series, tref, tstop):
    """The sampler's hourly filling: value of the GloFAS step nearest in time."""
    import pandas as pd
    hours = pd.date_range(tref, tstop, freq="h")
    gt = pd.to_datetime(times)
    return np.array([float(series[int(np.argmin(np.abs(gt - h)))]) for h in hours])


def hourly_linear(times, series, tref, tstop):
    import pandas as pd
    hours = pd.date_range(tref, tstop, freq="h")
    ts = pd.to_datetime(times)
    x = (ts - pd.Timestamp(tref)).total_seconds().values.astype(float)
    xh = (hours - pd.Timestamp(tref)).total_seconds().values.astype(float)
    return np.interp(xh, x, np.asarray(series, dtype=float))


def lowest_zb(dep, transform, x, y, ncells=NCELLS):
    from rasterio.transform import rowcol
    r0, c0 = (int(v) for v in rowcol(transform, x, y))
    if not (0 <= r0 < dep.shape[0] and 0 <= c0 < dep.shape[1]):
        return None
    rs, re = max(0, r0 - ncells), min(dep.shape[0], r0 + ncells + 1)
    cs, ce = max(0, c0 - ncells), min(dep.shape[1], c0 + ncells + 1)
    win = dep[rs:re, cs:ce]
    if not np.isfinite(win).any():
        return None
    k = int(np.nanargmin(win)); r, c = rs + k // win.shape[1], cs + k % win.shape[1]
    z0 = float(dep[r0, c0]) if np.isfinite(dep[r0, c0]) else None
    return {"src_zb_m": z0, "lowest_zb_m": round(float(win.flat[k]), 2), "lowest_offset_cells": [int(r - r0), int(c - c0)],
            "on_lowest": bool(z0 is not None and z0 <= float(win.flat[k]) + 1e-6)}


def classify(written, cand: dict, domain_mean: float) -> str:
    if written.std() < 1e-9:
        return "FALLBACK constant" + (f" = domain mean {domain_mean:.3f}" if abs(written[0] - domain_mean) < 0.01 else f" {written[0]:.3f} (not the domain mean)")
    for name, ser in cand.items():
        if ser is not None and len(ser) == len(written) and np.max(np.abs(ser - written)) <= 0.0051:
            return name
    return "OTHER series (matches no candidate)"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out-dir", type=Path, default=None)
    a = ap.parse_args()
    repo = a.repo.resolve()
    out_dir = a.out_dir or (repo / "reproduction" / "v14_rerun" / "code14")
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    os.environ.setdefault("GDAL_DATA", os.path.join(sys.prefix, "Library", "share", "gdal"))
    from _common import load_config
    import pyproj
    import rasterio
    rows = [{"run": r, "note": "v1.4 pipeline run", "config": repo / "reproduction" / "v14_rerun" / "configs" / f"{r}.yaml", "data": V14 / r / "data", "model": V14 / r / "model"} for r in V14_RUNS]
    rows += published_rows(repo)
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "window_half_deg": HALF, "lowest_zb_window_cells": NCELLS, "runs": []}
    md = ["| run | point | written min / max / mean (m³/s) | what was written | nearest cell @ named point: peak in window (cell) | nearest @ injection point: peak (cell) | window-max cell: peak (cell, n cells) | src on lowest z_b?; msk at src |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        cfg = load_config(["--config", str(r["config"])])
        if not cfg.upstream_q.get("enabled") or not cfg.upstream_q.get("src_points"):
            continue
        gf, da = open_glofas(r["data"], cfg.event_slug)
        lat = da["latitude"].values
        dom_mean = float(np.nan_to_num(da.values).mean()) if np.isfinite(da.values).all() else float(da.mean())
        dis = np.loadtxt(r["model"] / "sfincs.dis"); dis = dis[None, :] if dis.ndim == 1 else dis
        src = np.loadtxt(r["model"] / "sfincs.src"); src = src[None, :] if src.ndim == 1 else src
        pipe_dis = (r["model"] / "sfincs.dis.pipeline")
        pipe = None
        if pipe_dis.exists():
            pipe = np.loadtxt(pipe_dis); pipe = pipe[None, :] if pipe.ndim == 1 else pipe
        dep = tr = msk = None
        mtif = r["model"] / "gis" / "msk.tif"
        if mtif.exists():
            with rasterio.open(mtif) as s_:
                msk = s_.read(1)
        dtif = r["model"] / "gis" / "dep.tif"
        if dtif.exists():
            with rasterio.open(dtif) as s:
                dep = s.read(1).astype(float)
                if s.nodata is not None:
                    dep[dep == s.nodata] = np.nan
                tr = s.transform
        to_utm = pyproj.Transformer.from_crs(4326, cfg.epsg, always_xy=True)
        rec = {"run": r["run"], "note": r["note"], "config": str(r["config"]), "model": str(r["model"]), "glofas_file": str(gf),
               "glofas_latitude_order": "ascending" if lat[-1] > lat[0] else "descending", "glofas_domain_mean_m3s": round(dom_mean, 3),
               "glofas_time": [str(da.time.values[0])[:10], str(da.time.values[-1])[:10]], "n_dis_rows": int(dis.shape[0]), "n_dis_cols": int(dis.shape[1] - 1),
               "pipeline_dis_kept_as": (str(pipe_dis) if pipe is not None else None), "points": []}
        for i, sp in enumerate(cfg.upstream_q["src_points"]):
            lon, la_ = float(sp["lon"]), float(sp["lat"])
            ilon, ilat = float(sp.get("src_lon", lon)), float(sp.get("src_lat", la_))
            w = dis[:, i + 1]
            n_ser, n_cell = nearest(da, lon, la_)
            cand = {"window-max series, step-filled (the sampler, order-agnostic)": None, "nearest cell @ named point, step-filled": step_fill(da.time.values, n_ser, cfg.tref, cfg.tstop),
                    "nearest cell @ named point, hourly linear": hourly_linear(da.time.values, n_ser, cfg.tref, cfg.tstop)}
            wm = window_max(da, lon, la_)
            if wm is not None:
                cand["window-max series, step-filled (the sampler, order-agnostic)"] = step_fill(da.time.values, wm[0], cfg.tref, cfg.tstop)
            inj = None
            if (ilon, ilat) != (lon, la_):
                i_ser, i_cell = nearest(da, ilon, ilat)
                inj = {"cell": i_cell, "daily_peak_m3s": round(float(i_ser.max()), 2), "daily_mean_m3s": round(float(i_ser.mean()), 2)}
                cand["nearest cell @ injection point, hourly linear (audit rebuild)"] = hourly_linear(da.time.values, i_ser, cfg.tref, cfg.tstop)
                cand["nearest cell @ injection point, step-filled"] = step_fill(da.time.values, i_ser, cfg.tref, cfg.tstop)
            cls = classify(w, cand, dom_mean)
            win_peak = {k: (None if v is None else round(float(np.max(v)), 2)) for k, v in cand.items()}
            p = {"name": sp["name"], "candidate_peaks_in_simulated_window_m3s": win_peak, "named_lonlat": [lon, la_], "injection_lonlat": [ilon, ilat],
                 "written": {"min": round(float(w.min()), 2), "max": round(float(w.max()), 2), "mean": round(float(w.mean()), 3), "constant": bool(w.std() < 1e-9)},
                 "written_is": cls, "literal_slice_cells": literal_slice_size(da, lon, la_),
                 "nearest_named": {"cell": n_cell, "daily_peak_m3s": round(float(n_ser.max()), 2), "daily_mean_m3s": round(float(n_ser.mean()), 2)},
                 "nearest_injection": inj,
                 "window_max": (None if wm is None else {"cell": wm[1], "n_cells": wm[2], "daily_peak_m3s": round(float(wm[0].max()), 2), "daily_mean_m3s": round(float(wm[0].mean()), 2)})}
            if pipe is not None and pipe.shape == dis.shape:
                pw = pipe[:, i + 1]
                p["pipeline_file_written"] = {"min": round(float(pw.min()), 2), "max": round(float(pw.max()), 2), "mean": round(float(pw.mean()), 3), "constant": bool(pw.std() < 1e-9)}
            x0, y0 = to_utm.transform(ilon, ilat)
            sx, sy = float(src[i, 0]), float(src[i, 1])
            p["src_xy"] = [round(sx, 2), round(sy, 2)]; p["src_equals_injection_point"] = bool(abs(sx - x0) < 0.6 and abs(sy - y0) < 0.6)
            p["src_shift_from_injection_m"] = [round(sx - x0, 1), round(sy - y0, 1)]
            if dep is not None:
                p["src_vs_lowest_zb"] = lowest_zb(dep, tr, sx, sy)
            if msk is not None:
                from rasterio.transform import rowcol
                rr, cc = (int(v) for v in rowcol(tr, sx, sy))
                mv = msk[rr, cc] if (0 <= rr < msk.shape[0] and 0 <= cc < msk.shape[1]) else np.nan
                p["msk_at_src"] = None if not np.isfinite(mv) else int(mv)
            rec["points"].append(p)
            lz = p.get("src_vs_lowest_zb")
            lz_s = ("n/a" if lz is None else ("yes" if lz["on_lowest"] else f"no (src {lz['src_zb_m']} m, lowest {lz['lowest_zb_m']} m at {lz['lowest_offset_cells']})"))
            nk = win_peak["nearest cell @ named point, step-filled"]; ik = win_peak.get("nearest cell @ injection point, step-filled"); wk = win_peak["window-max series, step-filled (the sampler, order-agnostic)"]
            md.append(f"| {r['run']} | {sp['name']} | {w.min():.2f} / {w.max():.2f} / {w.mean():.2f} | {cls} | {nk} {n_cell} | "
                      f"{'same point' if inj is None else str(ik) + ' ' + str(inj['cell'])} | "
                      f"{'EMPTY window' if wm is None else f'{wk} {wm[1]} n={wm[2]}'} | {lz_s}; msk {p.get('msk_at_src')} |")
        out["runs"].append(rec)
        print(f"{r['run']}: {rec['glofas_latitude_order']} latitude, domain mean {dom_mean:.3f}; " + "; ".join(f"{p['name']}: {p['written_is']}" for p in rec["points"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "d7_scope.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    head = [f"# D7 scope check (CODE-14 A) — generated {out['utc']} by `reproduction/v14_rerun/scripts/d7_scope.py` (no runs)", "",
            "Per source point: the sfincs.dis column actually written (min / max / mean), what it is, and the GloFAS series the three candidate "
            "samplers would give — the cell nearest to the named point, the cell nearest to the injection point (src_lon/src_lat, Pineios only), "
            "and the max-mean-discharge cell of the ±0.1° window around the named point (the sampler's documented design, evaluated order-agnostically); peaks are over the simulated window tref..tstop (step-filled hourly), the JSON also holds the full-file daily peaks. "
            f"'src on lowest z_b' compares the written source cell with the lowest-z_b cell within ±{NCELLS} model cells (rule R).", ""]
    (out_dir / "d7_scope.md").write_text("\n".join(head + md) + "\n", encoding="utf-8")
    print("wrote", out_dir / "d7_scope.json", out_dir / "d7_scope.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
