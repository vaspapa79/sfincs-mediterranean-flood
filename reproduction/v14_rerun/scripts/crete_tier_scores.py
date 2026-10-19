"""Phase 5 Stage 4 (GO Phases 3-5, 2026-10-19) — EMSR933 Crete scoring by the rule_ledger.md §8 tiers, from one run's output.

Tier 1 (scored) = AOI03 Tzermiado: strict contingency at 0.05 / 0.10 / 0.25 / 0.50 m (CSI/HR/FAR/B/GSS), fuzzy r = 0..3 at
0.10 m, CSI* / B* (best threshold), SEDI / PSS — on the AOI's own universe (AOI ∩ active minus the v1.4 exclusion) against the
AOI's released delineation packages. Tier 2 (AOIs 01, 04, 06, 07) = observed vs modelled km² at h > 0.10 m only. Tier 3
(02, 05, 08) = excluded (no product). No all-AOI union score is produced. Same rasterisation and contingency code as the
validator. Usage: python -I crete_tier_scores.py --repo <worktree> --config <run yaml> --exclusion-tif <tif> --out-json <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

TIER = {"03": 1, "01": 2, "04": 2, "06": 2, "07": 2, "02": 3, "05": 3, "08": 3}
NAMES = {"01": "Kastelli", "02": "Irakleio", "03": "Tzermiado", "04": "Agios Ioannis", "05": "Anogeia", "06": "Agios Nikolaos", "07": "Omalos", "08": "Monastiraki"}
THR = (0.05, 0.10, 0.25, 0.50)


def aoi_of(p: Path) -> str | None:
    m = re.search(r"AOI(\d\d)", p.name)
    return m.group(1) if m else None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--exclusion-tif", type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts")); sys.path.insert(0, str(a.repo / "validation"))
    os.environ.setdefault("GDAL_DATA", os.path.join(os.environ.get("CONDA_PREFIX", ""), "Library", "share", "gdal"))
    from _common import load_config
    import validate_event_v2 as V
    import skill_scores as ss
    cfg = load_config(["--config", str(a.config)])
    s = V.open_sfincs_light(cfg.paths["model_dir"])
    excl = None
    if a.exclusion_tif:
        from eval_exclusion import read_mask_for_grid
        excl = read_mask_for_grid(a.exclusion_tif, s)
    ems_dir = cfg.paths["data_dir"] / "ems_polygons"
    obs = V._select_obs_shps(ems_dir, include_del_product=bool(cfg.ems.get("include_del_product", False)))
    aois = V._list_shps(ems_dir, ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"])
    active = s["msk"] > 0
    if excl is not None:
        active = active & ~excl
    A = s["cell_area_km2"]
    zsmax = s["ds"]["zsmax"].max(dim="timemax").values
    hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "config": str(a.config), "model_dir": str(cfg.paths["model_dir"]),
           "exclusion_tif": (str(a.exclusion_tif) if a.exclusion_tif else None), "rule": "rule_ledger.md §8 item 3 — tier 1 scored (AOI03), tier 2 km² only (01/04/06/07), tier 3 excluded (02/05/08); no union score",
           "observed_packages": [p.parent.name for p in obs], "aois": {}}
    by_aoi_obs = {}
    for p in obs:
        by_aoi_obs.setdefault(aoi_of(p), []).append(p)
    by_aoi_aoi = {}
    for p in aois:
        by_aoi_aoi.setdefault(aoi_of(p), []).append(p)
    for code in sorted(set(by_aoi_aoi) | set(by_aoi_obs)):
        tier = TIER.get(code, 2)
        rec = {"aoi": code, "name": NAMES.get(code, "?"), "tier": tier, "aoi_files": [p.name for p in by_aoi_aoi.get(code, [])], "obs_files": [p.name for p in by_aoi_obs.get(code, [])]}
        if tier == 3 or not by_aoi_aoi.get(code):
            rec["status"] = "excluded (tier 3: no product released)" if tier == 3 else "no AOI polygon"
            out["aois"][code] = rec; continue
        uni = active & V._rasterise_polys_to_grid(by_aoi_aoi[code], s["x"], s["y"], cfg.epsg, s["dx"], s["dy"])
        truth = V._rasterise_polys_to_grid(by_aoi_obs.get(code, []), s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]) if by_aoi_obs.get(code) else np.zeros_like(uni)
        rec["universe_km2"] = float(uni.sum() * A); rec["observed_km2"] = float((truth & uni).sum() * A)
        rec["modelled_km2_h_gt_0p10"] = float(((hmax > 0.10) & uni).sum() * A)
        rec["modelled_km2_by_threshold"] = {f"h>{t:.2f}m": float(((hmax > t) & uni).sum() * A) for t in THR}
        rec["peak_hmax_m"] = float(np.nanmax(np.where(uni, hmax, np.nan))) if uni.any() else None
        if tier == 1:
            sweep = {}
            for t in THR:
                c = V._contingency_full(hmax > t, truth, uni)
                c["skill"] = ss.skill_scores(c["tp"], c["fp"], c["fn"], c["tn"]); sweep[f"h>{t:.2f}m"] = c
            best = max(sweep, key=lambda k: sweep[k]["csi"] if sweep[k]["csi"] == sweep[k]["csi"] else -1)
            rec["strict_threshold_sweep"] = sweep; rec["csi_star"] = {"threshold": best, "csi": sweep[best]["csi"], "bias": sweep[best]["bias"]}
            mw = hmax > 0.10
            rec["fuzzy_at_h_gt_0p10m"] = {f"r={r}": V._contingency_full(V._dilate(mw, r), V._dilate(truth, r), uni) for r in (0, 1, 2, 3)}
            rec["fuzzy_model_oriented_r1"] = V._contingency_full(mw, V._dilate(truth, 1), uni)
            rec["fuzzy_obs_oriented_r1"] = V._contingency_full(V._dilate(mw, 1), truth, uni)
            rec["status"] = "scored (tier 1)"
        else:
            rec["status"] = "km² only (tier 2: post-event optical trace)"
        out["aois"][code] = rec
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    for code, r in out["aois"].items():
        if r.get("tier") == 1 and "strict_threshold_sweep" in r:
            c = r["strict_threshold_sweep"]["h>0.10m"]
            print(f"AOI{code} {r['name']:14s} tier 1: CSI {c['csi']:.3f} HR {c['hr']:.3f} FAR {c['far']:.3f} B {c['bias']:.2f} GSS {c['gss']:.3f}; CSI* {r['csi_star']['csi']:.3f} at {r['csi_star']['threshold']}; "
                  f"SEDI {c['skill']['sedi']:.3f} PSS {c['skill']['pss']:.3f}; obs {r['observed_km2']:.2f} km², modelled {r['modelled_km2_h_gt_0p10']:.2f} km² of {r['universe_km2']:.1f}")
        elif r.get("tier") == 2:
            print(f"AOI{code} {r['name']:14s} tier 2: observed {r.get('observed_km2', float('nan')):.3f} km² vs modelled {r.get('modelled_km2_h_gt_0p10', float('nan')):.3f} km² (universe {r.get('universe_km2', float('nan')):.1f} km², peak hmax {r.get('peak_hmax_m')})")
        else:
            print(f"AOI{code} {r['name']:14s} {r.get('status')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
