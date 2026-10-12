"""CODE-12 A3 (report only, D3) — domain-mean ERA5 and IMERG precipitation totals in each event's
spin-up window [tref, tstart) (downloaded but never simulated, F5_VERIFY (f)), plus the simulated
window [tstart, tstop) for scale, and whether SCS-CN infiltration is on. Nothing is changed.

Domain = the YAML bbox (model domain); ERA5 cells whose centre falls inside the bbox (nearest cell
if none), IMERG likewise. ERA5 `precip` = tp x 1000 stamped at the END of each hour (ECMWF) ->
rain in [t0, t1) = sum of stamps in (t0, t1]; IMERG = mean rate [mm/h] stamped at the START of each
30-min window -> sum(rate) x 0.5 h over stamps in [t0, t1).

Usage: python -I a3_spinup_totals.py --repo <worktree> --out-json <...> --out-md <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

EVENTS = [  # (label, example yaml, data dir, IMERG file preference)
    ("Pineios EMSR692 enhanced", "emsr692_pineios_enhanced.yaml", "D:/ELKAK/implementation/pineios_sfincs_enhanced/data"),
    ("Pineios EMSR692 baseline", "emsr692_pineios.yaml", "D:/ELKAK/implementation/pineios_sfincs_enhanced/data"),
    ("Mandra EMSR257 enhanced", "emsr257_mandra_enhanced.yaml", "D:/ELKAK/implementation/mandra_sfincs_enhanced/data"),
    ("Mandra EMSR257 baseline", "emsr257_mandra.yaml", "D:/ELKAK/implementation/mandra_sfincs_enhanced/data"),
    ("Strymonas EMSR122 enhanced (v3)", "emsr122_strymonas_enhanced.yaml", "D:/ELKAK/implementation/emsr122_sfincs_v3/data"),
    ("Strymonas EMSR122 baseline", "emsr122_strymonas.yaml", "D:/ELKAK/implementation/emsr122_sfincs_v3/data"),
    ("Valencia EMSR773 enhanced", "emsr773_valencia_enhanced.yaml", "D:/ELKAK/ELKAK2/NHESS/runs/valencia_emsr773/data"),
    ("Emilia-Romagna EMSR664 enhanced", "emsr664_emilia_romagna_enhanced.yaml", "D:/ELKAK/ELKAK2/NHESS/runs/emilia_emsr664/data"),
    ("Crete EMSR933 enhanced (Late IMERG)", "emsr933_crete_enhanced.yaml", "D:/ELKAK/implementation/emsr933_crete_enhanced/data"),
    ("Crete EMSR933 baseline", "emsr933_crete.yaml", "D:/ELKAK/implementation/emsr933_crete/data"),
]


def _bbox_sel(da, bbox, latn, lonn):
    w, s, e, n = bbox
    lat, lon = da[latn].values, da[lonn].values
    li = np.where((lat >= s) & (lat <= n))[0]; lo = np.where((lon >= w) & (lon <= e))[0]
    if li.size == 0:
        li = np.array([int(np.argmin(np.abs(lat - (s + n) / 2)))])
    if lo.size == 0:
        lo = np.array([int(np.argmin(np.abs(lon - (w + e) / 2)))])
    return da.isel({latn: li, lonn: lo}), int(li.size * lo.size)


def _era5_total(path: Path, bbox, t0, t1):
    import pandas as pd
    import xarray as xr
    ds = xr.open_dataset(path)
    if "valid_time" in ds.coords:
        ds = ds.rename({"valid_time": "time"})
    da = ds["precip"] if "precip" in ds else ds["tp"] * 1000.0
    latn = "latitude" if "latitude" in da.dims else "lat"; lonn = "longitude" if "longitude" in da.dims else "lon"
    da, ncell = _bbox_sel(da, bbox, latn, lonn)
    t = pd.to_datetime(da["time"].values)
    sel = (t > pd.Timestamp(t0)) & (t <= pd.Timestamp(t1))           # end-of-hour stamps in (t0, t1]
    tot = float(da.isel(time=np.where(sel)[0]).sum("time").mean().values) if sel.any() else None
    return tot, ncell, int(sel.sum()), [str(t.min()), str(t.max())]


def _imerg_total(path: Path, bbox, t0, t1):
    import re
    import pandas as pd
    import xarray as xr
    # raw IMERG files keep the GPM 'calendar: julian' attribute -> decode the time axis by hand
    # (seconds since the GPS epoch; Julian and Gregorian numerals coincide between 1901 and 2099)
    ds = xr.open_dataset(path, decode_times=False)
    da = ds["precip"]
    latn = "latitude" if "latitude" in da.dims else "lat"; lonn = "longitude" if "longitude" in da.dims else "lon"
    da, ncell = _bbox_sel(da, bbox, latn, lonn)
    units = str(da["time"].attrs.get("units", ""))
    m = re.match(r"(\w+) since (\d{4}-\d{2}-\d{2})[T ]?(\d{2}:\d{2}:\d{2})?", units)
    if not m:
        raise ValueError(f"cannot parse IMERG time units {units!r} in {path}")
    base = pd.Timestamp(m.group(2) + " " + (m.group(3) or "00:00:00"))
    tv = (base + pd.to_timedelta(da["time"].values.astype("float64"), unit=m.group(1)[0])).values
    sel = (tv >= np.datetime64(t0)) & (tv < np.datetime64(t1))        # start-of-interval stamps in [t0, t1)
    tot = float((da.isel(time=np.where(sel)[0]).sum("time") * 0.5).mean().values) if sel.any() else None
    return tot, ncell, int(sel.sum()), [str(tv.min())[:16], str(tv.max())[:16]]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--out-md", required=True, type=Path)
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts"))
    from _common import load_config

    rep = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "events": []}
    for label, yml, ddir in EVENTS:
        cfg = load_config(["--config", str(a.repo / "skill" / "examples" / yml)])
        ddir = Path(ddir)
        row = {"label": label, "yaml": yml, "data_dir": str(ddir), "slug": cfg.event_slug, "window_days": cfg.window,
               "tref": cfg.tref.isoformat(), "tstart": cfg.tstart.isoformat(), "tstop": cfg.tstop.isoformat(),
               "spinup_days_download_only": (cfg.tstart - cfg.tref).days, "bbox_WSEN": cfg.bbox_list,
               "rain_source": cfg.rain_source, "scs_cn_enabled": cfg.infiltration["enabled"],
               "scs_cn_amc": cfg.infiltration["amc"] if cfg.infiltration["enabled"] else None,
               "rain_bias_correct_enabled": cfg.rain_bias_correct["enabled"]}
        era = ddir / f"era5_{cfg.event_slug}.nc"
        im_raw, im = ddir / f"imerg_{cfg.event_slug}.raw.nc", ddir / f"imerg_{cfg.event_slug}.nc"
        imf = im_raw if im_raw.exists() else (im if im.exists() else None)
        row["files"] = {"era5": str(era) if era.exists() else None, "imerg": str(imf) if imf else None,
                        "imerg_is_raw": (imf == im_raw) if imf else None}
        for key, (t0, t1) in {"spinup": (cfg.tref, cfg.tstart), "simulated": (cfg.tstart, cfg.tstop)}.items():
            r = {}
            if era.exists():
                tot, nc, ns, span = _era5_total(era, cfg.bbox_list, t0, t1)
                r["era5_mm"] = None if tot is None else round(tot, 1); r["era5_cells"] = nc; r["era5_stamps"] = ns; r["era5_file_span"] = span
            if imf:
                tot, nc, ns, span = _imerg_total(imf, cfg.bbox_list, t0, t1)
                r["imerg_mm"] = None if tot is None else round(tot, 1); r["imerg_cells"] = nc; r["imerg_stamps"] = ns; r["imerg_file_span"] = span
            row[key] = r
        rep["events"].append(row)
        print(label, json.dumps({k: row[k] for k in ("spinup", "simulated")}))
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    L = [f"# A3 — precipitation in the spin-up window [tref, tstart) that is downloaded but not simulated (tspinup = 0), {rep['utc']}", "",
         "Domain means over the YAML bbox; ERA5 end-of-hour stamps in (tref, tstart], IMERG start-of-interval stamps in [tref, tstart) x 0.5 h; "
         "IMERG = raw product (before any R2 bias factor) where the .raw.nc exists. Report only — nothing changed.", "",
         "| event / config | spin-up d (tref -> tstart) | ERA5 spin-up mm | IMERG spin-up mm | ERA5 simulated mm | IMERG simulated mm | SCS-CN | R2 bias |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rep["events"]:
        sp, si = r["spinup"], r["simulated"]
        f = lambda d, k: ("—" if d.get(k) is None else f"{d[k]:.1f}")  # noqa: E731
        L.append(f"| {r['label']} | {r['spinup_days_download_only']} ({r['tref'][:10]} -> {r['tstart'][:10]}) | {f(sp, 'era5_mm')} | {f(sp, 'imerg_mm')} | "
                 f"{f(si, 'era5_mm')} | {f(si, 'imerg_mm')} | {'on (AMC ' + str(r['scs_cn_amc']) + ')' if r['scs_cn_enabled'] else 'off'} | "
                 f"{'on' if r['rain_bias_correct_enabled'] else 'off'} |")
    a.out_md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L)); print(f"-> {a.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
