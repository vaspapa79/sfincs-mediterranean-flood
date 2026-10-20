"""CODE-14 D (2026-10-20) — MANIFEST row 16: the Mandra v3 post-hoc mask restriction (supplement S2 "Mandra v3", a counter-example:
"restricting the mask post-hoc to the area buffer plus Pateras corridor (213 km², editing the mask while keeping the index file)
made every metric worse (CSI = 0.083, HR = 0.775, B = 9.08)"), recreated on the harness-v1.4 Mandra build.

Procedure, as the published run: the v1.4 canonical Mandra model (`mandra_enhanced`, same 569 x 542 grid as the published v1/v3
models — checked) is copied; every cell the published v3 edit deactivated (`sfincs.msk.orig` > 0 and `sfincs.msk` == 0 in
`implementation/mandra_sfincs_v3/model`) is set to 0 in the v1.4 `sfincs.msk`, the index file and everything else are kept;
SFINCS is re-run; the output is scored with the v1.4 validator on the new mask. The published v3 output is re-scored on the
published and on the new mask for the v1.3 columns. Records: results/mandra_v3_maskrestrict_{record,v14_newmask,v13_publishedmask,
v13_newmask}.json. Usage: python -I mandra_v3_maskrestrict_v14.py --repo <worktree> [--no-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

V14 = Path("D:/ELKAK/implementation/v14")
PUB_V3 = Path("D:/ELKAK/implementation/mandra_sfincs_v3")
RUN = "mandra_v3_maskrestrict"
BASE = "mandra_enhanced"
PUBLISHED_TEXT = {"source": "NHESS supplement R5, S2 'Mandra: post-hoc mask restriction (a counter-example)' and Table S2 Mandra v3 row",
                  "active_km2": 213, "csi": 0.083, "hr": 0.775, "bias": 9.08}


def utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--no-run", action="store_true", help="prepare the model and the config only")
    a = ap.parse_args()
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    os.environ.setdefault("GDAL_DATA", os.path.join(sys.prefix, "Library", "share", "gdal"))
    import xarray as xr
    import yaml
    from hydromt_sfincs import utils
    from _common import _load_machine_override
    ov = _load_machine_override(); py = ov["env"]["python"]; exe = ov["env"]["sfincs_exe"]
    env = dict(os.environ); env["GDAL_DATA"] = ov["env"].get("gdal_data", env.get("GDAL_DATA", "")); env["PYTHONIOENCODING"] = "utf-8"
    R = repo / "reproduction" / "v14_rerun"; res = R / "results"; cfgs = R / "configs"; masks = R / "masks"
    work = V14 / RUN; model = work / "model"; base_model = V14 / BASE / "model"
    rec = {"run": RUN, "event": "mandra", "kind": "enhanced", "phase": 6, "group": "row16", "manifest_row": 16, "base_run": BASE, "harness_tag": "v1.4.1",
           "label": "MANIFEST row 16: Mandra v3 post-hoc mask restriction (published 213 km² edit applied to the v1.4 canonical build; index file kept)",
           "published_model": str(PUB_V3 / "model"), "published_text": PUBLISHED_TEXT, "published_wallclock_s": 1906.7, "work": str(work),
           "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip(), "start_utc": utc(), "steps": []}
    # ---- 1. model copy (no outputs), data junction
    work.mkdir(parents=True, exist_ok=True)
    if not model.exists():
        model.mkdir()
        for p in base_model.iterdir():
            if p.name in ("sfincs_map.nc", "sfincs_his.nc", "sfincs_log.txt", "sfincs.log"):
                continue
            (shutil.copytree if p.is_dir() else shutil.copy2)(p, model / p.name)
    if not (work / "data").exists():
        import _winapi
        _winapi.CreateJunction(str(V14 / BASE / "data"), str(work / "data"))
    # ---- 2. the published restriction on the v1.4 mask (same grid: checked)
    ds14 = xr.open_dataset(base_model / "sfincs_map.nc"); ds3 = xr.open_dataset(PUB_V3 / "model" / "sfincs_map.nc")
    shape = ds14["msk"].shape
    if shape != ds3["msk"].shape or not (np.allclose(ds14["x"].values, ds3["x"].values) and np.allclose(ds14["y"].values, ds3["y"].values)):
        raise SystemExit("grid mismatch between the v1.4 Mandra build and the published v3 model")
    ind14 = utils.read_binary_map_index(base_model / "sfincs.ind")
    msk14 = utils.read_binary_map(base_model / "sfincs.msk", ind14, shape, mv=0, dtype="u1")
    ind3 = utils.read_binary_map_index(PUB_V3 / "model" / "sfincs.ind")
    msk3 = utils.read_binary_map(PUB_V3 / "model" / "sfincs.msk", ind3, shape, mv=0, dtype="u1")
    orig3 = utils.read_binary_map(PUB_V3 / "model" / "sfincs.msk.orig", ind3, shape, mv=0, dtype="u1")
    deact = (orig3 > 0) & (msk3 == 0)
    new = msk14.copy(); new[deact] = 0
    cell_km2 = float(ds14["msk"].attrs.get("cell_km2", 0.05 * 0.05)) if False else 0.05 * 0.05
    rec["mask_edit"] = {"published_v3_deactivated_cells": int(deact.sum()), "v14_active_before": int((msk14 > 0).sum()), "v14_active_after": int((new > 0).sum()),
                        "v14_boundary_cells_before": int((msk14 == 2).sum()), "v14_boundary_cells_after": int((new == 2).sum()),
                        "v14_cells_deactivated_here": int(((msk14 > 0) & (new == 0)).sum()), "active_km2_before": float((msk14 > 0).sum() * cell_km2), "active_km2_after": float((new > 0).sum() * cell_km2),
                        "published_v3_active_km2": float((msk3 > 0).sum() * cell_km2), "index_file": "kept (v1.4 sfincs.ind)"}
    if not (model / "sfincs.msk.v14").exists():
        shutil.copy2(model / "sfincs.msk", model / "sfincs.msk.v14")
    utils.write_binary_map(model / "sfincs.msk", new, msk14, dtype="u1")
    print("mask edit:", rec["mask_edit"])
    # ---- 3. config record (paths -> this work dir)
    raw = yaml.safe_load((cfgs / f"{BASE}.yaml").read_text(encoding="utf-8"))
    for k in ("work_dir", "deliverable_dir", "zip_dir"):
        raw["paths"][k] = str(work if k != "deliverable_dir" else work / "deliverable").replace("\\", "/")
    cfg_path = cfgs / f"{RUN}.yaml"
    cfg_path.write_text(f"# Harness v1.4 record — Phase 6 (CODE-14, 2026-10-20): MANIFEST row 16 recreated on the v1.4 Mandra build; derived from configs/{BASE}.yaml "
                        f"by reproduction/v14_rerun/scripts/mandra_v3_maskrestrict_v14.py (post-build sfincs.msk edit, index file kept)\n" + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    rec["config"] = str(cfg_path.relative_to(repo))
    if a.no_run:
        (res / f"{RUN}_record.json").write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8"); return 0
    # ---- 4. SFINCS
    t0 = time.time(); u0 = utc()
    with open(model / "sfincs_run_stdout.txt", "w", encoding="utf-8") as fh:
        r = subprocess.run([exe], cwd=model, stdout=fh, stderr=subprocess.STDOUT)
    rec["steps"].append({"step": "sfincs", "start_utc": u0, "end_utc": utc(), "wall_s": round(time.time() - t0, 1), "exit": r.returncode})
    if r.returncode != 0 or not (model / "sfincs_map.nc").exists():
        raise SystemExit(f"SFINCS failed (exit {r.returncode})")
    import re
    for name in ("sfincs_log.txt", "sfincs.log"):
        if (model / name).exists():
            m = re.search(r"Total time\s*:\s*([0-9.]+)", (model / name).read_text(errors="replace"))
            if m:
                rec["sfincs_total_time_s"] = float(m.group(1)); break
    # ---- 5. scoring: v1.4 new mask; the published v3 output on the published and the new mask
    excl = masks / "mandra_exclusion.tif"
    val = repo / "validation" / "validate_event_v2.py"
    rec["validation_v14"] = {}
    t0 = time.time()
    with open(res / f"{RUN}_v14_newmask.log", "w", encoding="utf-8") as lf:
        rv = subprocess.run([py, str(val), "--config", str(cfg_path), "--out-json", str(res / f"{RUN}_v14_newmask.json"), "--exclusion-tif", str(excl)], stdout=lf, stderr=subprocess.STDOUT, env=env)
    rec["validation_v14"] = {"exit": rv.returncode, "wall_s": round(time.time() - t0, 1), "json": f"results/{RUN}_v14_newmask.json"}
    rec["rescoring_v13"] = {}
    ex_yaml = repo / "skill" / "examples" / "emsr257_mandra_enhanced.yaml"
    for tag, ex in (("v13_publishedmask", None), ("v13_newmask", excl)):
        e = dict(env); e["SFINCS_WORK_DIR"] = str(PUB_V3)
        cmd = [py, str(val), "--config", str(ex_yaml), "--out-json", str(res / f"{RUN}_{tag}.json")] + (["--exclusion-tif", str(ex)] if ex else [])
        t0 = time.time()
        with open(res / f"{RUN}_{tag}.log", "w", encoding="utf-8") as lf:
            rr = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, env=e)
        rec["rescoring_v13"][tag] = {"exit": rr.returncode, "wall_s": round(time.time() - t0, 1), "json": f"results/{RUN}_{tag}.json", "published_work": str(PUB_V3)}
    pm = res / f"{RUN}_v13_publishedmask.json"
    if pm.exists():
        s = json.loads(pm.read_text(encoding="utf-8"))["validation"]["strict_threshold_sweep"]["h>0.10m"]
        rec["published_record_check"] = {"published_text": PUBLISHED_TEXT, "rescored_published_mask": {k: s[k] for k in ("tp", "fp", "fn", "csi", "hr", "far", "bias")},
                                         "csi_matches_text_3dp": round(s["csi"], 3) == PUBLISHED_TEXT["csi"], "hr_matches_text_3dp": round(s["hr"], 3) == PUBLISHED_TEXT["hr"]}
    q = subprocess.run([py, "-I", str(R / "scripts" / "quicklook.py"), "--repo", str(repo), "--config", str(cfg_path), "--out", str(R / "quicklook" / f"{RUN}_v14_hmax.png"),
                        "--metrics", str(res / f"{RUN}_v14_newmask.json"), "--exclusion-tif", str(excl), "--title", f"{RUN} — harness v1.4.1 build + published v3 mask edit"], capture_output=True, text=True, env=env)
    rec["quicklook"] = {"exit": q.returncode, "png": f"quicklook/{RUN}_v14_hmax.png", "err": q.stderr[-500:] if q.returncode else ""}
    rec["end_utc"] = utc()
    (res / f"{RUN}_record.json").write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: rec[k] for k in ("mask_edit", "sfincs_total_time_s", "validation_v14", "rescoring_v13", "published_record_check") if k in rec}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
