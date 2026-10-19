"""D6 test (iii) on an event: storecumprcp is a bookkeeping switch, not a physics change, for a run WITHOUT curve
numbers. The harness-v1.4 Mandra enhanced model of Phase 1 (CN off) is copied, `storecumprcp = 1` is added to
sfincs.inp, SFINCS is run, and the water-level fields are compared with the Phase-1 output (no scoring). If they are
not bit-identical, a replicate without the flag is run to separate SFINCS run-to-run differences from the flag.

Usage: python -I d6_invariance_event.py --model <Phase-1 model dir> --sfincs <sfincs.exe> --work <scratch> --out-json <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

SKIP = {"sfincs_map.nc", "sfincs_his.nc", "sfincs.log", "sfincs_log.txt", "hydromt.log", "sfincs_stdout.txt"}


def infiltration_type(inp_text: str) -> str:
    """SFINCS v2.3.0 selection order (sfincs_domain.f90:2054-2099): qinf > 0 -> 'con', qinffile -> 'c2d',
    scsfile -> 'cna', sefffile -> 'cnb', ... ; hydromt writes `qinf = 0.0` for runs without infiltration."""
    kv = {}
    for ln in inp_text.splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            kv[k.strip()] = v.strip()
    try:
        if float(kv.get("qinf", "0")) > 0:
            return "con"
    except ValueError:
        pass
    for key, t in (("qinffile", "c2d"), ("scsfile", "cna"), ("sefffile", "cnb"), ("psifile", "gai"), ("f0file", "hor")):
        if kv.get(key, "none") not in ("", "none"):
            return t
    return "none"


def copy_model(src: Path, dst: Path, extra_inp: str = ""):
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in src.iterdir():
        if f.is_file() and f.name not in SKIP:
            shutil.copy2(f, dst / f.name)
    if extra_inp:
        inp = dst / "sfincs.inp"
        inp.write_text(inp.read_text().rstrip() + "\n" + extra_inp + "\n")


def run(exe: str, model: Path) -> float:
    t0 = time.time()
    r = subprocess.run([exe], cwd=str(model), capture_output=True, text=True)
    (model / "sfincs_log.txt").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"SFINCS failed in {model}")
    return round(time.time() - t0, 1)


def compare(a: Path, b: Path) -> dict:
    import xarray as xr
    da, db = xr.open_dataset(a / "sfincs_map.nc"), xr.open_dataset(b / "sfincs_map.nc")
    out = {}
    for v in ("zs", "zsmax", "h", "hmax"):
        if v in da and v in db:
            x, y = da[v].values, db[v].values
            same_shape = x.shape == y.shape
            eq = same_shape and bool(np.array_equal(x, y, equal_nan=True))
            diff = np.nanmax(np.abs(x - y)) if same_shape else None
            out[v] = {"bit_identical": eq, "max_abs_diff_m": (None if diff is None else float(diff)),
                      "nan_pattern_identical": same_shape and bool(np.array_equal(np.isnan(x), np.isnan(y)))}
    out["extra_vars_in_b"] = sorted(set(db.data_vars) - set(da.data_vars))
    da.close(); db.close()
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--sfincs", required=True)
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    a = ap.parse_args()
    inp = (a.model / "sfincs.inp").read_text()
    rep = {"utc_start": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "reference_model": str(a.model),
           "reference_infiltration_type": infiltration_type(inp),
           "reference_has_storecumprcp": "storecumprcp" in inp}
    flag = a.work / "with_flag"
    copy_model(a.model, flag, "storecumprcp = 1")
    rep["with_flag_wall_s"] = run(a.sfincs, flag)
    rep["reference_vs_with_flag"] = compare(a.model, flag)
    if not all(v["bit_identical"] for k, v in rep["reference_vs_with_flag"].items() if isinstance(v, dict)):
        rep_dir = a.work / "replicate_no_flag"
        copy_model(a.model, rep_dir)
        rep["replicate_wall_s"] = run(a.sfincs, rep_dir)
        rep["reference_vs_replicate"] = compare(a.model, rep_dir)
        rep["replicate_vs_with_flag"] = compare(rep_dir, flag)
    rep["utc_end"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
