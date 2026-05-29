"""Run every pipeline step in order, with caching at the script level.

Usage:
  python scripts/run_pipeline.py --config examples/<event>.yaml
  python scripts/run_pipeline.py --config <event>.yaml --skip 5,6,7
  python scripts/run_pipeline.py --config <event>.yaml --only 9,10,11,12,13
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent

STEPS = [
    ("01", "download_ems.py"),
    ("02", "download_era5.py"),
    ("03", "download_glofas.py"),
    ("04", "download_dem.py"),
    ("05", "download_worldcover.py"),
    # IMERG (only runs if rain_source: imerg_half_hourly in YAML)
    ("06", "download_imerg.py"),
    ("07", "prep_inputs.py"),
    # Enhanced-forcing prep steps — no-ops if the corresponding config
    # section is disabled, so safe to keep in the default pipeline.
    ("08", "prep_cn_raster.py"),
    ("09", "prep_q_at_outlets.py"),
    ("10", "build_model.py"),
    ("11", "run_sfincs.py"),
    ("12", "fetch_basemap.py"),
    ("13", "qc_alignment.py"),
    ("14", "make_animation.py"),
    ("15", "make_mp4.py"),
    ("16", "package_deliverable.py"),
]


def parse_list(s: str | None) -> set[int]:
    if not s:
        return set()
    out = set()
    for tok in s.split(","):
        tok = tok.strip()
        if not tok:
            continue
        out.add(int(tok))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--skip", type=str, default="",
                        help="Comma-separated step numbers to skip, e.g. 5,6")
    parser.add_argument("--only", type=str, default="",
                        help="Comma-separated step numbers to run exclusively")
    parser.add_argument("--python", type=str,
                        default="C:/Users/vaspapa/AppData/Local/miniforge3/envs/sfincs-viz/python.exe")
    args = parser.parse_args()

    skip = parse_list(args.skip)
    only = parse_list(args.only)

    for step_id, script in STEPS:
        step_int = int(step_id)
        if only and step_int not in only:
            continue
        if step_int in skip:
            print(f"[{step_id}] SKIP {script}")
            continue
        print(f"\n=== [{step_id}] {script} ===")
        res = subprocess.run([args.python, str(THIS_DIR / script),
                              "--config", str(args.config)])
        if res.returncode != 0:
            print(f"[{step_id}] {script} FAILED (exit {res.returncode})")
            return res.returncode
    print("\npipeline finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
