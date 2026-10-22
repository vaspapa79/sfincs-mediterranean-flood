"""CODE-17 C6 — observed-area inflation of the validator's any-touched burning against centre burning, per event.

The validator (validation/validate_event_v2.py) burns the EMS observed-flood polygons onto the SFINCS grid with
rasterio all_touched=True (a cell is observed-wet when a polygon touches it). Centre burning (all_touched=False) marks a
cell wet only when its centre lies inside a polygon. For each event this script counts observed-wet cells both ways
inside the evaluation universe and reports inflation = any-touched / centre - 1:
  * v1.4 universe: the run of record's grid, AOI ∩ active minus the v1.4 exclusion (WorldCover 80 ∪ open sea,
    reproduction/v14_rerun/masks/<event>_exclusion.tif) — exactly the validator's evaluation mask;
  * release universe (check of the method against the release figures +18/+52/+82 % for Pineios/Strymonas/Mandra):
    the published model's grid, AOI ∩ active, no exclusion.
Polygons, AOIs, product preference (validate_event_v2._select_obs_shps) and grid come from the validator; the any-touched
raster is asserted equal to validate_event_v2._rasterise_polys_to_grid. The vector area of the observed polygons inside
the AOIs is given for reference. Crete: no union (rule_ledger.md §8 item 3) — the tier-1 block (AOI03) and each tier-2 AOI
on its own universe, as reproduction/v14_rerun/scripts/crete_tier_scores.py.

Usage: python -I c6_alltouched_inflation.py --repo <worktree> --out-json reproduction/v14_rerun/code17/c6_alltouched_inflation.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

RUNS = [
    {"event": "pineios", "run": "pineios_enhanced_v142", "release_run": "pineios_enhanced"},
    {"event": "strymonas", "run": "strymonas_enhanced_postD6_v142", "release_run": "strymonas_enhanced"},
    {"event": "mandra", "run": "mandra_enhanced", "release_run": "mandra_enhanced"},
    {"event": "valencia", "run": "valencia_enhanced_164_v142", "release_run": "valencia_enhanced_164"},
    {"event": "emilia", "run": "emilia_enhanced_8aoi_v142", "release_run": "emilia_enhanced_8aoi"},
    {"event": "crete", "run": "crete_canonical_r2on", "release_run": None},
]
CRETE_TIERS = {"03": 1, "01": 2, "04": 2, "06": 2, "07": 2}  # rule_ledger.md §8 item 3 (tier 3 = no product)
VECTOR_MAX_GEOMS = 2000   # reference vector area only below this polygon count (None above it)


def read_geoms(shp_paths, target_epsg):
    import pyogrio
    import pyproj
    from shapely import from_wkb
    from shapely.ops import transform as shp_transform
    target = pyproj.CRS.from_epsg(target_epsg)
    out = []
    for shp in shp_paths:
        if not shp.exists():
            continue
        info = pyogrio.read_info(shp)
        src = pyproj.CRS.from_user_input(info["crs"])
        _, _, gw, _ = pyogrio.raw.read(str(shp), return_fids=True)
        gs = [from_wkb(g) for g in gw]
        if src != target:
            tr = pyproj.Transformer.from_crs(src, target, always_xy=True).transform
            gs = [shp_transform(tr, g) for g in gs]
        out.extend(g for g in gs if not g.is_empty)
    return out


def burn(geoms, s, all_touched: bool) -> np.ndarray:
    """validate_event_v2._rasterise_polys_to_grid with the all_touched switch exposed (same transform and row flip)."""
    import rasterio.features
    from rasterio.transform import from_bounds
    x_grid, y_grid, dx, dy = s["x"], s["y"], s["dx"], s["dy"]
    ny, nx = x_grid.shape
    xs = x_grid[0, :]
    ys = y_grid[:, 0]
    transform = from_bounds(float(xs.min()) - dx / 2.0, float(ys.min()) - dy / 2.0, float(xs.max()) + dx / 2.0,
                            float(ys.max()) + dy / 2.0, nx, ny)
    if not geoms:
        return np.zeros((ny, nx), dtype=bool)
    out = rasterio.features.rasterize(((g, 1) for g in geoms), out_shape=(ny, nx), transform=transform,
                                      all_touched=all_touched, dtype="uint8")
    return out[::-1, :].astype(bool)


def counts(obs_geoms, aoi_geoms, universe, s, V, obs_shps, epsg, hmax=None, thr=0.10) -> dict:
    touched = burn(obs_geoms, s, True)
    ref = V._rasterise_polys_to_grid(obs_shps, s["x"], s["y"], epsg, s["dx"], s["dy"])
    assert np.array_equal(touched, ref), "any-touched raster differs from the validator's"
    centre = burn(obs_geoms, s, False)
    A = s["cell_area_km2"]
    nt, nc = int((touched & universe).sum()), int((centre & universe).sum())
    from shapely import union_all
    vec = None
    if obs_geoms and aoi_geoms and len(obs_geoms) <= VECTOR_MAX_GEOMS:   # the reference union is slow for large truths
        vec = float(union_all(obs_geoms).intersection(union_all(aoi_geoms)).area) / 1e6
    out = {"n_obs_polygons": len(obs_geoms), "universe_km2": round(float(universe.sum() * A), 3), "universe_cells": int(universe.sum()),
           "cells_any_touched": nt, "cells_centre": nc,
           "observed_km2_any_touched": round(nt * A, 4), "observed_km2_centre": round(nc * A, 4),
           "observed_km2_vector_in_aois": (round(vec, 4) if vec is not None else None),
           "inflation_pct": (round(100.0 * (nt / nc - 1.0), 1) if nc else None),
           "any_touched_over_vector": (round(nt * A / vec, 3) if vec else None)}
    if hmax is not None:
        # labelled re-scoring sensitivity (no SFINCS run): the run's h_max > thr against the truth burned by cell centre,
        # same grid and universe; the any-touched contingency is the validator's (asserted against the record by the caller)
        mw = hmax > thr
        keys = ("tp", "fp", "fn", "tn", "csi", "hr", "far", "bias", "gss", "f2")
        out["strict_h_gt_%s" % f"{thr:.2f}".replace(".", "p")] = {
            "any_touched": {k: V._contingency_full(mw, touched, universe)[k] for k in keys},
            "centre": {k: V._contingency_full(mw, centre, universe)[k] for k in keys}}
    return out


def hmax_of(s):
    zsmax = s["ds"]["zsmax"].max(dim="timemax").values
    return np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    a = ap.parse_args()
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    sys.path.insert(0, str(repo / "validation"))
    os.environ.setdefault("GDAL_DATA", os.path.join(os.environ.get("CONDA_PREFIX", sys.prefix), "Library", "share", "gdal"))
    from _common import load_config
    import validate_event_v2 as V
    from eval_exclusion import read_mask_for_grid
    spec = importlib.util.spec_from_file_location("phase1", repo / "reproduction/v14_rerun/scripts/phase1.py")
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)
    published = {r["run"]: r.get("published_model") for r in P.RUNS}

    t0 = dt.datetime.now(dt.timezone.utc)
    events = []
    for e in RUNS:
        cfg_path = repo / "reproduction/v14_rerun/configs" / f"{e['run']}.yaml"
        cfg = load_config(["--config", str(cfg_path)])
        s = V.open_sfincs_light(cfg.paths["model_dir"])
        excl_tif = repo / "reproduction/v14_rerun/masks" / f"{e['event']}_exclusion.tif"
        excl = read_mask_for_grid(excl_tif, s)
        ems_dir = cfg.paths["data_dir"] / "ems_polygons"
        obs_shps = V._select_obs_shps(ems_dir, include_del_product=bool(cfg.ems.get("include_del_product", False)))
        aoi_shps = V._list_shps(ems_dir, ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"])
        rec = {"event": e["event"], "run": e["run"], "config": str(cfg_path.relative_to(repo)).replace("\\", "/"),
               "model_dir": str(cfg.paths["model_dir"]), "exclusion_tif": str(excl_tif.relative_to(repo)).replace("\\", "/"),
               "cell_m": [s["dx"], s["dy"]], "n_obs_files": len(obs_shps), "n_aoi_files": len(aoi_shps),
               "obs_packages": sorted({p.parent.name for p in obs_shps})}
        active = s["msk"] > 0
        if e["event"] != "crete":
            obs_g, aoi_g = read_geoms(obs_shps, cfg.epsg), read_geoms(aoi_shps, cfg.epsg)
            aoi_mask = V._rasterise_polys_to_grid(aoi_shps, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"])
            rec["v14_universe"] = counts(obs_g, aoi_g, active & aoi_mask & ~excl, s, V, obs_shps, cfg.epsg, hmax=hmax_of(s))
            rj = json.loads((repo / "reproduction/v14_rerun/results" / f"{e['run']}_v14_newmask.json").read_text(encoding="utf-8"))["validation"]["strict_threshold_sweep"]["h>0.10m"]
            at = rec["v14_universe"]["strict_h_gt_0p10"]["any_touched"]
            assert all(int(at[k]) == int(rj[k]) for k in ("tp", "fp", "fn", "tn")), f"{e['run']}: any-touched contingency != record"
            rec["record_checked"] = f"results/{e['run']}_v14_newmask.json strict h>0.10m (tp/fp/fn/tn identical)"
            pm = published.get(e["release_run"]) if e["release_run"] else None
            if pm and (Path(pm) / "sfincs_map.nc").exists():
                sp = V.open_sfincs_light(Path(pm))
                aoi_p = V._rasterise_polys_to_grid(aoi_shps, sp["x"], sp["y"], cfg.epsg, sp["dx"], sp["dy"])
                rec["release_universe"] = {"model_dir": str(pm), **counts(obs_g, aoi_g, (sp["msk"] > 0) & aoi_p, sp, V, obs_shps, cfg.epsg)}
                sp["ds"].close()
        else:
            def code(p):
                m = re.search(r"AOI(\d\d)", p.name)
                return m.group(1) if m else None
            rec["aois"] = {}
            for c, tier in sorted(CRETE_TIERS.items()):
                o = [p for p in obs_shps if code(p) == c]
                ai = [p for p in aoi_shps if code(p) == c]
                uni = active & ~excl & V._rasterise_polys_to_grid(ai, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"])
                rec["aois"][c] = {"tier": tier, "obs_files": [p.name for p in o],
                                  **counts(read_geoms(o, cfg.epsg), read_geoms(ai, cfg.epsg), uni, s, V, o, cfg.epsg,
                                           hmax=(hmax_of(s) if tier == 1 else None))}
                if tier == 1:
                    tj = json.loads((repo / "reproduction/v14_rerun/phase5" / f"{e['run']}_tiers.json").read_text(encoding="utf-8"))["aois"][c]["strict_threshold_sweep"]["h>0.10m"]
                    at = rec["aois"][c]["strict_h_gt_0p10"]["any_touched"]
                    assert all(int(at[k]) == int(tj[k]) for k in ("tp", "fp", "fn", "tn")), "crete AOI03: any-touched contingency != tiers JSON"
                    rec["record_checked"] = f"phase5/{e['run']}_tiers.json AOI03 strict h>0.10m (tp/fp/fn/tn identical)"
        s["ds"].close()
        events.append(rec)
        v = rec.get("v14_universe") or rec["aois"]["03"]
        print(f"{e['event']:9s} v1.4: touched {v['observed_km2_any_touched']:9.3f} km2, centre {v['observed_km2_centre']:9.3f} km2, "
              f"vector {v['observed_km2_vector_in_aois']} km2, inflation {v['inflation_pct']} %"
              + (f" | release universe: inflation {rec['release_universe']['inflation_pct']} %" if rec.get("release_universe") else ""), flush=True)
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "script": "reproduction/v14_rerun/scripts/c6_alltouched_inflation.py",
           "definition": "inflation = observed-wet cells burned any-touched / burned by cell centre - 1, inside the universe; "
                         "strict_h_gt_0p10.centre = labelled re-scoring sensitivity (no SFINCS run): the run of record's h_max > 0.10 m "
                         "against the truth burned by cell centre on the same grid and universe",
           "release_figures_checked": "manuscript release text: +18 % (Pineios), +52 % (Strymonas), +82 % (Mandra), release evaluation mask",
           "events": events, "elapsed_s": round((dt.datetime.now(dt.timezone.utc) - t0).total_seconds(), 1)}
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    for r in events:
        if r["event"] == "crete":
            for c, v in r["aois"].items():
                print(f"  crete AOI{c} tier {v['tier']}: touched {v['observed_km2_any_touched']} centre {v['observed_km2_centre']} "
                      f"vector {v['observed_km2_vector_in_aois']} km2, inflation {v['inflation_pct']} %")
    print(f"elapsed {out['elapsed_s']} s -> {a.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
