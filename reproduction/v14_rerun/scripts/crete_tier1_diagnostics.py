"""CODE-16 B (2026-10-21) — Crete (EMSR933) diagnostics on the tier-1 block (rule_ledger.md §8 item 3: AOI03 Tzermiado is the
only scored block; no all-AOI union score). Post-processing only, no SFINCS run.

The Phase-4 truth-buffer and time-matched files for Crete were computed on the union of every released package (the generic
Phase-4 scripts know no tiers); Table S3 needs them on the tier-1 block, and Table S6 needs the evaluation-universe variants of
that block. For each run given (default: the canonical crete_canonical_r2on):
  * universe = AOI03 polygons (all AOI03 areaOfInterestA files) ∩ active minus the v1.4 exclusion — as crete_tier_scores.py;
    truth = the AOI03 delineation packages selected by the validator (_select_obs_shps with include_del_product);
  * truth buffer −20 / 0 / +20 m: truth_buffer_scores.buffer_sweep (the published raster-domain procedure); the 0 m CSI must
    equal the tier-1 strict CSI of phase5/<run>_tiers.json (checked);
  * time-matched: hmax up to the earliest and the latest acquisition of the AOI03 packages (time_matched_scores helpers);
  * universe variants for S6: AOI03 (must equal the tier-1 record, checked), AOI03 dilated / eroded by 1 km (round(1000/dx)
    cells, square structuring element, as table_s3_v14.py). The 'active mask only' variant is not defined for Crete: truth
    exists only inside the AOIs and §8-3 scores the tier-1 block only.
Usage: python -I crete_tier1_diagnostics.py --repo <worktree> [--runs crete_canonical_r2on,...] [--out-json .../code16/crete_tier1_diagnostics.json]
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

AOI = "03"
THR = 0.10


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--runs", default="crete_canonical_r2on")
    ap.add_argument("--out-json", type=Path, default=None)
    a = ap.parse_args()
    repo = a.repo.resolve()
    R = repo / "reproduction" / "v14_rerun"
    sys.path.insert(0, str(repo / "skill" / "scripts")); sys.path.insert(0, str(repo / "validation")); sys.path.insert(0, str(Path(__file__).resolve().parent))
    os.environ.setdefault("GDAL_DATA", os.path.join(sys.prefix, "Library", "share", "gdal"))
    from _common import load_config
    from validate_event_v2 import _contingency_full, _dilate, _list_shps, _rasterise_polys_to_grid, _select_obs_shps, open_sfincs_light
    from eval_exclusion import read_mask_for_grid
    from truth_buffer_scores import buffer_sweep, load_geoms
    from time_matched_scores import product_acquisition, running_hmax_snapshots
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/crete_tier1_diagnostics.py",
           "rule": "rule_ledger.md §8 item 3 — tier 1 = AOI03 Tzermiado, the only scored block; no all-AOI union score", "threshold_m": THR, "runs": {}}
    for run in [x for x in a.runs.split(",") if x]:
        cfg = load_config(["--config", str(R / "configs" / f"{run}.yaml")])
        s = open_sfincs_light(cfg.paths["model_dir"])
        excl = read_mask_for_grid(R / "masks" / "crete_exclusion.tif", s)
        ems_dir = cfg.paths["data_dir"] / "ems_polygons"
        obs = [p for p in _select_obs_shps(ems_dir, include_del_product=bool(cfg.ems.get("include_del_product", False))) if re.search(rf"AOI{AOI}_", p.name)]
        aois = [p for p in _list_shps(ems_dir, ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"]) if re.search(rf"AOI{AOI}_", p.name)]
        active = (s["msk"] > 0) & ~excl
        A = s["cell_area_km2"]
        aoi_r = _rasterise_polys_to_grid(aois, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"])
        uni = active & aoi_r
        truth = _rasterise_polys_to_grid(obs, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"])
        zsmax = s["ds"]["zsmax"].max(dim="timemax").values
        hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
        wet = hmax > THR
        tiers = json.loads((R / "phase5" / f"{run}_tiers.json").read_text(encoding="utf-8"))["aois"][AOI]
        canon = tiers["strict_threshold_sweep"]["h>0.10m"]
        rec = {"run": run, "aoi_files": [p.name for p in aois], "obs_files": [p.name for p in obs], "universe_km2": float(uni.sum() * A), "observed_km2": float((truth & uni).sum() * A),
               "tiers_record": f"phase5/{run}_tiers.json aois[{AOI}]"}
        # ---- universe variants (S6)
        k = max(1, int(round(1000.0 / float(s["dx"]))))
        variants = [("AOI03 (tier-1 universe)", uni), ("AOI03 + 1 km", active & _dilate(aoi_r, k)), ("AOI03 − 1 km", active & ~_dilate(~aoi_r, k))]
        rec["universe_variants"] = []
        for i, (name, m) in enumerate(variants):
            c = _contingency_full(wet, truth & active, m)
            c["name"] = name; c["area_km2"] = float(m.sum() * A)
            if i == 0:
                c["equals_tier1_record"] = bool(all(c[kk] == canon[kk] for kk in ("tp", "fp", "fn", "tn")))
            rec["universe_variants"].append(c)
        rec["active_mask_only"] = "not defined for Crete (truth exists only inside the AOIs; §8-3 scores the tier-1 block only)"
        # ---- truth buffer (S3)
        sweep = buffer_sweep(wet, load_geoms(obs, cfg.epsg), uni, s)
        rec["truth_buffer"] = sweep
        rec["truth_buffer_zero_equals_tier1"] = bool(all(sweep["0"][kk] == canon[kk] for kk in ("tp", "fp", "fn", "tn")))
        # ---- time-matched (S3): hmax up to the earliest / latest acquisition of the AOI03 packages
        metas = [product_acquisition(p) for p in obs]
        acq = []
        for m in metas:
            if m["acq_utc"] is not None:
                acq.append(m["acq_utc"] + dt.timedelta(days=1) - dt.timedelta(seconds=1) if m["date_only"] else m["acq_utc"])
        rec["acquisitions"] = [{**{kk: (v.isoformat() if isinstance(v, dt.datetime) else v) for kk, v in m.items()}, "obs_shp": p.name} for m, p in zip(metas, obs)]
        tm = {"full": _contingency_full(wet, truth, uni)}
        if acq:
            t0, t1 = min(acq), max(acq)
            snap = running_hmax_snapshots(s["ds"], s["zb"], [t0, t1])
            tm["earliest_acq_utc"] = t0.isoformat(); tm["latest_acq_utc"] = t1.isoformat()
            tm["to_earliest"] = _contingency_full(snap[t0] > THR, truth, uni)
            tm["to_latest"] = _contingency_full(snap[t1] > THR, truth, uni)
        rec["time_matched"] = tm
        out["runs"][run] = rec
        print(f"{run}: universe {rec['universe_km2']:.2f} km², observed {rec['observed_km2']:.2f} km²; variants " +
              "; ".join(f"{v['name']} {v['area_km2']:.1f} km² CSI {v['csi']:.3f}" for v in rec["universe_variants"]) +
              f"; equals tier-1 {rec['universe_variants'][0]['equals_tier1_record']}; buffer " + " / ".join(f"{b} m {sweep[b]['csi']:.3f}" for b in sweep) +
              f" (0 m = tier 1: {rec['truth_buffer_zero_equals_tier1']}); time-matched full {tm['full']['csi']:.3f}" +
              (f", to earliest {tm['to_earliest']['csi']:.3f}, to latest {tm['to_latest']['csi']:.3f}" if acq else ""), flush=True)
        assert rec["universe_variants"][0]["equals_tier1_record"] and rec["truth_buffer_zero_equals_tier1"], "tier-1 consistency check failed"
    op = a.out_json or (R / "code16" / "crete_tier1_diagnostics.json")
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("wrote", op)
    return 0


if __name__ == "__main__":
    sys.exit(main())
