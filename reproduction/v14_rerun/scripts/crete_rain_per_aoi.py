"""CODE-17 A5 (CODE-10 Stage 4b leftover) — EMSR933 Crete rainfall per AOI catchment.

The Stage-4 rainfall diagnostic was produced per NOA station (crete_rain_vs_noa.py); the CODE-10 brief asked for it per AOI
catchment. This script delivers that table from the same inputs, with no model run:
  * AOI catchment = the AOI's land cells plus every land cell whose flow path passes through the AOI, on the Stage-1 flow
    network (reproduction/emsr933/scripts/stage1_terrain.py: GLO-30 decimated 3x to ~90 m over the island box, sea <= 0 m
    masked, depressions filled, pyflwdir D8) = the basins of the AOI's outlet cells and inner pits (the cells Stage 1
    summed as "uparea_sum_at_outlets"); AOI extents from the latest EMS API manifest (Stage 5).
  * per catchment: area-weighted mean and maximum event total of raw IMERG Late, IMERG after R2 (the canonical run's
    forcing file) and ERA5(T), each ~90 m cell taking the total of the grid cell nearest to its centre; windows = the R2
    anchor window (local days 30 Sep - 4 Oct 2026 = 2026-09-29T21:00Z -> 2026-10-04T21:00Z, as crete_rain_vs_noa) and
    the simulated window [tstart, tstop) of the run config;
  * NOA/meteo.gr stations whose header position (rounded to 0.1 deg) falls inside the catchment, with their five-day totals.
Tiers and AOI names are read from phase5/crete_canonical_r2on_tiers.json (rule_ledger.md §8 item 3).
Output: JSON + CSV + one PNG (grouped bars, the style of crete_rain_vs_noa.png).

Usage: python -I crete_rain_per_aoi.py --repo <worktree> --event-root D:/ELKAK/implementation/emsr933_crete
       --raw <imerg_crete.raw.nc> --r2 <imerg_crete.nc of the canonical run> --era5 <era5_crete.nc>
       --config reproduction/v14_rerun/configs/crete_canonical_r2on.yaml --out-json reproduction/v14_rerun/phase5/crete_rain_per_aoi.json
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def nearest_index(coords: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Index of the coordinate nearest to each value (coords 1-D, ascending or descending)."""
    c = np.asarray(coords, dtype=float)
    order = np.argsort(c)
    cs = c[order]
    pos = np.clip(np.searchsorted(cs, values), 1, len(cs) - 1)
    left, right = cs[pos - 1], cs[pos]
    pick = np.where(np.abs(values - left) <= np.abs(right - values), pos - 1, pos)
    return order[pick]


def field_total(da, t0, t1):
    """Event total (mm) per grid cell over [t0, t1): sum of the rates x the step (h), as crete_rain_vs_noa.nearest_total_mm."""
    import pandas as pd
    t = pd.to_datetime(da["time"].values)
    sel = (t >= pd.Timestamp(t0)) & (t < pd.Timestamp(t1))
    step_h = float(np.median(np.diff(t.values).astype("timedelta64[s]").astype(float)) / 3600.0) if len(t) > 1 else 1.0
    sub = da.isel(time=np.where(sel)[0]).transpose("time", "latitude", "longitude")
    tot = np.nansum(np.asarray(sub.values, dtype=float), axis=0) * step_h
    return tot, np.asarray(da["latitude"].values, dtype=float), np.asarray(da["longitude"].values, dtype=float), step_h, int(sel.sum())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--event-root", required=True, type=Path)
    ap.add_argument("--raw", required=True, type=Path)
    ap.add_argument("--r2", required=True, type=Path)
    ap.add_argument("--era5", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--days", default="2026-09-30,2026-10-04")
    ap.add_argument("--noa-stations", action="store_true",
                    help="also list the NOA/meteo.gr stations inside each catchment with their totals (station values are not committed; off by default)")
    a = ap.parse_args()
    repo = a.repo
    st1 = _load(repo / "reproduction/emsr933/scripts/stage1_terrain.py", "stage1_terrain")
    rvn = _load(repo / "reproduction/v14_rerun/scripts/crete_rain_vs_noa.py", "crete_rain_vs_noa")
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    from _common import load_config  # noqa: E402
    import pyflwdir
    from shapely import wkt as swkt

    t_start = dt.datetime.now(dt.timezone.utc)
    cfg = load_config(["--config", str(a.config)])
    sim0, sim1 = cfg.tstart, cfg.tstop
    d0, d1 = a.days.split(",")
    w0, w1 = rvn.utc_window(d0, d1)

    # ---- Stage-1 flow network (same calls and parameters as stage1_terrain.main)
    vrt = a.event_root / "data/copdem30/copdem30.vrt"
    dem, transform, shape = st1.read_dem(vrt)
    carea2d = np.repeat(st1.cell_area_km2(transform, shape)[:, None], shape[1], axis=1)
    land = np.isfinite(dem) & (dem > 0)
    dem_h = np.where(land, dem, -9999.0).astype("float32")
    flw = pyflwdir.from_dem(data=dem_h, nodata=-9999.0, max_depth=-1.0, transform=transform, latlon=True, outlets="edge")
    uparea = flw.upstream_area(unit="km2")
    uparea = np.where(uparea < 0, np.nan, uparea).ravel()
    idxs_ds = flw.idxs_ds.astype(np.int64)

    manifests = sorted((repo / "reproduction/emsr933").glob("ems_snapshot_*_manifest.json"))
    manifest_path = manifests[-1]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tier_rec = json.loads((repo / "reproduction/v14_rerun/phase5/crete_canonical_r2on_tiers.json").read_text(encoding="utf-8"))
    tiers = tier_rec["aois"]
    # AOIs without a product (tier 3) carry no entry; their codes are listed in the record's rule text
    import re
    m3 = re.search(r"tier 3 excluded \(([0-9/]+)\)", tier_rec["rule"])
    tier3 = set(m3.group(1).split("/")) if m3 else set()

    # ---- fields and NOA stations
    fields = {"imerg_raw_mm": rvn._open(a.raw), "imerg_r2_mm": rvn._open(a.r2), "era5_mm": rvn._open(a.era5)}
    xs = transform.c + (np.arange(shape[1]) + 0.5) * transform.a
    ys = transform.f + (np.arange(shape[0]) + 0.5) * transform.e
    totals = {}
    for k, da in fields.items():
        for wname, (t0, t1) in (("anchor", (w0, w1)), ("simulated", (sim0, sim1))):
            tot, lats, lons, step_h, nsteps = field_total(da, t0, t1)
            ri, ci = nearest_index(lats, ys), nearest_index(lons, xs)
            totals[(k, wname)] = {"on_dem": tot[np.ix_(ri, ci)], "step_h": step_h, "n_steps": nsteps,
                                  "cell_ids": (ri[:, None] * 100000 + ci[None, :])}
    stations = rvn.station_totals(repo / "reproduction/emsr933/noa_stations/stations_daily.csv", (d0, d1)) if a.noa_stations else {}

    rows = []
    masks = {ao["number"]: st1.rasterize(swkt.loads(ao["extent_wkt"]), transform, shape) for ao in manifest["aois"]}
    for ao in sorted(manifest["aois"], key=lambda x: x["number"]):
        k = ao["number"]
        code = f"{k:02d}"
        m = masks[k]
        mf = m.ravel()
        idx_in = np.where(mf)[0]
        ds = idxs_ds[idx_in]
        pits_inside = idx_in[ds == idx_in]
        outlets = idx_in[(ds != idx_in) & ~mf[ds]]
        seeds = np.concatenate([outlets, pits_inside]).astype(np.int64)
        bas = flw.basins(idxs=seeds) if seeds.size else np.zeros(shape, dtype=np.int32)
        catch = ((bas > 0) | m) & land
        aoi_land = m & land
        t = tiers.get(code, {})
        rec = {"aoi": code, "name": t.get("name", ao["name"]), "tier": t.get("tier", 3 if code in tier3 else None),
               "aoi_land_km2": round(float(carea2d[aoi_land].sum()), 2),
               "catchment_km2": round(float(carea2d[catch].sum()), 1),
               "stage1_uparea_sum_at_outlets_km2": round(float(np.nansum(uparea[outlets])), 1),
               "n_outlet_cells": int(outlets.size), "n_pits_inside": int(pits_inside.size),
               # Stage 1 gave a cell in two AOI boxes to the lower-numbered AOI; here every AOI keeps its full extent
               "overlap_with_other_aois_km2": {f"{j:02d}": round(float(carea2d[m & mj].sum()), 2)
                                               for j, mj in sorted(masks.items()) if j != k and (m & mj).any()},
               "catchment_contains_aois": [f"{j:02d}" for j, mj in sorted(masks.items()) if j != k and (mj & land).any()
                                           and bool(((bas > 0) & mj & land).sum() >= 0.5 * (mj & land).sum())]}
        wts = carea2d[catch]
        for (fk, wname), tt in totals.items():
            vals = tt["on_dem"][catch]
            rec[f"{fk}_{wname}_mean"] = round(float(np.sum(vals * wts) / np.sum(wts)), 1)
            rec[f"{fk}_{wname}_max"] = round(float(vals.max()), 1)
            rec[f"{fk}_n_grid_cells"] = int(np.unique(tt["cell_ids"][catch]).size)
            avals = tt["on_dem"][aoi_land]
            rec[f"{fk}_{wname}_aoi_mean"] = (round(float(np.sum(avals * carea2d[aoi_land]) / np.sum(carea2d[aoi_land])), 1)
                                             if avals.size else None)
        inside = []
        for slug, s in sorted(stations.items()):
            r_ = int(np.floor((s["lat"] - transform.f) / transform.e))
            c_ = int(np.floor((s["lon"] - transform.c) / transform.a))
            if 0 <= r_ < shape[0] and 0 <= c_ < shape[1] and catch[r_, c_]:
                inside.append({"station": slug, "lat": s["lat"], "lon": s["lon"], "noa_total_mm": round(s["noa_total_mm"], 1),
                               "n_days": s["n_days"]})
        if a.noa_stations:
            rec["noa_stations_inside"] = inside
        rows.append(rec)

    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "script": "reproduction/v14_rerun/scripts/crete_rain_per_aoi.py",
           "windows_utc": {"anchor": [w0.isoformat(), w1.isoformat()], "simulated": [str(sim0), str(sim1)]},
           "anchor_local_days": [d0, d1],
           "inputs": {"raw": str(a.raw), "r2": str(a.r2), "era5": str(a.era5), "config": str(a.config), "dem_vrt": str(vrt),
                      "aoi_manifest": str(manifest_path.relative_to(repo)).replace("\\", "/"),
                      "tiers": "reproduction/v14_rerun/phase5/crete_canonical_r2on_tiers.json",
                      "noa": ("reproduction/emsr933/noa_stations/stations_daily.csv" if a.noa_stations else "not used (--noa-stations off)")},
           "time_step_h": {fk: totals[(fk, "anchor")]["step_h"] for fk in fields},
           "n_steps": {f"{fk}_{w}": totals[(fk, w)]["n_steps"] for fk in fields for w in ("anchor", "simulated")},
           "grid": {"shape": list(shape), "cell_deg": [round(transform.a, 6), round(-transform.e, 6)], "decimation": st1.DECIM},
           "catchment_definition": ("AOI land cells plus the basins of the AOI outlet cells and inner pits on the Stage-1 D8 network "
                                    "(filled GLO-30 at ~90 m); a cell takes the total of the nearest forcing-grid cell; means area-weighted"),
           "note": (("NOA station positions are rounded to 0.1 deg in the station headers, so 'inside' is indicative; NOA values from "
                     "meteo.gr station summaries (attribution required: Εθνικό Αστεροσκοπείο Αθηνών / meteo.gr)") if a.noa_stations else
                    "NOA/meteo.gr station values are not committed and not listed here (decision of 21 Oct 2026); the R2 anchor stays in the run config"),
           "aois": rows, "elapsed_s": round((dt.datetime.now(dt.timezone.utc) - t_start).total_seconds(), 1)}
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    cols = ["aoi", "name", "tier", "aoi_land_km2", "catchment_km2", "stage1_uparea_sum_at_outlets_km2"]
    for fk in fields:
        cols += [f"{fk}_anchor_mean", f"{fk}_anchor_max", f"{fk}_simulated_mean", f"{fk}_anchor_aoi_mean", f"{fk}_n_grid_cells"]
    cols += (["noa_stations_inside"] if a.noa_stations else [])
    with open(a.out_json.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "noa_stations_inside": "; ".join(f"{s['station']} {s['noa_total_mm']} mm ({s['n_days']} d)"
                                                              for s in r.get("noa_stations_inside", []))})

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "font.size": 8, "savefig.dpi": 300})
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    x = np.arange(len(rows))
    wdt = 0.8 / 3
    for i, (fk, lab, c) in enumerate([("imerg_raw_mm", "raw IMERG Late", "#7f7f7f"),
                                      ("imerg_r2_mm", "IMERG after R2 (447.8 mm anchor)", "#1f4e79"),
                                      ("era5_mm", "ERA5(T)", "#c0392b")]):
        ax.bar(x + i * wdt, [r[f"{fk}_anchor_mean"] for r in rows], wdt, color=c, label=f"{lab}, catchment mean")
    first = True
    for i, r in enumerate(rows):
        for s in r.get("noa_stations_inside", []):
            ax.plot(i + wdt, s["noa_total_mm"], "k^", mfc="k" if s["n_days"] == 5 else "none", ms=4,
                    label="NOA station inside the catchment (open = incomplete record)" if first else None)
            first = False
    ax.set_xticks(x + wdt)
    ax.set_xticklabels([f"AOI{r['aoi']} {r['name']}\n(tier {r['tier']}, {r['catchment_km2']:.0f} km²)" for r in rows],
                       rotation=30, ha="right", fontsize=6.5)
    ax.set_ylabel("5-day total (mm)")
    ax.set_title("EMSR933 Crete: AOI-catchment totals, 29 Sep 21:00 → 4 Oct 21:00 UTC", fontsize=8)
    ax.legend(fontsize=6.5, frameon=False)
    fig.tight_layout()
    fig.savefig(a.out_json.with_suffix(".png"))
    plt.close(fig)
    for r in rows:
        print(f"AOI{r['aoi']} {r['name']:12s} tier {r['tier']} catchment {r['catchment_km2']:7.1f} km2 "
              f"(stage1 sum {r['stage1_uparea_sum_at_outlets_km2']}) raw {r['imerg_raw_mm_anchor_mean']:6.1f} "
              f"R2 {r['imerg_r2_mm_anchor_mean']:6.1f} ERA5 {r['era5_mm_anchor_mean']:6.1f} mm; "
              + (f"NOA inside: {[(s['station'], s['noa_total_mm']) for s in r['noa_stations_inside']]}" if a.noa_stations else ""))
    print(f"elapsed {out['elapsed_s']} s -> {a.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
