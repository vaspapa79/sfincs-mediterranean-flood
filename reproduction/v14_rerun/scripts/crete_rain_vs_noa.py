"""Phase 5d (GO Phases 3-5, 2026-10-19) — EMSR933 Crete rainfall diagnostics against the NOA/meteo.gr stations.

For every station with coordinates in reproduction/emsr933/noa_stations/stations_daily.csv: the NOA total over the local
days 30 Sep - 4 Oct 2026 (the rule_ledger.md §8 anchor window; a station-local day is 21:00 UTC -> 21:00 UTC, so the window is
2026-09-29T21:00Z -> 2026-10-04T21:00Z), and over the same UTC window the nearest-cell totals of raw IMERG Late, IMERG after
the R2 correction (the canonical run's forcing file) and ERA5(T). Output: JSON + CSV + a grouped bar chart. The station
coordinates are rounded to whole arc-minutes (0.1°) in the NOA headers (stations_meta.csv), i.e. one IMERG cell of uncertainty.
NOA values are reproduced here only for the comparison; publication needs NOA consent/attribution (meteo.gr terms).

Usage: python -I crete_rain_vs_noa.py --repo <worktree> --raw <imerg_crete.raw.nc or the uncorrected imerg_crete.nc>
       --r2 <imerg_crete.nc of the canonical run> --era5 <era5_crete.nc> --out-json <...> [--days 2026-09-30,2026-10-04]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np


def utc_window(day_first: str, day_last: str):
    """Local calendar days (EEST, UTC+3) -> UTC window [first day 21:00Z of the previous day, last day 21:00Z)."""
    d0 = dt.datetime.fromisoformat(day_first); d1 = dt.datetime.fromisoformat(day_last)
    return d0 - dt.timedelta(hours=3), d1 + dt.timedelta(days=1) - dt.timedelta(hours=3)


def station_totals(daily_csv: Path, days: tuple[str, str]) -> dict:
    d0, d1 = days
    out = {}
    with open(daily_csv, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not (d0 <= r["date"] <= d1):
                continue
            try:
                lat, lon = float(r["lat"]), float(r["lon"])
            except ValueError:
                continue
            s = out.setdefault(r["station_slug"], {"station": r["station_slug"], "name": r["station_name"], "lat": lat, "lon": lon,
                                                    "elev_m": r.get("elev_m"), "noa_total_mm": 0.0, "n_days": 0, "days": []})
            s["noa_total_mm"] += float(r["rain_mm"]); s["n_days"] += 1; s["days"].append(r["date"])
    return out


def nearest_total_mm(da, lon: float, lat: float, t0, t1):
    import pandas as pd
    pt = da.sel(latitude=lat, longitude=lon, method="nearest")
    t = pd.to_datetime(pt["time"].values)
    sel = (t >= pd.Timestamp(t0)) & (t < pd.Timestamp(t1))
    v = np.asarray(pt.values, dtype=float)[sel]
    if len(t) > 1:
        step_h = float(np.median(np.diff(t.values).astype("timedelta64[s]").astype(float)) / 3600.0)
    else:
        step_h = 1.0
    return float(np.nansum(v) * step_h), (float(pt.longitude), float(pt.latitude))


def _open(p: Path):
    import netCDF4
    import xarray as xr
    ds = xr.open_dataset(p, decode_times=False)
    if "valid_time" in ds.coords and "time" not in ds.coords:
        ds = ds.rename({"valid_time": "time"})
    t = ds["time"]
    dates = netCDF4.num2date(t.values, t.attrs.get("units", "hours since 1970-01-01"), calendar=t.attrs.get("calendar", "standard"), only_use_cftime_datetimes=True)
    ds = ds.assign_coords(time=np.array([np.datetime64(f"{d.year:04d}-{d.month:02d}-{d.day:02d}T{d.hour:02d}:{d.minute:02d}:{d.second:02d}") for d in dates], dtype="datetime64[ns]"))
    v = "precip" if "precip" in ds else list(ds.data_vars)[0]
    return ds[v]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--raw", required=True, type=Path); ap.add_argument("--r2", type=Path); ap.add_argument("--era5", type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--days", default="2026-09-30,2026-10-04")
    a = ap.parse_args()
    d0, d1 = a.days.split(",")
    t0, t1 = utc_window(d0, d1)
    st = station_totals(a.repo / "reproduction" / "emsr933" / "noa_stations" / "stations_daily.csv", (d0, d1))
    fields = {"imerg_raw_mm": _open(a.raw)}
    if a.r2 and a.r2.exists():
        fields["imerg_r2_mm"] = _open(a.r2)
    if a.era5 and a.era5.exists():
        fields["era5_mm"] = _open(a.era5)
    rows = []
    for slug, s in sorted(st.items()):
        r = dict(s)
        for k, da in fields.items():
            r[k], cell = nearest_total_mm(da, s["lon"], s["lat"], t0, t1)
            r[k + "_cell"] = cell
        rows.append(r)
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "local_days": [d0, d1], "window_utc": [t0.isoformat(), t1.isoformat()],
           "files": {k: str(v) for k, v in (("raw", a.raw), ("r2", a.r2), ("era5", a.era5)) if v}, "stations": rows,
           "note": "NOA station coordinates are rounded to 0.1 deg in the station headers (one IMERG cell); NOA values from meteo.gr station summaries, attribution required for publication"}
    for k in fields:
        xs = np.array([r[k] for r in rows]); ys = np.array([r["noa_total_mm"] for r in rows]); ok = np.array([r["n_days"] == 5 for r in rows])
        out[f"{k}_vs_noa"] = {"n_complete_stations": int(ok.sum()), "mean_ratio_field_over_noa": float(np.mean(xs[ok] / ys[ok])) if ok.any() else None,
                              "mean_bias_mm": float(np.mean(xs[ok] - ys[ok])) if ok.any() else None, "rmse_mm": float(np.sqrt(np.mean((xs[ok] - ys[ok]) ** 2))) if ok.any() else None}
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    with open(a.out_json.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        cols = ["station", "name", "lat", "lon", "elev_m", "n_days", "noa_total_mm"] + list(fields)
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "font.size": 8, "savefig.dpi": 300})
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    x = np.arange(len(rows)); wdt = 0.8 / (1 + len(fields))
    ax.bar(x, [r["noa_total_mm"] for r in rows], wdt, color="k", label=f"NOA station ({d0} → {d1}, local days)")
    for i, (k, lab, c) in enumerate([("imerg_raw_mm", "raw IMERG Late", "#7f7f7f"), ("imerg_r2_mm", "IMERG after R2 (447.8 mm anchor)", "#1f4e79"), ("era5_mm", "ERA5(T)", "#c0392b")]):
        if k in fields:
            ax.bar(x + (i + 1) * wdt, [r[k] for r in rows], wdt, color=c, label=lab)
    ax.set_xticks(x + 0.4); ax.set_xticklabels([r["station"] + ("" if r["n_days"] == 5 else "*") for r in rows], rotation=45, ha="right")
    ax.set_ylabel("5-day total (mm)"); ax.set_title("EMSR933 Crete: 29 Sep 21:00 → 4 Oct 21:00 UTC, nearest grid cell per station (* = incomplete station record)")
    ax.legend(fontsize=6.5, frameon=False); fig.tight_layout(); fig.savefig(a.out_json.with_suffix(".png")); plt.close(fig)
    for r in rows:
        print(f"{r['station']:14s} NOA {r['noa_total_mm']:6.1f} mm ({r['n_days']} d)  " + "  ".join(f"{k} {r[k]:6.1f}" for k in fields))
    print({k: out[f"{k}_vs_noa"] for k in fields})
    return 0


if __name__ == "__main__":
    sys.exit(main())
