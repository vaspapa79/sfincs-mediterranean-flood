"""CODE-12 A1 regression — harness v1.3 (default) must write the SAME forcing files after the v1.4
code change as before it, for a published event.

Renders the build yml with build_model.render_build_yml (post-change code) and the data catalog
with prep_inputs.render_catalog, drops the (slow) setup_subgrid step, runs `hydromt build` into
--out, and compares every file with a --reference directory produced by the pre-change code
(same yml minus subgrid, same catalog). Byte comparison first; for netCDFs that differ in bytes the
values and attributes are compared as well (hydromt writes HDF5 files whose internal layout is not
deterministic between two runs of identical code — wind_2d.nc, see F5/CODE-12 notes).

Usage (sfincs-viz python, -I):
  regression_forcing_v13.py --repo <worktree> --config skill/examples/emsr692_pineios_enhanced.yaml
      --data-dir D:/ELKAK/implementation/pineios_sfincs_enhanced/data --out <dir> --reference <before-dir>
      --json <report.json>
"""
from __future__ import annotations

import argparse
import datetime as dt
import filecmp
import json
import re
import subprocess
import sys
from pathlib import Path


def nc_equal(a: Path, b: Path) -> dict:
    import numpy as np
    import xarray as xr
    da, db = xr.open_dataset(a, decode_times=False), xr.open_dataset(b, decode_times=False)
    out = {"variables": {}, "attrs_equal": da.attrs == db.attrs, "all_values_equal": True, "all_var_attrs_equal": True}
    for v in set(da.variables) | set(db.variables):
        if v not in da.variables or v not in db.variables:
            out["variables"][v] = "missing on one side"; out["all_values_equal"] = False; continue
        va, vb = da[v], db[v]
        if va.dtype.kind in "fiu":
            same = va.shape == vb.shape and bool(np.array_equal(va.values, vb.values, equal_nan=True))
        else:
            same = va.shape == vb.shape and bool((va.values == vb.values).all())
        out["variables"][v] = {"values_equal": same, "attrs_equal": va.attrs == vb.attrs}
        out["all_values_equal"] &= same
        out["all_var_attrs_equal"] &= (va.attrs == vb.attrs)
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--reference", required=True, type=Path)
    ap.add_argument("--json", required=True, type=Path)
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts"))
    from _common import load_config
    import build_model
    import prep_inputs

    t0 = dt.datetime.now(dt.timezone.utc)
    cfg = load_config(["--config", str(a.config)])
    yml = build_model.render_build_yml(cfg)
    yml_forcing = re.sub(r"\nsetup_subgrid:\n(  .*\n?)+", "\n", yml)
    cat = prep_inputs.render_catalog(cfg, a.data_dir.replace("\\", "/"))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "sfincs_build_full.yml").write_text(yml, encoding="utf-8")
    (a.out / "sfincs_build_forcing.yml").write_text(yml_forcing, encoding="utf-8")
    (a.out / "data_catalog.yml").write_text(cat, encoding="utf-8")
    model = a.out / "model"
    cmd = [cfg.env["hydromt"], "build", "sfincs", str(model), "-i", str(a.out / "sfincs_build_forcing.yml"),
           "-d", str(a.out / "data_catalog.yml"), "--fo", "-v"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    (a.out / "hydromt_build.log").write_text(res.stdout + res.stderr, encoding="utf-8")
    rep = {"utc": t0.strftime("%Y-%m-%dT%H:%M:%SZ"), "config": str(a.config), "harness_version": cfg.harness_version,
           "hydromt_rc": res.returncode, "reference_dir": str(a.reference), "out_dir": str(model), "files": {}}
    # yml / catalog identity with the pre-change renders stored next to the reference model
    for name, mine in (("before_forcing.yml", yml_forcing), ("catalog_before.yml", cat)):
        ref = a.reference.parent / name
        rep["files"][name] = {"text_identical": ref.read_text(encoding="utf-8") == mine if ref.exists() else None}
    for f in sorted(a.reference.iterdir()):
        if f.is_dir() or f.name == "hydromt.log":
            continue
        mine = model / f.name
        entry = {"exists": mine.exists()}
        if mine.exists():
            entry["byte_identical"] = filecmp.cmp(f, mine, shallow=False)
            if not entry["byte_identical"] and f.suffix == ".nc":
                entry["content"] = nc_equal(f, mine)
        rep["files"][f.name] = entry
    verdict_bytes = all(e.get("byte_identical") for n, e in rep["files"].items() if "byte_identical" in e)
    verdict_content = all(e.get("byte_identical") or (e.get("content", {}).get("all_values_equal") and
                                                     e.get("content", {}).get("all_var_attrs_equal") and
                                                     e.get("content", {}).get("attrs_equal"))
                          for n, e in rep["files"].items() if "byte_identical" in e)
    rep["verdict"] = {"all_files_byte_identical": verdict_bytes, "all_files_content_identical": verdict_content}
    a.json.parent.mkdir(parents=True, exist_ok=True)
    a.json.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep["verdict"]), "\n", json.dumps({k: v for k, v in rep["files"].items()}, indent=1)[:3000])
    return 0 if res.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
