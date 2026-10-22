"""CODE-19 A1 — domain-mean precipitation over the ACTIVE MASK of each canonical run (ERA5 and raw IMERG), for the 7-day forcing
lead-in before the simulated window and for the simulated window, plus the largest 24-h domain-mean total inside the lead-in and
the 5-day antecedent totals (the AMC window) before tstart and before the event day. Zero compute: reads the run's own forcing
files (data/era5_<slug>.nc; data/imerg_<slug>.raw.nc, or imerg_<slug>.nc where R2 is off and the file is the raw product) and
sfincs_map.nc (msk, x, y). No SFINCS run, no scoring.

Conventions (recorded in the JSON): ERA5 hourly values are accumulations labelled at the END of the hour, so a window [t0, t1)
takes the labels t0 < t <= t1; IMERG half-hourly rates are labelled at the START of the interval, so [t0, t1) takes t0 <= t < t1.
Domain mean = mean over the active cells of the nearest source cell (equal-area UTM cells -> area weights on the source grid).
Where a file does not cover the whole 7-day lead-in (Mandra: 1 d, Valencia: 3 d of IMERG), the covered part is reported with
its coverage; nothing is downloaded.

Usage (sfincs-viz env): python -I code19_a1_rain_leadin.py --repo <worktree>
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RUNS = [("pineios", "pineios_enhanced_v142"), ("mandra", "mandra_enhanced"), ("strymonas", "strymonas_enhanced_postD6_v142"),
        ("valencia", "valencia_enhanced_164_v142"), ("emilia", "emilia_enhanced_8aoi_v142"), ("crete", "crete_canonical_r2on")]
LEADIN_DAYS, AMC_DAYS = 7, 5
LABELLING = {"era5": "end", "imerg_raw": "start"}


def select_steps(times, t0, t1, labelling: str):
    """Boolean mask of the steps whose interval lies in [t0, t1): 'start'-labelled rates -> t0 <= t < t1; 'end'-labelled
    accumulations (label at the end of the step) -> t0 < t <= t1."""
    t = np.asarray(times, dtype="datetime64[ns]")
    t0, t1 = np.datetime64(t0, "ns"), np.datetime64(t1, "ns")
    if labelling == "start":
        return (t >= t0) & (t < t1)
    if labelling == "end":
        return (t > t0) & (t <= t1)
    raise ValueError(labelling)


def rolling_max(rate, step_h: float, hours: float = 24.0):
    """(largest sum of rate x step_h over any window of `hours`, index of the window's first step); NaN counts as 0;
    (nan, -1) when the series is shorter than the window."""
    r = np.nan_to_num(np.asarray(rate, dtype=float)) * step_h
    n = int(round(hours / step_h))
    if len(r) < n or n < 1:
        return float("nan"), -1
    cs = np.concatenate([[0.0], np.cumsum(r)])
    sums = cs[n:] - cs[:-n]
    i = int(np.argmax(sums))
    return float(sums[i]), i


def nearest_index(axis, values):
    """Index on a monotonic 1-D axis (either direction) of the coordinate nearest to each value."""
    a = np.asarray(axis, dtype=float); order = np.argsort(a); s = a[order]
    v = np.asarray(values, dtype=float)
    j = np.clip(np.searchsorted(s, v), 1, len(s) - 1)
    pick = np.where(np.abs(v - s[j - 1]) <= np.abs(s[j] - v), j - 1, j)
    return order[pick]


def read_precip(nc_path: Path):
    """(times datetime64[ns], rate (time, lat, lon) in the file's units, lat, lon, step_h, attrs) of a pipeline ERA5 / IMERG file."""
    import netCDF4
    import xarray as xr
    ds = xr.open_dataset(nc_path, decode_times=False)
    if "valid_time" in ds.coords and "time" not in ds.coords:
        ds = ds.rename({"valid_time": "time"})
    t = ds["time"]
    dates = netCDF4.num2date(t.values, t.attrs.get("units", "hours since 1970-01-01"), calendar=t.attrs.get("calendar", "standard"), only_use_cftime_datetimes=True)
    times = np.array([np.datetime64(f"{d.year:04d}-{d.month:02d}-{d.day:02d}T{d.hour:02d}:{d.minute:02d}:{d.second:02d}") for d in dates], dtype="datetime64[ns]")
    v = "precip" if "precip" in ds else list(ds.data_vars)[0]
    da = ds[v].transpose("time", "latitude", "longitude")
    rate = da.values.astype(float)
    lat, lon = da["latitude"].values.astype(float), da["longitude"].values.astype(float)
    step_h = float(np.median(np.diff(times).astype("timedelta64[s]").astype(float)) / 3600.0)
    attrs = {k: str(v_) for k, v_ in {**ds.attrs, **da.attrs}.items()}
    ds.close()
    return times, rate, lat, lon, step_h, attrs


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rule_r4_clause(repo: Path) -> list:
    lines = (repo / "docs" / "frozen_rule_R.md").read_text(encoding="utf-8").splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith("R4 SCS-CN"))
    j = next(k for k in range(i + 1, len(lines)) if lines[k].startswith("R5 "))
    return lines[i:j]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    a = ap.parse_args()
    repo = a.repo.resolve()
    for p in (repo / "skill" / "scripts", repo / "validation"):
        sys.path.insert(0, str(p))
    import pyproj
    from _common import load_config
    import validate_event_v2 as V

    out_dir = repo / "reproduction" / "v14_rerun" / "code19"; out_dir.mkdir(parents=True, exist_ok=True)
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/code19_a1_rain_leadin.py",
           "definition": "domain mean over the active cells (msk > 0) of the nearest source cell; ERA5 end-labelled hourly accumulations (t0 < t <= t1), IMERG start-labelled "
                         "half-hourly rates (t0 <= t < t1); totals = sum(rate x step); lead-in = [tstart - 7 d, tstart); simulated = [tstart, tstop); max 24 h = largest "
                         "rolling 24-h total of the domain-mean series inside the covered lead-in; AMC-5d = [t - 5 d, t) before tstart and before the event day",
           "leadin_days": LEADIN_DAYS, "amc_days": AMC_DAYS, "rule_R4_clause": rule_r4_clause(repo), "events": []}
    for event, run in RUNS:
        cfg_path = repo / "reproduction" / "v14_rerun" / "configs" / f"{run}.yaml"
        cfg = load_config(["--config", str(cfg_path)])
        rec = json.loads((repo / "reproduction" / "v14_rerun" / "results" / f"{run}_record.json").read_text(encoding="utf-8"))
        rj = json.loads((repo / "reproduction" / "v14_rerun" / "phase4" / "rain" / f"{run}_v14.json").read_text(encoding="utf-8"))
        s = V.open_sfincs_light(cfg.paths["model_dir"]); s["ds"].close()
        active = s["msk"] > 0
        tr = pyproj.Transformer.from_crs(cfg.epsg, 4326, always_xy=True)
        lon_c, lat_c = tr.transform(s["x"][active], s["y"][active])
        tstart, tstop = np.datetime64(cfg.tstart), np.datetime64(cfg.tstop)
        t_lead0 = tstart - np.timedelta64(LEADIN_DAYS, "D")
        event_day = tstart + np.timedelta64(int(cfg.window["pre_event_days"]), "D")
        windows = {"leadin_7d": (t_lead0, tstart), "simulated": (tstart, tstop), "amc_5d_before_tstart": (tstart - np.timedelta64(AMC_DAYS, "D"), tstart),
                   "amc_5d_before_event_day": (event_day - np.timedelta64(AMC_DAYS, "D"), event_day)}
        r2_on = bool((cfg.raw.get("rain_bias_correct") or {}).get("enabled"))
        slug = cfg.event_slug
        files = {"era5": cfg.paths["data_dir"] / f"era5_{slug}.nc",
                 "imerg_raw": cfg.paths["data_dir"] / (f"imerg_{slug}.raw.nc" if r2_on else f"imerg_{slug}.nc")}
        ev = {"event": event, "run": run, "config": str(cfg_path.relative_to(repo)).replace("\\", "/"), "epsg": cfg.epsg, "active_cells": int(active.sum()),
              "tstart": str(tstart)[:16], "tstop": str(tstop)[:16], "event_day": str(event_day)[:10], "r2_enabled": r2_on,
              "infiltration": {k: cfg.raw.get("infiltration", {}).get(k) for k in ("enabled", "hsg", "amc")}, "cn_realised_active_mean": (rec.get("cn_realised") or {}).get("active_mean_cn"),
              "windows": {k: [str(v[0])[:16], str(v[1])[:16]] for k, v in windows.items()}, "sources": {}}
        for key, path in files.items():
            if not path.exists():
                ev["sources"][key] = {"file": str(path), "present": False}; continue
            times, rate, lat, lon, step_h, attrs = read_precip(path)
            if key == "imerg_raw" and not r2_on:
                assert "bias_correction" not in attrs, f"{run}: {path.name} carries a bias_correction attribute but R2 is off"
            ilat, ilon = nearest_index(lat, lat_c), nearest_index(lon, lon_c)
            w = np.bincount(ilat * len(lon) + ilon, minlength=len(lat) * len(lon)).reshape(len(lat), len(lon)).astype(float)
            wsum = w.sum()
            series = np.tensordot(np.nan_to_num(rate), w, axes=([1, 2], [0, 1])) / wsum
            nanw = np.tensordot(np.isnan(rate).astype(float), w, axes=([1, 2], [0, 1])) / wsum
            src = {"file": str(path), "sha256": sha256(path), "present": True, "units": attrs.get("units", "mm/h (pipeline convention)"), "step_h": step_h,
                   "labelling": LABELLING[key], "file_time_first_last": [str(times[0])[:16], str(times[-1])[:16]], "source_cells_weighted": int((w > 0).sum()),
                   "rain_json_bbox_simulated_total_mm": ((rj["sources"].get(key if r2_on or key == "era5" else "imerg") or {}).get("by_window") or {}).get("simulated", {}).get("domain_mean_total_mm"),
                   "windows": {}}
            if key == "imerg_raw":
                src["file_source_attr"] = attrs.get("source")
            for wk, (t0, t1) in windows.items():
                sel = select_steps(times, t0, t1, LABELLING[key])
                hours = (t1 - t0) / np.timedelta64(1, "h")
                cov_h = float(sel.sum() * step_h)
                rec_w = {"total_mm": float(series[sel].sum() * step_h) if sel.any() else None, "coverage_h": cov_h, "window_h": float(hours),
                         "coverage_fraction": round(cov_h / hours, 4) if hours else None, "max_nan_weight_fraction": float(nanw[sel].max()) if sel.any() else None}
                if wk == "leadin_7d":
                    tot, i0 = rolling_max(series[sel], step_h, 24.0) if sel.any() else (float("nan"), -1)
                    if i0 >= 0:
                        lab = times[sel][i0]
                        start = lab - np.timedelta64(int(step_h * 60), "m") if LABELLING[key] == "end" else lab
                        rec_w["max_24h_total_mm"] = tot; rec_w["max_24h_start"] = str(start)[:16]
                    else:
                        rec_w["max_24h_total_mm"] = None; rec_w["max_24h_start"] = None
                src["windows"][wk] = rec_w
            ev["sources"][key] = src
        out["events"].append(ev)
        e, i = ev["sources"]["era5"], ev["sources"]["imerg_raw"]
        def f(src, wk, k="total_mm"):
            v = (src.get("windows") or {}).get(wk, {}).get(k) if src.get("present") else None
            return "—" if v is None else f"{v:.1f}"
        def cov(src, wk):
            v = (src.get("windows") or {}).get(wk, {}).get("coverage_fraction") if src.get("present") else None
            return "" if v in (None, 1.0) else f" ({v * 100:.0f} % of the window covered)"
        print(f"{event} ({run}): active {ev['active_cells']} | lead-in 7 d ERA5 {f(e, 'leadin_7d')}{cov(e, 'leadin_7d')} / IMERG {f(i, 'leadin_7d')}{cov(i, 'leadin_7d')} mm; "
              f"simulated ERA5 {f(e, 'simulated')} / IMERG {f(i, 'simulated')} mm; max 24 h in lead-in ERA5 {f(e, 'leadin_7d', 'max_24h_total_mm')} / IMERG {f(i, 'leadin_7d', 'max_24h_total_mm')} mm; "
              f"AMC 5 d before tstart ERA5 {f(e, 'amc_5d_before_tstart')} / IMERG {f(i, 'amc_5d_before_tstart')}; before event day {f(e, 'amc_5d_before_event_day')} / {f(i, 'amc_5d_before_event_day')}", flush=True)
    (out_dir / "a1_rain_leadin.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", out_dir / "a1_rain_leadin.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
