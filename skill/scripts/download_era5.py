"""Download ERA5 hourly forcing for the event window via CDS.

Writes data/era5_<event_slug>_raw.zip (CDS returns a ZIP for the
single-levels reanalysis). Caches: skips if the file already exists.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cdsapi

from _common import load_config


def main():
    cfg = load_config()
    out = cfg.paths["data_dir"] / f"era5_{cfg.event_slug}_raw.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 1024:
        print(f"already present: {out} ({out.stat().st_size/1e6:.1f} MB)")
        return 0

    # Day list for the simulation + spin-up window.
    days = set()
    cur = cfg.tref
    while cur <= cfg.tstop:
        days.add((f"{cur.year:04d}", f"{cur.month:02d}", f"{cur.day:02d}"))
        cur += __import__("datetime").timedelta(days=1)
    years = sorted({d[0] for d in days})
    months = sorted({d[1] for d in days})
    day_strs = sorted({d[2] for d in days})

    if len(years) > 1:
        # CDS request only takes a single year; fall back to per-year requests
        # if the window straddles New Year. For now warn and proceed with the
        # first year — the user's events all land within one year.
        print(f"WARN: window spans multiple years {years}; CDS request may need splitting.")

    req = {
        "product_type": "reanalysis",
        "format": "netcdf",
        "variable": [
            "total_precipitation",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "mean_sea_level_pressure",
        ],
        "year": years[0],
        "month": months,
        "day": day_strs,
        "time": [f"{h:02d}:00" for h in range(24)],
        "area": cfg.bbox_with_buffer,  # NWSE
        "grid": [0.25, 0.25],
    }
    print(f"CDS request: area={req['area']}  year={req['year']}  "
          f"months={req['month']}  days={len(req['day'])}")

    c = cdsapi.Client()
    print(f"CDS client ready -> {c.url}", flush=True)
    c.retrieve("reanalysis-era5-single-levels", req, str(out))
    print(f"done: {out} ({out.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
