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
sys.path.insert(0, str(THIS_DIR))  # so --check can import _common helpers

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


def maybe_bias_correct(python: str, config_path: Path) -> int:
    """R5: gauge-anchored IMERG bias correction, parameterised from the YAML.

    Runs as step 06b (right after download_imerg, before prep_inputs) whenever
    the config carries an enabled `rain_bias_correct` block on an IMERG run.
    The scaling factor + window + watershed used to live only in CLI history;
    sourcing them from the config makes the rainfall forcing reproducible. The
    correction is idempotent (bias_correct_imerg.py keeps a `.raw.nc` backup),
    so re-runs are safe. No-op when the block is absent/disabled.
    """
    from _common import load_config
    cfg = load_config(["--config", str(config_path)])
    bc = cfg.rain_bias_correct
    if not (bc["enabled"] and cfg.rain_source == "imerg_half_hourly"):
        print("[06b] bias_correct_imerg.py SKIP (rain_bias_correct disabled)")
        return 0
    missing = [k for k in ("watershed_bbox", "event_start", "event_end") if not bc[k]]
    if missing:
        print(f"[06b] bias_correct_imerg.py FAILED: rain_bias_correct enabled but "
              f"missing {', '.join(missing)}")
        return 2
    cmd = [python, str(THIS_DIR / "bias_correct_imerg.py"),
           "--config", str(config_path),
           "--target-mm", repr(bc["target_mm"]),
           "--event-start", bc["event_start"],
           "--event-end", bc["event_end"],
           "--watershed-bbox", bc["watershed_bbox"]]
    print(f"\n=== [06b] bias_correct_imerg.py "
          f"(target {bc['target_mm']:g} mm, watershed {bc['watershed_bbox']}, "
          f"{bc['event_start']} -> {bc['event_end']}) ===")
    return subprocess.run(cmd).returncode


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
    parser.add_argument("--python", type=str, default=sys.executable,
                        help="Python that runs each step (default: the interpreter "
                             "running this script — i.e. activate sfincs-viz first).")
    parser.add_argument("--check", action="store_true",
                        help="Preflight only: validate tools/paths/creds (incl. the "
                             "machine-local override) and exit, before any download.")
    args = parser.parse_args()

    if args.check:
        from _common import load_config, preflight_check
        return preflight_check(load_config(["--config", str(args.config)]))

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
        # R5: bias-correct the freshly downloaded IMERG before prep_inputs (07).
        if step_id == "06":
            rc = maybe_bias_correct(args.python, args.config)
            if rc != 0:
                print(f"[06b] bias_correct_imerg.py FAILED (exit {rc})")
                return rc
    print("\npipeline finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
