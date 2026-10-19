"""Phase 1 of the harness-v1.4 re-run (GO-C execution order, 2026-10-19): Strymonas, Mandra, Pineios —
baselines + canonical enhanced, in the MANIFEST order (Strymonas pair first).

Per run, in order:
  1. run config = the committed example YAML + `harness_version: v1.4` + a local work dir
     (`D:/ELKAK/implementation/v14/<run>`); written to reproduction/v14_rerun/configs/<run>.yaml as the record.
     The Pineios grid-matched baseline has no example: it is derived from emsr692_pineios_enhanced.yaml with every
     enhanced block disabled and ERA5 rain, and its v1.3 rendering is checked against the frozen record
     D:/ELKAK/reproduction/grid_matched_baseline/work/sfincs_build.yml.
  2. data dir seeded from the published run's data dir — directory junctions for the static inputs (DEM, WorldCover,
     EMS polygons, extracted ERA5/GloFAS) and copies of the small per-event files (raw GloFAS, IMERG + .raw.nc,
     ERA5 raw zip is NOT copied so prep_inputs does not extract into the junction). No download. The published
     directories are never written to.
  3. pipeline steps 06 (IMERG: already present -> skip; 06b bias correction re-derived from .raw.nc), 07 prep_inputs,
     08 prep_cn_raster, 09 prep_q_at_outlets, 10 build_model (v1.4: D4 prep + hydromt + D5 alignment + D2 bnd),
     11 run_sfincs; each timed.
  4. after the build: the event's exclusion GeoTIFF (v1.4 open_sea_mask.tif ∪ WorldCover 80) via
     validation/eval_exclusion.py, cross-checked against the published model's gis (symmetric difference recorded);
     the published v1.3 output is re-scored in the background (published mask and new mask) while SFINCS runs.
  5. after SFINCS: v1.4 output scored with the new mask; quick-look PNG; timing JSON.
Usage: python -I phase1.py --repo <worktree> [--runs strymonas_enhanced,...] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

V14_ROOT = Path("D:/ELKAK/implementation/v14")
IMPL = Path("D:/ELKAK/implementation")
JUNCTION_DIRS = ("copdem30", "esa_worldcover", "ems_polygons", "era5_extracted", "glofas_extracted")

RUNS = [
    {"run": "strymonas_enhanced", "event": "strymonas", "kind": "enhanced", "example": "emsr122_strymonas_enhanced.yaml",
     "seed_data": IMPL / "emsr122_sfincs_v3" / "data", "seed_slug": "strymonas",
     "published_work": IMPL / "emsr122_sfincs_v3", "published_model": IMPL / "emsr122_sfincs_v3" / "model",
     "manifest_row": 1, "published_wallclock_s": 109.2},
    {"run": "strymonas_baseline", "event": "strymonas", "kind": "baseline", "example": "emsr122_strymonas.yaml",
     "seed_data": IMPL / "emsr122_sfincs" / "data", "seed_slug": "emsr122",
     "published_work": IMPL / "emsr122_sfincs", "published_model": IMPL / "emsr122_sfincs" / "model",
     "manifest_row": 2, "published_wallclock_s": 256.5},
    {"run": "mandra_enhanced", "event": "mandra", "kind": "enhanced", "example": "emsr257_mandra_enhanced.yaml",
     "seed_data": IMPL / "mandra_sfincs_enhanced" / "data", "seed_slug": "mandra",
     "published_work": IMPL / "mandra_sfincs_enhanced", "published_model": IMPL / "mandra_sfincs_enhanced" / "model",
     "manifest_row": 3, "published_wallclock_s": 1097.8},
    {"run": "mandra_baseline", "event": "mandra", "kind": "baseline", "example": "emsr257_mandra.yaml",
     "seed_data": IMPL / "mandra_sfincs" / "data", "seed_slug": "mandra",
     "published_work": IMPL / "mandra_sfincs", "published_model": IMPL / "mandra_sfincs" / "model",
     "manifest_row": 4, "published_wallclock_s": 546.6},
    {"run": "pineios_enhanced", "event": "pineios", "kind": "enhanced", "example": "emsr692_pineios_enhanced.yaml",
     "seed_data": IMPL / "pineios_sfincs_enhanced" / "data", "seed_slug": "pineios",
     "published_work": IMPL / "pineios_sfincs_enhanced", "published_model": IMPL / "pineios_sfincs_enhanced" / "model",
     "manifest_row": 5, "published_wallclock_s": 1456.2},
    {"run": "pineios_baseline_gridmatched", "event": "pineios", "kind": "baseline", "example": "emsr692_pineios_enhanced.yaml",
     "derive_gridmatched_baseline": True,
     "seed_data": IMPL / "pineios_sfincs_enhanced" / "data", "seed_slug": "pineios",
     "published_work": None, "published_data": IMPL / "pineios_sfincs_enhanced" / "data",
     "published_model": Path("D:/ELKAK/reproduction/grid_matched_baseline/model"),
     "published_build_yml": Path("D:/ELKAK/reproduction/grid_matched_baseline/work/sfincs_build.yml"),
     "manifest_row": 6, "published_wallclock_s": 1006.4},
]


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str):
    print(f"[{utc()}] {msg}", flush=True)


def junction(link: Path, target: Path):
    import _winapi
    if link.exists() or link.is_symlink():
        return "exists"
    _winapi.CreateJunction(str(target), str(link))
    return "created"


# ------------------------------------------------------------------------------------------- 1. run configs
def make_config(repo: Path, r: dict, out_dir: Path) -> tuple[Path, dict]:
    import yaml
    src = repo / "skill" / "examples" / r["example"]
    raw = yaml.safe_load(src.read_text(encoding="utf-8"))
    note = {"derived_from": f"skill/examples/{r['example']}", "changes": []}
    raw["harness_version"] = "v1.4"; note["changes"].append("harness_version: v1.4")
    work = V14_ROOT / r["run"]
    raw["paths"]["work_dir"] = str(work).replace("\\", "/")
    raw["paths"]["deliverable_dir"] = str(work / "deliverable").replace("\\", "/")
    raw["paths"]["zip_dir"] = str(work).replace("\\", "/")
    note["changes"].append(f"paths.work_dir/deliverable_dir/zip_dir -> {work}")
    if r.get("derive_gridmatched_baseline"):
        raw["rain_source"] = "era5_hourly"
        for blk in ("coastal_bc", "wind_pressure", "rain_bias_correct", "infiltration", "upstream_q"):
            if blk in raw:
                raw[blk]["enabled"] = False
        raw["event"]["name"] = "Pineios"; raw["event"]["slug"] = "pineios"
        note["changes"].append("grid-matched baseline (MANIFEST row 6): rain_source era5_hourly; coastal_bc, wind_pressure, "
                               "rain_bias_correct, infiltration, upstream_q disabled; window/bbox/grid of the enhanced run kept")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{r['run']}.yaml"
    header = (f"# Harness v1.4 re-run config — Phase 1 (GO-C, 2026-10-19). Generated by reproduction/v14_rerun/scripts/phase1.py\n"
              f"# from {note['derived_from']}: " + "; ".join(note["changes"]) + "\n")
    out.write_text(header + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return out, note


def check_gridmatched_render(repo: Path, cfg_path: Path, record: Path) -> dict:
    """The derived baseline must render (under v1.3) the frozen grid-matched build file."""
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    from _common import load_config
    import build_model
    cfg = load_config(["--config", str(cfg_path)])
    cfg.raw["harness_version"] = "v1.3"
    norm = lambda s: re.sub(r"reclass_table: .*", "reclass_table: X", s).strip()  # noqa: E731
    mine = norm(build_model.render_build_yml(cfg)); rec = norm(record.read_text(encoding="utf-8"))
    cfg.raw["harness_version"] = "v1.4"
    return {"record": str(record), "identical_under_v13": mine == rec,
            "diff_lines": [] if mine == rec else [ln for ln in mine.splitlines() if ln not in rec.splitlines()] + ["--- record ---"] + [ln for ln in rec.splitlines() if ln not in mine.splitlines()]}


# ------------------------------------------------------------------------------------------- 2. seeding
def seed(r: dict, work: Path, slug: str) -> dict:
    data = work / "data"; data.mkdir(parents=True, exist_ok=True)
    src = r["seed_data"]; s0 = r["seed_slug"]
    rep = {"from": str(src), "junctions": {}, "copied": [], "skipped": []}
    for d in JUNCTION_DIRS:
        if (src / d).exists():
            rep["junctions"][d] = junction(data / d, src / d)
    files = {f"glofas_{s0}.nc": f"glofas_{slug}.nc", f"imerg_{s0}.nc": f"imerg_{slug}.nc", f"imerg_{s0}.raw.nc": f"imerg_{slug}.raw.nc",
             f"era5_{s0}.nc": f"era5_{slug}.nc"}
    for a, b in files.items():
        if (src / a).exists():
            if not (data / b).exists():
                shutil.copy2(src / a, data / b); rep["copied"].append(f"{a} -> {b}")
            else:
                rep["skipped"].append(b)
    return rep


# ------------------------------------------------------------------------------------------- 3. pipeline
def run_step(py: str, repo: Path, cfg: Path, step: int, logf: Path, env: dict) -> dict:
    t0 = time.time(); u0 = utc()
    with open(logf, "a", encoding="utf-8") as fh:
        fh.write(f"\n##### step {step:02d} start {u0}\n"); fh.flush()
        res = subprocess.run([py, str(repo / "skill" / "scripts" / "run_pipeline.py"), "--config", str(cfg), "--only", str(step)],
                             stdout=fh, stderr=subprocess.STDOUT, env=env)
    rec = {"step": step, "start_utc": u0, "end_utc": utc(), "wall_s": round(time.time() - t0, 1), "exit": res.returncode}
    if res.returncode != 0:
        raise RuntimeError(f"step {step} failed (exit {res.returncode}); see {logf}")
    return rec


def sfincs_total_time(model: Path):
    for name in ("sfincs_log.txt", "sfincs.log"):
        p = model / name
        if p.exists():
            m = re.search(r"Total time\s*:\s*([0-9.]+)", p.read_text(errors="replace"))
            if m:
                return float(m.group(1))
    return None


# ------------------------------------------------------------------------------------------- 4. exclusion + scoring
def make_exclusion(py: str, repo: Path, r: dict, work: Path, masks: Path, env: dict) -> dict:
    out = masks / f"{r['event']}_exclusion.tif"; js = masks / f"{r['event']}_exclusion.json"
    sea_tif = work / "open_sea_mask.tif"
    wc = work / "data" / "esa_worldcover" / "esa_worldcover_2021.vrt"
    gis = r["published_model"] / "gis"
    if out.exists():
        # second run of the same event: the build's open-sea mask must equal the one already used
        import rasterio
        import numpy as np
        with rasterio.open(sea_tif) as a:
            sea = a.read(1) == 1
        prev = json.loads(js.read_text(encoding="utf-8"))
        with rasterio.open(prev["open_sea_source"]) as b:
            sea_prev = b.read(1) == 1
        same = sea.shape == sea_prev.shape and bool((sea == sea_prev).all())
        diff = int((sea ^ sea_prev).sum()) if sea.shape == sea_prev.shape else -1
        return {"reused": str(out), "open_sea_identical_to_first_build": same, "symmetric_difference_cells": diff}
    cmd = [py, "-I", str(repo / "validation" / "eval_exclusion.py"), "--open-sea-tif", str(sea_tif), "--gis", str(gis),
           "--worldcover", str(wc), "--out", str(out), "--out-json", str(js), "--allow-diff"]
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if res.returncode != 0:
        raise RuntimeError("eval_exclusion failed:\n" + res.stdout[-2000:] + res.stderr[-2000:])
    return json.loads(js.read_text(encoding="utf-8"))


def validate_cmd(py: str, repo: Path, cfg: Path, out_json: Path, exclusion: Path | None, work_override: Path | None, env: dict):
    e = dict(env)
    if work_override:
        e["SFINCS_WORK_DIR"] = str(work_override)
    cmd = [py, str(repo / "validation" / "validate_event_v2.py"), "--config", str(cfg), "--out-json", str(out_json)]
    if exclusion:
        cmd += ["--exclusion-tif", str(exclusion)]
    return cmd, e


def published_work_for(r: dict, scratch: Path) -> Path:
    """Work dir whose data/ and model/ are the published ones (junctions for the grid-matched baseline)."""
    if r.get("published_work"):
        return r["published_work"]
    w = scratch / r["run"]; w.mkdir(parents=True, exist_ok=True)
    junction(w / "data", r["published_data"]); junction(w / "model", r["published_model"])
    return w


# ------------------------------------------------------------------------------------------- main
def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--runs", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    from _common import _load_machine_override
    ov = _load_machine_override()
    py = ov["env"]["python"]
    env = dict(os.environ); env["GDAL_DATA"] = ov["env"].get("gdal_data", env.get("GDAL_DATA", ""))
    env["PYTHONIOENCODING"] = "utf-8"
    out_root = repo / "reproduction" / "v14_rerun"
    cfg_dir, res_dir, masks, ql = out_root / "configs", out_root / "results", out_root / "masks", out_root / "quicklook"
    for d in (cfg_dir, res_dir, masks, ql):
        d.mkdir(parents=True, exist_ok=True)
    scratch = V14_ROOT / "_rescoring"
    sel = [x for x in a.runs.split(",") if x]
    for r in RUNS:
        if sel and r["run"] not in sel:
            continue
        run = r["run"]; work = V14_ROOT / run
        rec_path = res_dir / f"{run}_record.json"
        rec = {"run": run, "event": r["event"], "kind": r["kind"], "manifest_row": r["manifest_row"], "work": str(work),
               "published_model": str(r["published_model"]), "published_wallclock_s": r["published_wallclock_s"],
               "start_utc": utc(), "steps": []}
        log(f"=== {run} ===")
        cfg_path, note = make_config(repo, r, cfg_dir); rec["config"] = str(cfg_path.relative_to(repo)); rec["config_note"] = note
        if r.get("derive_gridmatched_baseline"):
            rec["gridmatched_render_check"] = check_gridmatched_render(repo, cfg_path, r["published_build_yml"])
            log(f"grid-matched render check: {rec['gridmatched_render_check']['identical_under_v13']}")
        from _common import load_config
        cfg = load_config(["--config", str(cfg_path)])
        rec["seed"] = seed(r, work, cfg.event_slug)
        log(f"seeded {work}: junctions {rec['seed']['junctions']}, copied {rec['seed']['copied']}")
        if a.dry_run:
            rec_path.write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
            continue
        logf = work / "pipeline_v14.log"
        bg = []
        for step in (6, 7, 8, 9, 10, 11):
            st = run_step(py, repo, cfg_path, step, logf, env)
            rec["steps"].append(st)
            log(f"step {step:02d} done in {st['wall_s']} s")
            if step == 10:
                prep = work / "coastal_prep.json"
                rec["coastal_prep"] = json.loads(prep.read_text(encoding="utf-8")) if prep.exists() else None
                rec["exclusion"] = make_exclusion(py, repo, r, work, masks, env)
                log(f"exclusion: {rec['exclusion']}")
                excl = masks / f"{r['event']}_exclusion.tif"
                pw = published_work_for(r, scratch)
                ex_yaml = repo / "skill" / "examples" / r["example"]
                if r.get("derive_gridmatched_baseline"):
                    # the published grid-matched baseline has no v1.3 example: score it with the derived config
                    # (window/bbox/EMS identical to the enhanced example), v1.3 semantics do not enter the validator
                    ex_yaml = cfg_path
                for tag, ex in (("v13_publishedmask", None), ("v13_newmask", excl)):
                    oj = res_dir / f"{run}_{tag}.json"
                    cmd, e = validate_cmd(py, repo, ex_yaml, oj, ex, pw, env)
                    lf = open(res_dir / f"{run}_{tag}.log", "w", encoding="utf-8")
                    bg.append((tag, subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, env=e), lf, time.time()))
                log("v1.3 re-scoring started in the background (published mask + new mask)")
        model = work / "model"
        rec["sfincs_total_time_s"] = sfincs_total_time(model)
        excl = masks / f"{r['event']}_exclusion.tif"
        t0 = time.time()
        cmd, e = validate_cmd(py, repo, cfg_path, res_dir / f"{run}_v14_newmask.json", excl, None, env)
        with open(res_dir / f"{run}_v14_newmask.log", "w", encoding="utf-8") as lf:
            res = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, env=e)
        rec["validation_v14"] = {"exit": res.returncode, "wall_s": round(time.time() - t0, 1), "json": f"results/{run}_v14_newmask.json"}
        log(f"v1.4 validation done ({rec['validation_v14']['wall_s']} s, exit {res.returncode})")
        rec["rescoring_v13"] = {}
        for tag, p, lf, t0 in bg:
            rc = p.wait(); lf.close()
            rec["rescoring_v13"][tag] = {"exit": rc, "wall_s": round(time.time() - t0, 1), "json": f"results/{run}_{tag}.json"}
        log(f"v1.3 re-scoring finished: {rec['rescoring_v13']}")
        qcmd = [py, "-I", str(repo / "reproduction" / "v14_rerun" / "scripts" / "quicklook.py"), "--repo", str(repo), "--config", str(cfg_path),
                "--out", str(ql / f"{run}_v14_hmax.png"), "--metrics", str(res_dir / f"{run}_v14_newmask.json"), "--exclusion-tif", str(excl),
                "--title", f"{run} — harness v1.4, new evaluation mask"]
        q = subprocess.run(qcmd, capture_output=True, text=True, env=env)
        rec["quicklook"] = {"exit": q.returncode, "png": f"quicklook/{run}_v14_hmax.png", "err": q.stderr[-500:] if q.returncode else ""}
        rec["end_utc"] = utc()
        rec_path.write_text(json.dumps(rec, indent=2, default=str), encoding="utf-8")
        log(f"record written: {rec_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
