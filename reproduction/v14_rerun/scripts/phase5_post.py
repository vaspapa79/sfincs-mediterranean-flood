"""Phase 5 post-processing (GO Phases 3-5, 2026-10-19) — Crete Stage 4 products from the finished Crete runs. No SFINCS run.

Per finished Crete run: tier scoring (crete_tier_scores.py -> phase5/<run>_tiers.json). Once the canonical run exists:
rainfall vs the NOA stations (crete_rain_vs_noa.py -> phase5/crete_rain_vs_noa.{json,csv,png}; raw = the canonical run's
imerg_crete.raw.nc, R2 = its imerg_crete.nc, ERA5 = its era5_crete.nc). Figures (cluster maps, rain series) come from phase4.py.
Usage: python -I phase5_post.py --repo <worktree> [--runs a,b]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

CRETE_RUNS = ["crete_baseline", "crete_canonical_r2on", "crete_sens_r2off", "crete_sens_anchor_224", "crete_sens_anchor_336", "crete_sens_anchor_582", "crete_sens_karst_q1914"]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--runs", default="")
    a = ap.parse_args()
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    from _common import _load_machine_override
    ov = _load_machine_override(); py = ov["env"]["python"]
    env = dict(os.environ); env["GDAL_DATA"] = ov["env"].get("gdal_data", env.get("GDAL_DATA", "")); env["PYTHONIOENCODING"] = "utf-8"
    R = repo / "reproduction" / "v14_rerun"; res, cfgs, masks, S = R / "results", R / "configs", R / "masks", R / "scripts"
    P5 = R / "phase5"; (P5 / "logs").mkdir(parents=True, exist_ok=True)
    sel = [x for x in a.runs.split(",") if x] or CRETE_RUNS
    man = {"utc_start": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "runs": {}}

    def run(cmd, logname):
        t0 = time.time()
        with open(P5 / "logs" / f"{logname}.log", "w", encoding="utf-8") as fh:
            r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env)
        return {"exit": r.returncode, "wall_s": round(time.time() - t0, 1)}

    for name in sel:
        rec_p = res / f"{name}_record.json"; cfg = cfgs / f"{name}.yaml"
        rec = json.loads(rec_p.read_text(encoding="utf-8")) if rec_p.exists() else None
        if not (rec and rec.get("end_utc") and cfg.exists()):
            man["runs"][name] = {"status": "not finished"}; print(f"{name}: not finished", flush=True); continue
        man["runs"][name] = {"tiers": run([py, "-I", str(S / "crete_tier_scores.py"), "--repo", str(repo), "--config", str(cfg), "--exclusion-tif", str(masks / "crete_exclusion.tif"),
                                           "--out-json", str(P5 / f"{name}_tiers.json")], f"{name}_tiers")}
        print(f"{name}: {man['runs'][name]}", flush=True)
    can = res / "crete_canonical_r2on_record.json"
    if can.exists() and json.loads(can.read_text(encoding="utf-8")).get("end_utc"):
        w = Path(json.loads(can.read_text(encoding="utf-8"))["work"]) / "data"
        man["rain_vs_noa"] = run([py, "-I", str(S / "crete_rain_vs_noa.py"), "--repo", str(repo), "--raw", str(w / "imerg_crete.raw.nc"), "--r2", str(w / "imerg_crete.nc"),
                                  "--era5", str(w / "era5_crete.nc"), "--out-json", str(P5 / "crete_rain_vs_noa.json")], "rain_vs_noa")
        print("rain vs NOA:", man["rain_vs_noa"], flush=True)
    man["utc_end"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (P5 / "phase5_manifest.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
