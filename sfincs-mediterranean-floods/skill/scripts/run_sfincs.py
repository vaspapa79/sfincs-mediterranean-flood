"""Run the SFINCS binary in model/, captured to sfincs_log.txt."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _common import load_config


def main():
    cfg = load_config()
    model = cfg.paths["model_dir"]
    sfincs = cfg.env.get("sfincs_exe")
    if not sfincs or not Path(sfincs).exists():
        sys.exit(f"sfincs.exe not found at {sfincs}")

    # Clear stale outputs that block the binary from re-opening files.
    for stale in [model / "sfincs_map.nc", model / "sfincs.log",
                  model / "sfincs_log.txt"]:
        if stale.exists():
            stale.unlink()

    log = model / "sfincs_log.txt"
    print(f"running SFINCS in {model}  -> {log}", flush=True)
    with open(log, "w") as fh:
        res = subprocess.run([str(sfincs)], cwd=str(model),
                             stdout=fh, stderr=subprocess.STDOUT)
    print(f"exit code: {res.returncode}")
    print("--- last 20 lines of sfincs_log.txt ---")
    print("\n".join(log.read_text().splitlines()[-20:]))
    if res.returncode != 0:
        sys.exit(f"SFINCS exited non-zero ({res.returncode})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
