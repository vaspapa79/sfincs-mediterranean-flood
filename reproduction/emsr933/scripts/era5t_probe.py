"""CODE-10 Stage 0c — which window days are ERA5 (expver 0001) vs ERA5T (expver 0005)?

Retrieves ONE variable (total_precipitation) on a 0.25-deg box over central Crete at
00/06/12/18 UTC for every requestable day of 27 Sep - 7 Oct 2026 (one request per month:
the CDS form is a month x day cross-product), then reads the `expver` coordinate the new
CDS netCDF attaches to each valid_time. Downloads go to a new, empty directory.

Usage: python -I era5t_probe.py --dl-dir D:/ELKAK/implementation/emsr933_crete/availability \
           --out-dir <worktree>/reproduction/emsr933 --days-sep 27,28,29,30 --days-oct 01,02,03
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dl-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--days-sep", default="27,28,29,30")
    ap.add_argument("--days-oct", default="01,02,03")
    args = ap.parse_args()
    import cdsapi
    import xarray as xr

    tag = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dl = args.dl_dir / f"era5t_probe_{tag}"
    dl.mkdir(parents=True, exist_ok=False)
    c = cdsapi.Client()
    rep = {"started_utc": tag, "dataset": "reanalysis-era5-single-levels", "per_time": {}, "requests": []}
    for month, days in (("09", args.days_sep), ("10", args.days_oct)):
        days = [d for d in days.split(",") if d]
        if not days:
            continue
        req = {"product_type": ["reanalysis"], "variable": ["total_precipitation"], "year": ["2026"],
               "month": [month], "day": days, "time": ["00:00", "06:00", "12:00", "18:00"],
               "area": [35.3, 24.9, 35.05, 25.15], "data_format": "netcdf", "download_format": "unarchived"}
        target = dl / f"era5_probe_2026{month}.nc"
        t0 = dt.datetime.now(dt.timezone.utc)
        c.retrieve("reanalysis-era5-single-levels", req, str(target))
        t1 = dt.datetime.now(dt.timezone.utc)
        rep["requests"].append({"month": month, "days": days, "file": target.name,
                                "bytes": target.stat().st_size, "queue_plus_download_s": round((t1 - t0).total_seconds())})
        ds = xr.open_dataset(target)
        tname = "valid_time" if "valid_time" in ds.coords else "time"
        ev = ds["expver"].values if "expver" in ds.coords or "expver" in ds else None
        for i, t in enumerate(ds[tname].values):
            k = str(t)[:16]
            rep["per_time"][k] = str(ev[i]) if ev is not None and getattr(ev, "ndim", 0) == 1 else str(ev)
        ds.close()
    per_day = {}
    for k, v in rep["per_time"].items():
        per_day.setdefault(k[:10], set()).add(v)
    rep["per_day_expver"] = {d: sorted(s) for d, s in sorted(per_day.items())}
    rep["finished_utc"] = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out_dir / f"era5t_probe_{tag}.json"
    out.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep["per_day_expver"], indent=1))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
