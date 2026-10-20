"""Phase 4b (GO Phases 3-5, 2026-10-19) — time-matched diagnostic (supplement, not canonical).

The canonical score compares the EMS observed extent with hmax over the whole simulated window. Here hmax is accumulated
only up to the acquisition time of each EMS product (the state the satellite could see), on that product's own truth
polygons and AOI universe, with the v1.4 evaluation mask (exclusion GeoTIFF) applied on both sides. Post-processing only:
nothing is re-run.

hmax up to t: the maximum of (a) the hourly `zs` output at times <= t and (b) every daily `zsmax` block that is complete
by t (SFINCS writes zsmax at the END of each dtmaxout interval; a block adds the sub-hourly peaks the hourly zs misses),
minus zb, floored at 0, NaN -> 0 as in the validator. With t = None this equals the validator's hmax (plus the hourly
series, which never exceeds the block maxima).

Acquisition times come from the EMS package `*source*` layers ('Post-event' rows: src_date 'DD/MM/YYYY', source_tm
'THH:MM:SSZ' or 'HH:MM:SS'); legacy packages (EMSR122) carry only a date on the crisis polygon, which is flagged
date_only and evaluated at the end of that day (and at its start, as the bracket).

Usage: python -I time_matched_scores.py --repo <worktree> --config <run yaml> --exclusion-tif <tif> --out-json <...>
       [--window t0,t1]   (optional: also score hmax restricted to the window t0..t1, e.g. the canonical Strymonas
                           window for the lead-in sensitivity; UTC 'YYYY-MM-DDTHH:MM')
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

NON_IMAGE = {"Open Street Map", "CLC", "EuroBoundaryMap", "Not Applicable", "Null", "None", "FABDEM", "SRTM", "COPERNICUS DEM", "GLO-30", ""}


# ------------------------------------------------------------------------------------------- acquisition parsing
def parse_acq(date_s, time_s):
    """-> (datetime | None, date_only). Dates 'DD/MM/YYYY' or ISO; times 'THH:MM:SSZ' | 'HH:MM:SS' | missing."""
    d = str(date_s).strip() if date_s is not None else ""
    if not d or d in ("Not Applicable", "None", "nan", "NaT"):
        return None, True
    try:
        if "/" in d:
            day, mon, yr = (int(x) for x in d.split("/")[:3])
            base = dt.datetime(yr, mon, day)
        else:
            base = dt.datetime.fromisoformat(d[:10])
    except Exception:
        return None, True
    t = str(time_s).strip() if time_s is not None else ""
    t = t.lstrip("T").rstrip("Z")
    if not t or t in ("Not Applicable", "None", "nan"):
        return base, True
    try:
        hh, mm, ss = (t.split(":") + ["0", "0"])[:3]
        return base.replace(hour=int(hh), minute=int(mm), second=int(float(ss))), False
    except Exception:
        return base, True


def post_event_acquisitions(rows):
    """Post-event image acquisitions in a `*source*` layer -> sorted [(sensor, datetime, resolution)]."""
    out = []
    for r in rows:
        if not str(r.get("eventphase", "")).lower().startswith("post"):
            continue
        name = str(r.get("source_nam", "")).strip()
        if name in NON_IMAGE:
            continue
        when, _ = parse_acq(r.get("src_date"), r.get("source_tm"))
        if when is None:
            continue
        out.append((name, when, str(r.get("sensor_res", r.get("sensor_gsd", ""))).strip()))
    return sorted(out, key=lambda a: a[1])


def _dbf_rows(dbf: Path) -> list[dict]:
    import pyogrio
    meta, _, _, attrs = pyogrio.raw.read(str(dbf))
    cols = list(meta["fields"])
    n = len(attrs[0]) if attrs else 0
    return [{c: attrs[cols.index(c)][r] for c in cols} for r in range(n)]


def product_acquisition(obs_shp: Path):
    """Acquisition(s) of the product that holds an observed-flood shapefile.
    -> dict(product, sensor, acq_utc, date_only, n_post_images, all_post)."""
    pdir = obs_shp.parent
    name = pdir.name if pdir.name not in ("VECTOR", "Maps") else pdir.parent.name
    srcs = sorted(set(glob.glob(str(pdir / "*source*.dbf")) + glob.glob(str(pdir / "**" / "*source*.dbf"), recursive=True)))
    acqs = []
    for sd in srcs:
        try:
            acqs += post_event_acquisitions(_dbf_rows(Path(sd)))
        except Exception:
            continue
    if acqs:
        sensor, when, res = acqs[-1]                      # the latest post-event image: the state the product reflects
        return {"product": name, "sensor": sensor, "resolution": res, "acq_utc": when, "date_only": False,
                "n_post_images": len(acqs), "all_post": [(a[0], a[1].isoformat()) for a in acqs], "source": "source layer"}
    # legacy: date on the crisis polygon itself
    rows = _dbf_rows(obs_shp.with_suffix(".dbf"))
    dates = sorted({str(r.get("src_date"))[:10] for r in rows if r.get("src_date") not in (None, "", "Null")})
    if dates:
        when, _ = parse_acq(dates[-1], None)
        return {"product": name, "sensor": "SAR delineation (legacy package, date only)", "resolution": "", "acq_utc": when, "date_only": True,
                "n_post_images": len(dates), "all_post": [("src_date", d) for d in dates], "source": "polygon src_date"}
    return {"product": name, "sensor": "?", "resolution": "", "acq_utc": None, "date_only": True, "n_post_images": 0, "all_post": [], "source": "none"}


# ------------------------------------------------------------------------------------------- running hmax
def running_hmax(ds, zb, t_to, t_from=None):
    """hmax accumulated over (t_from, t_to]: hourly zs at times in the window + every zsmax block entirely inside it."""
    import pandas as pd
    zb = np.asarray(zb, dtype=float)
    times = pd.to_datetime(ds["time"].values)
    sel = np.ones(len(times), dtype=bool)
    if t_to is not None:
        sel &= times <= pd.Timestamp(t_to)
    if t_from is not None:
        sel &= times > pd.Timestamp(t_from)
    h = np.zeros(zb.shape, dtype=float)
    # frame by frame: a block selection materialises the whole (time, n, m) array (2.4 GB + a bool mask on the Crete grid)
    for i in np.where(sel)[0]:
        zs = ds["zs"].isel(time=int(i)).values
        h = np.maximum(h, np.where(np.isnan(zs), 0.0, np.maximum(zs - zb, 0)))
    if "zsmax" in ds:
        tmax = pd.to_datetime(ds["timemax"].values)
        if len(tmax) > 1:
            block = (tmax[1:] - tmax[:-1]).min()
        else:
            block = pd.Timestamp(tmax[0]) - pd.Timestamp(times[0]) if len(times) else pd.Timedelta(days=1)
        starts = tmax - block
        keep = np.ones(len(tmax), dtype=bool)
        if t_to is not None:
            keep &= tmax <= pd.Timestamp(t_to)
        if t_from is not None:
            keep &= starts >= pd.Timestamp(t_from)
        for k in np.where(keep)[0]:
            zm = ds["zsmax"].isel(timemax=int(k)).values
            h = np.maximum(h, np.where(np.isnan(zm), 0.0, np.maximum(zm - zb, 0)))
    return h


def running_hmax_snapshots(ds, zb, times):
    """One pass over the hourly zs (and the zsmax blocks): the running maximum (hmax over (-inf, t]) for every t in
    `times`, returned as {t: array}. Equivalent to running_hmax(ds, zb, t) for each t, with each frame read once."""
    import pandas as pd
    zb = np.asarray(zb, dtype=float)
    want = sorted({pd.Timestamp(t) for t in times})
    tt = pd.to_datetime(ds["time"].values)
    events = [(t, "zs", i) for i, t in enumerate(tt)]
    if "zsmax" in ds:
        tmax = pd.to_datetime(ds["timemax"].values)
        events += [(t, "zsmax", k) for k, t in enumerate(tmax)]
    events.sort(key=lambda e: (e[0], e[1]))
    h = np.zeros(zb.shape, dtype=float)
    out = {}
    j = 0
    for t, kind, i in events:
        while j < len(want) and want[j] < t:
            out[want[j]] = h.copy(); j += 1
        z = ds["zs"].isel(time=int(i)).values if kind == "zs" else ds["zsmax"].isel(timemax=int(i)).values
        h = np.maximum(h, np.where(np.isnan(z), 0.0, np.maximum(z - zb, 0)))
    while j < len(want):
        out[want[j]] = h.copy(); j += 1
    return {t: out[pd.Timestamp(t)] for t in times}


# ------------------------------------------------------------------------------------------- main
def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--exclusion-tif", type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--window", default="", help="t0,t1 UTC (YYYY-MM-DDTHH:MM): also score hmax restricted to this window")
    ap.add_argument("--threshold", type=float, default=0.10)
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts")); sys.path.insert(0, str(a.repo / "validation"))
    os.environ.setdefault("GDAL_DATA", os.path.join(os.environ.get("CONDA_PREFIX", ""), "Library", "share", "gdal"))
    from _common import load_config
    from validate_event_v2 import _rasterise_polys_to_grid, _contingency_full, _select_obs_shps, _list_shps, open_sfincs_light
    cfg = load_config(["--config", str(a.config)])
    s = open_sfincs_light(cfg.paths["model_dir"])      # zs stays lazy; running_hmax reads only the frames it needs
    excl = None
    if a.exclusion_tif:
        from eval_exclusion import read_mask_for_grid
        excl = read_mask_for_grid(a.exclusion_tif, s)
    ems_dir = cfg.paths["data_dir"] / "ems_polygons"
    obs_shps = _select_obs_shps(ems_dir, include_del_product=bool(cfg.ems.get("include_del_product", False)))
    aoi_pats = ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"]
    aoi_all = _list_shps(ems_dir, aoi_pats)
    sys.path.insert(0, str(Path(__file__).resolve().parent))      # python -I: the script directory is not on sys.path
    from truth_cache import cache_key, cached_bool
    cache_dir = a.out_json.parent / "_cache"

    def rast(shps, tag):
        return cached_bool(cache_dir, cache_key(cfg.event_slug, s, shps, tag), lambda: _rasterise_polys_to_grid(list(shps), s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]))
    active = s["msk"] > 0
    if excl is not None:
        active = active & ~excl
    A = s["cell_area_km2"]
    ds, zb = s["ds"], s["zb"]
    thr = a.threshold

    def score(h, truth, universe):
        return _contingency_full(h > thr, truth, universe)

    metas = [product_acquisition(shp) for shp in obs_shps]
    need = []
    for meta in metas:
        if meta["acq_utc"] is not None:
            t_acq = meta["acq_utc"]
            need += ([t_acq + dt.timedelta(days=1) - dt.timedelta(seconds=1), t_acq] if meta["date_only"] else [t_acq])
    snap = running_hmax_snapshots(ds, zb, need) if need else {}
    h_full = running_hmax(ds, zb, None)
    products = []
    acq_times = []
    for shp, meta in zip(obs_shps, metas):
        truth = rast([shp], "product")
        # universe = the AOI polygon of this product's folder (fallback: any AOI file sharing the AOI token, else the whole active mask)
        pdir = shp.parent
        aoi_here = _list_shps(pdir, aoi_pats)
        if not aoi_here:
            m = re.search(r"(AOI\d+|\d{2}[A-Z]+)", shp.name)
            aoi_here = [p for p in aoi_all if m and m.group(1) in p.name]
        universe = active & (rast(aoi_here, "aoi") if aoi_here else np.ones_like(active))
        row = {**{k: (v.isoformat() if isinstance(v, dt.datetime) else v) for k, v in meta.items()}, "obs_shp": shp.name,
               "universe_km2": float(universe.sum() * A), "obs_km2": float((truth & universe).sum() * A), "aoi_files": [p.name for p in aoi_here],
               "full_window": score(h_full, truth, universe)}
        if meta["acq_utc"] is not None:
            t_acq = meta["acq_utc"]
            if meta["date_only"]:
                t_end = t_acq + dt.timedelta(days=1) - dt.timedelta(seconds=1)
                row["time_matched"] = score(snap[t_end], truth, universe); row["time_matched_at"] = t_end.isoformat()
                row["time_matched_start_of_day"] = score(snap[t_acq], truth, universe)
            else:
                row["time_matched"] = score(snap[t_acq], truth, universe); row["time_matched_at"] = t_acq.isoformat()
            acq_times.append(t_acq if not meta["date_only"] else t_acq + dt.timedelta(days=1) - dt.timedelta(seconds=1))
        products.append(row)
    # union over all products (the canonical truth), hmax up to the earliest and the latest acquisition
    aoi_universe = active & (rast(aoi_all, "aoi_all") if aoi_all else np.ones_like(active))
    truth_all = rast(obs_shps, "truth_union")
    union = {"universe_km2": float(aoi_universe.sum() * A), "obs_km2": float((truth_all & aoi_universe).sum() * A),
             "full_window": score(h_full, truth_all, aoi_universe)}
    if acq_times:
        t0, t1 = min(acq_times), max(acq_times)
        union["earliest_acq_utc"] = t0.isoformat(); union["latest_acq_utc"] = t1.isoformat()
        union["hmax_to_earliest"] = score(snap[t0], truth_all, aoi_universe)
        union["hmax_to_latest"] = score(snap[t1], truth_all, aoi_universe)
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "config": str(a.config), "model_dir": str(cfg.paths["model_dir"]),
           "event": cfg.event_slug, "threshold_m": thr, "exclusion_tif": (str(a.exclusion_tif) if a.exclusion_tif else None),
           "simulated_window": [str(cfg.tstart), str(cfg.tstop)], "n_products": len(products), "products": products, "union": union,
           "method": "hmax(t) = max(hourly zs <= t, daily zsmax blocks complete by t) - zb; truth = the product's polygons; universe = AOI ∩ active minus exclusion"}
    if a.window:
        w0, w1 = (dt.datetime.fromisoformat(x) for x in a.window.split(","))
        hw = running_hmax(ds, zb, w1, t_from=w0)
        out["window"] = {"t0": w0.isoformat(), "t1": w1.isoformat(), "union": score(hw, truth_all, aoi_universe),
                         "products": {p["product"]: score(hw, rast([shp], "product"), aoi_universe) for p, shp in zip(products, obs_shps)}}
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    for p in products:
        tmr = p.get("time_matched", {})
        print(f"{p['product']:48s} acq {p.get('time_matched_at', '-')[:16]:16s} {p['sensor'][:18]:18s} CSI full {p['full_window']['csi']:.3f} -> time-matched {tmr.get('csi', float('nan')):.3f}  "
              f"HR {p['full_window']['hr']:.3f} -> {tmr.get('hr', float('nan')):.3f}  B {p['full_window']['bias']:.2f} -> {tmr.get('bias', float('nan')):.2f}")
    if acq_times:
        print(f"union: full {union['full_window']['csi']:.3f}; to earliest acq {union['hmax_to_earliest']['csi']:.3f}; to latest acq {union['hmax_to_latest']['csi']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
