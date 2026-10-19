"""CODE-13 Part B — EMSR933 Crete rebuild with the v1.4 coastal set-up (grid, dep, mask, subgrid; NO forcing,
NO run): prepare_coastal_exclusion -> render_build_yml(exclude_mask) minus the precipitation step -> hydromt
build -> water-level boundary points along the coastal ring -> QC numbers (crete_build_qc.py).

Usage: python -I crete_rebuild_v14.py --repo <worktree> --work D:/ELKAK/implementation/emsr933_crete/buildqc_v14
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--config", default="skill/examples/emsr933_crete.yaml")
    ap.add_argument("--catalog", default="D:/ELKAK/implementation/emsr933_crete/data_catalog.yml")
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts"))
    from _common import load_config
    import build_model

    a.work.mkdir(parents=True, exist_ok=True)
    cfg = load_config(["--config", str(a.repo / a.config)])
    assert cfg.harness_version == "v1.4", cfg.harness_version
    t0 = time.time(); utc0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prep = build_model.prepare_coastal_exclusion(cfg, a.work, Path(a.catalog))
    t_prep = time.time() - t0
    yml = build_model.render_build_yml(cfg, exclude_mask=prep["exclude_mask"])
    yml_build = re.sub(r"\nsetup_precip_forcing_from_grid:\n(  .*\n?)+", "\n", yml)      # Part B/C: no forcing
    (a.work / "sfincs_build_full.yml").write_text(yml, encoding="utf-8")
    (a.work / "sfincs_build_qc.yml").write_text(yml_build, encoding="utf-8")
    model = a.work / "model"
    model.mkdir(exist_ok=True)
    t1 = time.time()
    res = subprocess.run([cfg.env["hydromt"], "build", "sfincs", str(model), "-i", str(a.work / "sfincs_build_qc.yml"),
                          "-d", a.catalog, "--fo", "-vv"], capture_output=True, text=True)
    (a.work / "hydromt_build.log").write_text(res.stdout + res.stderr, encoding="utf-8")
    t_build = time.time() - t1
    if res.returncode != 0:
        print(res.stdout[-3000:], res.stderr[-3000:]); return 1
    n_bnd = build_model.inject_waterlevel_bnd(cfg, model)
    rep = {"utc_start": utc0, "utc_end": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "config": a.config,
           "harness_version": cfg.harness_version, "coastal_prep": prep, "prep_wall_s": round(t_prep, 1), "hydromt_build_wall_s": round(t_build, 1),
           "n_bnd_points": int(n_bnd), "model_dir": str(model), "subgrid_MB": round((model / "sfincs_subgrid.nc").stat().st_size / 1e6, 1)}
    (a.work / "rebuild_v14.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "coastal_prep"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
