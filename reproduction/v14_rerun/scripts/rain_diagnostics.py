"""Phase 4c (GO Phases 3-5, 2026-10-19) — rainfall diagnostics re-derived from the v1.4 forcing files and the raw products.

For one run (its YAML + work dir) and a set of windows, report per source
  * model forcing   model/precip_2d.nc            the field SFINCS read (after R2 scaling and the D5 corner alignment), whole grid
  * imerg_raw       data/imerg_<slug>.raw.nc      raw IMERG half-hourly rates (mm/h, left-labelled), bbox subset
  * imerg           data/imerg_<slug>.nc          IMERG after the R2 bias correction (= raw when R2 is off), bbox subset
  * era5            data/era5_<slug>.nc           ERA5 hourly precipitation (mm/h, accumulation labelled at the end of the hour), bbox subset
the domain-mean total [mm], the maximum cell total [mm], the peak domain-mean intensity [mm/h] with its time, and the peak
cell intensity [mm/h]. Totals integrate rate x step length over t0 <= t < t1 (the step length = the median time spacing).
With an R2 block the IMERG files are also reported on the watershed bbox over the event window (anchor check: the
corrected total should equal target_mm, the ratio corrected/raw is the realised factor).

Usage: python -I rain_diagnostics.py --repo <worktree> --config <run yaml> --out-json <...> [--window name=YYYY-MM-DDTHH:MM,YYYY-MM-DDTHH:MM ...]
Default windows: simulated (tstart..tstop), forcing (tref..tstop), event (rain_bias_correct.event_start..event_end + one step).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np


def _lat_lon_names(da):
    lat = next((d for d in da.dims if d.lower() in ("latitude", "lat", "y")), None)
    lon = next((d for d in da.dims if d.lower() in ("longitude", "lon", "x")), None)
    return lat, lon


def subset_bbox(da, west, south, east, north):
    """Cells whose centre lies inside the bbox, whatever the order of the latitude axis."""
    lat, lon = _lat_lon_names(da)
    ilat = np.where((da[lat].values >= south) & (da[lat].values <= north))[0]
    ilon = np.where((da[lon].values >= west) & (da[lon].values <= east))[0]
    return da.isel({lat: ilat, lon: ilon})


def _step_hours(times) -> float:
    import pandas as pd
    t = pd.to_datetime(times)
    if len(t) < 2:
        return 1.0
    return float(np.median(np.diff(t.values).astype("timedelta64[s]").astype(float)) / 3600.0)


def _window(da, t0, t1):
    import pandas as pd
    t = pd.to_datetime(da["time"].values)
    sel = np.ones(len(t), dtype=bool)
    if t0 is not None:
        sel &= t >= pd.Timestamp(t0)
    if t1 is not None:
        sel &= t < pd.Timestamp(t1)
    return da.isel(time=np.where(sel)[0])


def _cell_totals(da, t0, t1):
    w = _window(da, t0, t1)
    dt_h = _step_hours(da["time"].values)
    return (w.fillna(0.0).sum(dim="time") * dt_h), w, dt_h


def domain_mean_total_mm(da, t0, t1) -> float:
    tot, _, _ = _cell_totals(da, t0, t1)
    return float(tot.mean())


def max_cell_total_mm(da, t0, t1) -> float:
    tot, _, _ = _cell_totals(da, t0, t1)
    return float(tot.max())


def peak_intensity(da, t0, t1) -> dict:
    w = _window(da, t0, t1)
    lat, lon = _lat_lon_names(w)
    series = w.mean(dim=(lat, lon), skipna=True)
    k = int(np.nanargmax(series.values)) if series.size else 0
    return {"domain_mean_peak_mm_h": float(series.values[k]) if series.size else float("nan"),
            "domain_mean_peak_time": str(w["time"].values[k])[:19] if series.size else None,
            "cell_peak_mm_h": float(np.nanmax(w.values)) if w.size else float("nan"),
            "n_steps": int(w.sizes["time"]), "step_h": _step_hours(da["time"].values)}


def summarise(da, t0, t1) -> dict:
    out = peak_intensity(da, t0, t1)
    out["domain_mean_total_mm"] = domain_mean_total_mm(da, t0, t1)
    out["max_cell_total_mm"] = max_cell_total_mm(da, t0, t1)
    lat, lon = _lat_lon_names(da)
    out["n_cells"] = int(da.sizes[lat] * da.sizes[lon])
    return out


def _open(p: Path):
    """Open a precipitation file with a plain datetime64 time axis (hydromt writes precip_2d.nc with a julian calendar,
    which xarray decodes to cftime objects; decode by hand through netCDF4.num2date instead)."""
    import netCDF4
    import xarray as xr
    ds = xr.open_dataset(p, decode_times=False)
    if "valid_time" in ds.coords and "time" not in ds.coords:
        ds = ds.rename({"valid_time": "time"})
    t = ds["time"]
    # cftime components -> datetime64 (hydromt labels precip_2d.nc 'julian'; the labels are calendar dates counted from
    # the reference date, so the components are the dates SFINCS uses — python datetimes would reject the calendar)
    dates = netCDF4.num2date(t.values, t.attrs.get("units", "hours since 1970-01-01"), calendar=t.attrs.get("calendar", "standard"),
                             only_use_cftime_datetimes=True)
    ds = ds.assign_coords(time=np.array([np.datetime64(f"{d.year:04d}-{d.month:02d}-{d.day:02d}T{d.hour:02d}:{d.minute:02d}:{d.second:02d}") for d in dates],
                                        dtype="datetime64[ns]"))
    v = "Precipitation" if "Precipitation" in ds else ("precip" if "precip" in ds else list(ds.data_vars)[0])
    return ds[v], ds.attrs


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--window", action="append", default=[], help="name=t0,t1 (UTC, YYYY-MM-DDTHH:MM)")
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts"))
    from _common import load_config
    cfg = load_config(["--config", str(a.config)])
    data, model = cfg.paths["data_dir"], cfg.paths["model_dir"]
    b = cfg.bbox
    bbox = (float(b["west"]), float(b["south"]), float(b["east"]), float(b["north"]))
    windows = {"simulated": (cfg.tstart, cfg.tstop), "forcing": (cfg.tref, cfg.tstop)}
    bc = cfg.rain_bias_correct if hasattr(cfg, "rain_bias_correct") else {}
    if bc and bc.get("event_start") and bc.get("event_end"):
        e0 = dt.datetime.fromisoformat(str(bc["event_start"]).replace(" ", "T"))
        e1 = dt.datetime.fromisoformat(str(bc["event_end"]).replace(" ", "T")) + dt.timedelta(minutes=30)
        windows["event"] = (e0, e1)
    for w in a.window:
        name, rng = w.split("=", 1)
        t0s, t1s = rng.split(",")
        windows[name] = (dt.datetime.fromisoformat(t0s), dt.datetime.fromisoformat(t1s))
    slug = cfg.event_slug
    sources = {"model_forcing": model / "precip_2d.nc", "imerg_raw": data / f"imerg_{slug}.raw.nc", "imerg": data / f"imerg_{slug}.nc", "era5": data / f"era5_{slug}.nc"}
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "config": str(a.config), "event": slug, "bbox": bbox,
           "rain_source": cfg.rain_source if isinstance(cfg.rain_source, str) else dict(cfg.rain_source),
           "r2": {k: bc.get(k) for k in ("enabled", "target_mm", "watershed_bbox", "event_start", "event_end")} if bc else None,
           "windows": {k: [v[0].isoformat(), v[1].isoformat()] for k, v in windows.items()}, "sources": {}}
    for name, p in sources.items():
        if not p.exists():
            out["sources"][name] = {"file": str(p), "present": False}
            continue
        da, attrs = _open(p)
        rec = {"file": str(p), "present": True, "units": da.attrs.get("units"), "time_first_last": [str(da["time"].values[0])[:16], str(da["time"].values[-1])[:16]],
               "file_attrs": {k: str(v)[:80] for k, v in attrs.items() if k in ("sfincs_corner_alignment", "x_shift_m", "y_shift_m", "source", "imerg_product", "bias_factor", "scale_factor", "target_mm")}}
        if name != "model_forcing":
            sub = subset_bbox(da, *bbox)
            rec["bbox_cells"] = int(sub.size // max(sub.sizes["time"], 1))
            # the published Fig 4 / Fig 6 scripts averaged the whole downloaded file (bbox + era5_buffer_deg): kept for the like-for-like check
            rec["by_window_file_extent"] = {wn: summarise(da, t0, t1) for wn, (t0, t1) in windows.items()}
            rec["file_extent_cells"] = int(da.size // max(da.sizes["time"], 1))
        else:
            sub = da
        rec["by_window"] = {wn: summarise(sub, t0, t1) for wn, (t0, t1) in windows.items()}
        if bc and bc.get("watershed_bbox") and name in ("imerg_raw", "imerg") and "event" in windows:
            wb = bc["watershed_bbox"]
            wb = [float(x) for x in (wb if isinstance(wb, (list, tuple)) else str(wb).split(","))]
            ws = subset_bbox(da, *wb)
            rec["watershed_event_window"] = summarise(ws, *windows["event"])
            rec["watershed_event_window"]["watershed_bbox"] = wb
        out["sources"][name] = rec
    if all(out["sources"].get(k, {}).get("present") for k in ("imerg_raw", "imerg")) and "event" in windows:
        r = out["sources"]["imerg_raw"]["watershed_event_window"]["domain_mean_total_mm"]; c = out["sources"]["imerg"]["watershed_event_window"]["domain_mean_total_mm"]
        out["r2_realised"] = {"raw_watershed_mean_mm": r, "corrected_watershed_mean_mm": c, "factor": (c / r if r else None), "target_mm": bc.get("target_mm")}
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    # domain-mean series (bbox mean rate, mm/h) of every present source -> CSV beside the JSON (the data behind Fig 4 / Fig 6)
    import pandas as pd
    series = {}
    for name, p in sources.items():
        if not p.exists():
            continue
        da, _ = _open(p)
        sub = da if name == "model_forcing" else subset_bbox(da, *bbox)
        lat, lon = _lat_lon_names(sub)
        series[name] = sub.mean(dim=(lat, lon), skipna=True).to_series()
    if series:
        df = pd.DataFrame(series); df.index.name = "time_utc"
        csv = a.out_json.with_name(a.out_json.stem + "_series.csv"); df.to_csv(csv, float_format="%.4f"); out["series_csv"] = str(csv)
        a.out_json.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    for name, rec in out["sources"].items():
        if rec.get("present"):
            for wn, v in rec["by_window"].items():
                print(f"{name:14s} {wn:10s} total {v['domain_mean_total_mm']:7.1f} mm  max cell {v['max_cell_total_mm']:7.1f} mm  peak mean {v['domain_mean_peak_mm_h']:6.2f} mm/h at {v['domain_mean_peak_time']}  peak cell {v['cell_peak_mm_h']:6.1f} mm/h")
    if out.get("r2_realised"):
        print("R2 realised:", out["r2_realised"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
