"""CODE-10 — regression check for the F2/F4 harness changes (rule 5).

Re-executes `validation/validate_event_v2.py` (worktree copy, i.e. WITH the F2 change, switch off)
on the two held-out canonical outputs and compares with the published records:

  Valencia EMSR773, 164-mm canonical re-run: work dir
      ELKAK2/NHESS/R1_verification/task_valencia_anchor/_scoring/v164  (model -> rerun_v164/model,
      data -> runs/valencia_emsr773/data)  vs  _scoring/score_v164.json (full validator output,
      2026-07-21) and reports/valencia_emsr773_metrics.json (condensed, 4 dp).
  Emilia-Romagna EMSR664, canonical run + full 8-AOI truth: scratch work dir with junctions
      model -> ELKAK2/NHESS/runs/emilia_emsr664/model, data -> R1_verification/task_emilia_aoi/data
      vs  task_emilia_aoi/_scoring/emilia_rescore.json and reports/emilia_emsr664_metrics.json.

Then, labelled DIAGNOSTIC and never written to reports/: Emilia with `ems.include_del_product: true`
(the EMSR664_AOI01_DEL_PRODUCT_v1 observedEventA layer that the published union never matched).

Usage (sfincs-viz python):
  python regression_f2f4.py --worktree D:/ELKAK/sfincs-mediterranean-floods/.worktrees/emsr933-crete \
      --scratch <scratch dir>  [--python <sfincs-viz python.exe>]
Writes <worktree>/reproduction/emsr933/regression_f2f4.json and prints a summary.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import yaml

R1 = Path("D:/ELKAK/ELKAK2/NHESS/R1_verification")
RUNS = Path("D:/ELKAK/ELKAK2/NHESS/runs")
THRESH = ("h>0.05m", "h>0.10m", "h>0.25m", "h>0.50m")


def sedi_pss(c: dict) -> tuple[float, float]:
    """Manuscript Eq. (10)/(11): H = TP/(TP+FN), F = FP/(FP+TN) (POFD)."""
    H = c["tp"] / (c["tp"] + c["fn"])
    F = c["fp"] / (c["fp"] + c["tn"])
    sedi = ((math.log(F) - math.log(H) - math.log(1 - F) + math.log(1 - H)) /
            (math.log(F) + math.log(H) + math.log(1 - F) + math.log(1 - H)))
    return sedi, H - F


def condensed(fresh: dict, slug: str, epsg: int) -> dict:
    """Rebuild the reports/*.json layout from a full validator output (4 dp metrics, 2 dp areas)."""
    v = fresh["validation"]
    sweep = {}
    for t in THRESH:
        c = dict(v["strict_threshold_sweep"][t])
        s, p = sedi_pss(c)
        row = {k: (round(c[k], 4) if isinstance(c[k], float) else c[k]) for k in
               ("tp", "fp", "fn", "tn", "csi", "hr", "far", "f1", "f2", "bias", "gss", "hss", "acc")}
        row["sedi"], row["pss"] = round(s, 4), round(p, 4)
        sweep[t] = row
    return {"event": slug, "epsg": epsg,
            "evaluation_area_km2": round(v["evaluation_area_km2"], 2),
            "observed_wet_km2": round(v["observed_wet_km2_strict"], 2),
            "n_obs_shp": v["n_ems_shps"], "strict_threshold_sweep": sweep}


def diff_dicts(a, b, path="") -> list[str]:
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}/{k}: only in {'published' if k in b else 'fresh'}")
            else:
                out += diff_dicts(a[k], b[k], f"{path}/{k}")
    elif a != b:
        out.append(f"{path}: fresh={a!r} published={b!r}")
    return out


def junction(link: Path, target: Path) -> None:
    if link.exists():
        return
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True,
                   capture_output=True)


def run_validator(py: str, worktree: Path, cfg_path: Path, out_json: Path) -> str:
    env = dict(os.environ)
    env.setdefault("GDAL_DATA", str(Path(py).parent / "Library" / "share" / "gdal"))
    r = subprocess.run([py, str(worktree / "validation" / "validate_event_v2.py"),
                        "--config", str(cfg_path), "--out-json", str(out_json)],
                       capture_output=True, text=True, env=env, cwd=str(worktree))
    if r.returncode != 0:
        sys.exit(f"validator failed for {cfg_path}:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", required=True, type=Path)
    ap.add_argument("--scratch", required=True, type=Path)
    ap.add_argument("--python", default=sys.executable)
    a = ap.parse_args()
    wt, sc = a.worktree, a.scratch
    sc.mkdir(parents=True, exist_ok=True)
    rep = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "validator": str(wt / "validation" / "validate_event_v2.py"), "events": {}}

    # ---- Valencia: existing symlinked scoring dir from the 2026-07-21 re-anchor ----------------
    cfg_v = yaml.safe_load((R1 / "task_valencia_anchor/_scoring/cfg_v164.yaml").read_text(encoding="utf-8"))
    cfg_v_path = sc / "cfg_valencia_v164.yaml"
    cfg_v_path.write_text(yaml.safe_dump(cfg_v, sort_keys=False), encoding="utf-8")
    fresh_v_path = sc / "valencia_fresh.json"
    log_v = run_validator(a.python, wt, cfg_v_path, fresh_v_path)
    fresh_v = json.loads(fresh_v_path.read_text(encoding="utf-8"))
    pub_full_v = json.loads((R1 / "task_valencia_anchor/_scoring/score_v164.json").read_text(encoding="utf-8"))
    pub_cond_v = json.loads((wt / "reports/valencia_emsr773_metrics.json").read_text(encoding="utf-8"))
    d_full = diff_dicts(fresh_v["validation"], pub_full_v["validation"])
    cond_v = condensed(fresh_v, "valencia_emsr773", int(cfg_v["crs"]["epsg"]))
    d_cond = diff_dicts(cond_v, pub_cond_v)
    rep["events"]["valencia_emsr773"] = {
        "config": str(cfg_v_path), "work_dir": cfg_v["paths"]["work_dir"], "fresh_json": str(fresh_v_path),
        "validator_stdout_tail": log_v.strip().splitlines()[-4:],
        "full_block_vs_score_v164": "IDENTICAL" if not d_full else d_full,
        "condensed_vs_reports_json": "IDENTICAL" if not d_cond else d_cond,
        "csi_0p10": fresh_v["validation"]["strict_threshold_sweep"]["h>0.10m"]["csi"],
        "n_ems_shps": fresh_v["validation"]["n_ems_shps"]}

    # ---- Emilia: scratch work dir with junctions to the canonical model + 8-AOI truth ----------
    ew = sc / "emilia_work"
    ew.mkdir(exist_ok=True)
    junction(ew / "model", RUNS / "emilia_emsr664/model")
    junction(ew / "data", R1 / "task_emilia_aoi/data")
    cfg_e = yaml.safe_load((R1 / "task_emilia_aoi/emilia_task.yaml").read_text(encoding="utf-8"))
    cfg_e["paths"]["work_dir"] = str(ew)
    cfg_e["paths"]["deliverable_dir"] = str(ew / "deliverable")
    cfg_e_path = sc / "cfg_emilia_8aoi.yaml"
    cfg_e_path.write_text(yaml.safe_dump(cfg_e, sort_keys=False), encoding="utf-8")
    fresh_e_path = sc / "emilia_fresh.json"
    log_e = run_validator(a.python, wt, cfg_e_path, fresh_e_path)
    fresh_e = json.loads(fresh_e_path.read_text(encoding="utf-8"))
    pub_cond_e = json.loads((wt / "reports/emilia_emsr664_metrics.json").read_text(encoding="utf-8"))
    cond_e = condensed(fresh_e, "emilia_emsr664", int(cfg_e["crs"]["epsg"]))
    d_cond_e = diff_dicts(cond_e, pub_cond_e)
    resc = json.loads((R1 / "task_emilia_aoi/_scoring/emilia_rescore.json").read_text(encoding="utf-8"))
    # the 8-AOI entry is the one whose n_obs_shp matches the published report
    tag8 = [k for k, v in resc.items() if isinstance(v, dict) and v.get("n_obs_shp") == pub_cond_e["n_obs_shp"]]
    d_resc = None
    if tag8:
        r8 = resc[tag8[0]]
        d_resc = []
        for t in ("h>0.10m", "h>0.50m"):
            for k in ("tp", "fp", "fn", "tn"):
                if r8[t][k] != fresh_e["validation"]["strict_threshold_sweep"][t][k]:
                    d_resc.append(f"{t}/{k}: fresh={fresh_e['validation']['strict_threshold_sweep'][t][k]} rescore={r8[t][k]}")
    rep["events"]["emilia_emsr664"] = {
        "config": str(cfg_e_path), "work_dir": str(ew), "fresh_json": str(fresh_e_path),
        "validator_stdout_tail": log_e.strip().splitlines()[-4:],
        "condensed_vs_reports_json": "IDENTICAL" if not d_cond_e else d_cond_e,
        "contingency_vs_emilia_rescore": ("IDENTICAL" if d_resc == [] else d_resc) if tag8 else "rescore tag not found",
        "rescore_tag": tag8, "csi_0p10": fresh_e["validation"]["strict_threshold_sweep"]["h>0.10m"]["csi"],
        "n_ems_shps": fresh_e["validation"]["n_ems_shps"]}

    # ---- DIAGNOSTIC only: Emilia with the DEL_PRODUCT switch on -------------------------------
    cfg_d = dict(cfg_e)
    cfg_d["ems"] = dict(cfg_e.get("ems") or {}, include_del_product=True)
    cfg_d_path = sc / "cfg_emilia_8aoi_DIAGNOSTIC_delproduct.yaml"
    cfg_d_path.write_text(yaml.safe_dump(cfg_d, sort_keys=False), encoding="utf-8")
    fresh_d_path = sc / "emilia_DIAGNOSTIC_delproduct.json"
    run_validator(a.python, wt, cfg_d_path, fresh_d_path)
    fd = json.loads(fresh_d_path.read_text(encoding="utf-8"))["validation"]
    fe = fresh_e["validation"]
    rep["diagnostic_emilia_include_del_product"] = {
        "note": "NOT canonical. Effect of counting EMSR664_AOI01_DEL_PRODUCT_v1 observedEventA in the truth union.",
        "n_ems_shps": [fe["n_ems_shps"], fd["n_ems_shps"]],
        "observed_wet_km2_strict": [fe["observed_wet_km2_strict"], fd["observed_wet_km2_strict"]],
        "csi_0p10": [fe["strict_threshold_sweep"]["h>0.10m"]["csi"], fd["strict_threshold_sweep"]["h>0.10m"]["csi"]],
        "hr_0p10": [fe["strict_threshold_sweep"]["h>0.10m"]["hr"], fd["strict_threshold_sweep"]["h>0.10m"]["hr"]],
        "contingency_0p10": [fe["strict_threshold_sweep"]["h>0.10m"], fd["strict_threshold_sweep"]["h>0.10m"]]}

    out = wt / "reproduction/emsr933/regression_f2f4.json"
    out.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    for ev, r in rep["events"].items():
        print(f"{ev}: n_ems_shps={r['n_ems_shps']} CSI@0.10={r['csi_0p10']:.6f}")
        for k in ("full_block_vs_score_v164", "condensed_vs_reports_json", "contingency_vs_emilia_rescore"):
            if k in r:
                print(f"   {k}: {r[k] if isinstance(r[k], str) else str(r[k])[:600]}")
    dg = rep["diagnostic_emilia_include_del_product"]
    print(f"DIAGNOSTIC emilia include_del_product: n_shp {dg['n_ems_shps']}, obs km2 {dg['observed_wet_km2_strict']}, "
          f"CSI {dg['csi_0p10']}, HR {dg['hr_0p10']}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
