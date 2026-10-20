"""CODE-14 D (2026-10-20) — Table S3 equivalent: evaluation-mask sensitivity of the canonical strict (hmax > 0.10 m) metrics
under harness v1.4, with the v1.4 mask as the reference. Post-processing only (no SFINCS run).

As the published `_mask_sensitivity.py` (reviewer objection #7; supplement Table S3): the canonical run per event is held
fixed and only the evaluation mask varies —
  1. active mask, no AOI restriction            (msk > 0)              minus the exclusion
  2. AOI-union (the v1.4 reference)             (msk > 0) & union(AOI) minus the exclusion     = the canonical v1.4 score
  3. AOI-union dilated by 1 km                  (msk > 0) & dilate(union, 1 km) minus the exclusion
  4. AOI-union eroded by 1 km                   (msk > 0) & erode(union, 1 km)  minus the exclusion
with the validator's own rasterisation, dilation (square structuring element, round(1000 / dx) cells) and contingency,
and the v1.4 exclusion (WorldCover 80 ∪ open sea) removed on both sides exactly as validate_event_v2.apply_exclusion does.
Variant 2 must reproduce the canonical v1.4 record (checked). Rasterisations are shared with the Phase-4 truth cache.

Usage: python -I table_s3_v14.py --repo <worktree> [--runs a,b,...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import numpy as np

EVENTS = [  # (label, canonical v1.4 run, published Table S3 row?)
    ("Pineios (EMSR692)", "pineios_enhanced", True),
    ("Mandra (EMSR257)", "mandra_enhanced", True),
    ("Strymonas (EMSR122)", "strymonas_enhanced_postD6", True),
    ("Valencia (EMSR773)", "valencia_enhanced_164", False),
    ("Emilia-R. (EMSR664)", "emilia_enhanced_8aoi", False),
]
THR = 0.10


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--runs", default="")
    ap.add_argument("--run-suffix", default="", help="e.g. _v141: score <run><suffix> records/configs when they exist")
    a = ap.parse_args()
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "skill" / "scripts")); sys.path.insert(0, str(repo / "validation")); sys.path.insert(0, str(Path(__file__).resolve().parent))
    os.environ.setdefault("GDAL_DATA", os.path.join(sys.prefix, "Library", "share", "gdal"))
    from _common import load_config
    from validate_event_v2 import _rasterise_polys_to_grid, _dilate, _contingency_full, _list_shps, _select_obs_shps, open_sfincs_light
    from eval_exclusion import read_mask_for_grid
    from truth_cache import cache_key, cached_bool
    R = repo / "reproduction" / "v14_rerun"
    sel = [x for x in a.runs.split(",") if x]
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "threshold_m": THR, "method": "validate_event_v2 rasterisation / _dilate / _contingency_full; exclusion removed on both sides; 1 km = round(1000/dx) cells, square structuring element", "events": []}
    md = ["| Event | Mask | Area (km²) | CSI | HR | FAR | B | GSS | TP / FP / FN | published S3 (CSI / HR / B) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for label, run0, in_s3 in EVENTS:
        run = run0 + a.run_suffix if (R / "configs" / f"{run0}{a.run_suffix}.yaml").exists() else run0
        if sel and run0 not in sel and run not in sel:
            continue
        cfg = load_config(["--config", str(R / "configs" / f"{run}.yaml")])
        s = open_sfincs_light(cfg.paths["model_dir"])
        excl = read_mask_for_grid(R / "masks" / f"{cfg.event_slug if cfg.event_slug != 'emilia_romagna' else 'emilia'}_exclusion.tif", s)
        ems_dir = cfg.paths["data_dir"] / "ems_polygons"
        obs = _select_obs_shps(ems_dir, include_del_product=bool(cfg.ems.get("include_del_product", False)))
        aois = _list_shps(ems_dir, ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"])
        cache_dir = R / "phase4" / "truth_buffer" / "_cache"
        ems_wet = cached_bool(cache_dir, cache_key(cfg.event_slug, s, obs, "plain_validator"), lambda: _rasterise_polys_to_grid(obs, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]))
        aoi_uni = cached_bool(cache_dir, cache_key(cfg.event_slug, s, aois, "aoi_union"), lambda: _rasterise_polys_to_grid(aois, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]))
        msk = s["msk"] > 0
        zsmax = s["ds"]["zsmax"].max(dim="timemax").values
        hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
        model_wet = hmax > THR
        k = max(1, int(round(1000.0 / float(s["dx"]))))
        ems_x = ems_wet & ~excl                                   # truth loses the excluded cells too (apply_exclusion)
        variants = [("Active mask (no AOI)", msk & ~excl), ("AOI-union (v1.4 reference)", msk & aoi_uni & ~excl),
                    ("AOI-union + 1 km", msk & _dilate(aoi_uni, k) & ~excl), ("AOI-union − 1 km", msk & ~_dilate(~aoi_uni, k) & ~excl)]
        canon = json.loads((R / "results" / f"{run}_v14_newmask.json").read_text(encoding="utf-8"))["validation"]["strict_threshold_sweep"]["h>0.10m"]
        ev = {"label": label, "run": run, "dx_m": float(s["dx"]), "one_km_cells": k, "n_obs_shps": len(obs), "n_aoi_shps": len(aois), "canonical_record": f"results/{run}_v14_newmask.json", "variants": []}
        for i, (name, mask) in enumerate(variants):
            c = _contingency_full(model_wet, ems_x, mask)
            c["area_km2"] = float(mask.sum() * s["cell_area_km2"]); c["name"] = name
            if i == 1:
                c["equals_canonical_record"] = bool(all(c[kk] == canon[kk] for kk in ("tp", "fp", "fn", "tn")))
            ev["variants"].append(c)
            md.append(f"| {label if i == 0 else ''} | {name} | {c['area_km2']:.0f} | {c['csi']:.3f} | {c['hr']:.3f} | {c['far']:.3f} | {c['bias']:.2f} | {c['gss']:.3f} | {c['tp']} / {c['fp']} / {c['fn']} | {'see supplement Table S3' if in_s3 else '— (not in S3)'} |")
            print(f"{run:28s} {name:28s} area {c['area_km2']:8.1f} km²  CSI {c['csi']:.3f} HR {c['hr']:.3f} FAR {c['far']:.3f} B {c['bias']:.2f}" + ("  <- canonical check " + str(c.get("equals_canonical_record")) if i == 1 else ""))
        out["events"].append(ev)
    od = R / "code14"; od.mkdir(parents=True, exist_ok=True)
    tag = a.run_suffix or ""
    (od / f"table_s3_v14{tag}.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    (od / f"table_s3_v14{tag}.md").write_text(f"# Table S3 equivalent — evaluation-mask sensitivity under harness v1.4{tag} (generated {out['utc']} by `scripts/table_s3_v14.py`)\n\n"
                                               "Canonical run per event held fixed; the mask varies as in the published `_mask_sensitivity.py`; the v1.4 exclusion (WorldCover 80 ∪ open sea) is removed from every variant on both sides; "
                                               "variant 2 equals the canonical v1.4 record (checked in the JSON).\n\n" + "\n".join(md) + "\n", encoding="utf-8")
    print("wrote", od / f"table_s3_v14{tag}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
