"""Download GloFAS v4 reanalysis daily Q for the event window via EWDS.

Reads the CDS key from ~/.cdsapirc, but points the client at the EWDS
endpoint (different URL from CDS, same credential).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import cdsapi

from _common import load_config


def main():
    cfg = load_config()
    out = cfg.paths["data_dir"] / f"glofas_{cfg.event_slug}.nc"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 1024:
        print(f"already present: {out} ({out.stat().st_size/1e6:.1f} MB)")
        return 0

    cds_key_file = Path(os.path.expanduser(cfg.env.get("cds_key_file", "~/.cdsapirc")))
    if not cds_key_file.exists():
        sys.exit(f"missing CDS credentials at {cds_key_file}")
    key = None
    for ln in cds_key_file.read_text().splitlines():
        if ln.startswith("key:"):
            key = ln.split(":", 1)[1].strip()
            break
    if not key:
        sys.exit(f"could not read 'key:' line from {cds_key_file}")

    c = cdsapi.Client(url="https://ewds.climate.copernicus.eu/api", key=key)
    print(f"EWDS client ready -> {c.url}", flush=True)

    # Pull the full month(s) of the event for headroom.
    years = sorted({cfg.tref.year, cfg.tstop.year})
    months = sorted({f"{cfg.tref.month:02d}", f"{cfg.tstop.month:02d}"})

    req = {
        "system_version": ["version_4_0"],
        "hydrological_model": ["lisflood"],
        "product_type": ["consolidated"],
        "variable": ["river_discharge_in_the_last_24_hours"],
        "hyear": [str(y) for y in years],
        "hmonth": months,
        "hday": [f"{d:02d}" for d in range(1, 32)],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": cfg.bbox_with_buffer,
    }
    print(f"GloFAS request: area={req['area']}  year={req['hyear']}  "
          f"months={req['hmonth']}")
    c.retrieve("cems-glofas-historical", req, str(out))
    print(f"done: {out} ({out.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
