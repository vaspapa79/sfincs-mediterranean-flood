"""D6 (found at Checkpoint 4, report only) — SFINCS v2.3.0 curve-number infiltration ('cna') without storecumprcp.

Source facts (v2.3.0_mt_Faber_release):
  * sfincs_domain.f90:2066-2069   scsfile given -> inftype = 'cna' (the hydromt setup_cn_infiltration route).
  * sfincs_meteo.f90:1265-1266    2-D rain: netprcp = prcp; cumprcp = cumprcp + prcp*dt   (always).
  * sfincs_infiltration.f90:87-112 'cna': if cumprcp > 0.2 S: I = cumprcp - Q(cumprcp); qinfmap = (I - cuminf)/dt;
                                  netprcp -= qinfmap; cuminf += qinfmap*dt ONLY if store_cumulative_precipitation.
  * sfincs_input.f90:219, 439-441 storecumprcp default 0 -> store_cumulative_precipitation = .false.
  * sfincs_continuity.f90:~535    z_volume = z_volume + dvol (no floor; the 'cna' branch has no z_volume <= 0 guard,
                                  unlike 'con', sfincs_infiltration.f90:45-46).
  => with storecumprcp = 0, cuminf stays 0, every time step removes the WHOLE cumulative infiltration I from a cell
     whose cumulative rain exceeds Ia = 0.2 S: an unbounded sink for rain and for any inflowing water (discharge).

This script demonstrates it on a closed synthetic plain (no boundary, no sea): CN 76 everywhere (S = 80.2 mm,
Ia = 16.0 mm), 30 mm of rain in 3 h, then a 20 m3/s point source for 12 h; 24-h run. The same hydromt build is run
twice, storecumprcp = 0 (as published) and 1; the water volume on the grid at the end is compared with the
correct SCS budget (rain runoff Q(30 mm) over the area + the source volume). No event, no score.
Usage: python -I d6_cn_sink_check.py --repo <worktree> --out-json <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

BBOX = (23.0, 35.0, 23.1, 35.09)             # ~9.1 x 10.0 km
CN = 76
RAIN_MM_H, RAIN_HOURS = 10.0, 3              # 30 mm, 01:00-04:00
Q_M3S, Q_START_H, Q_END_H = 20.0, 6.0, 18.0


def scs_runoff_mm(p_mm: float, cn: float) -> float:
    s = (1000.0 / cn - 10.0) * 25.4
    ia = 0.2 * s
    return 0.0 if p_mm <= ia else (p_mm - ia) ** 2 / (p_mm + 0.8 * s)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts"))
    os.environ.setdefault("GDAL_DATA", str(Path(sys.executable).parent / "Library" / "share" / "gdal"))
    import pandas as pd
    import rasterio
    import xarray as xr
    from rasterio.transform import from_origin
    from _common import EventCfg, _load_machine_override
    import build_model

    env = _load_machine_override()["env"]
    work = Path(tempfile.mkdtemp(prefix="d6_cn_"))
    data = work / "data"; data.mkdir()
    w, s, e, n = BBOX
    res = 0.0005
    ny, nx = int(round((n - s + 0.02) / res)), int(round((e - w + 0.02) / res))
    tr = from_origin(w - 0.01, n + 0.01, res, res)
    for name, val, dtype, nod in (("dep.tif", 2.0, "float32", -9999.0), ("landuse.tif", 40, "uint8", 0), ("cn.tif", CN, "uint8", 0)):
        with rasterio.open(data / name, "w", driver="GTiff", height=ny, width=nx, count=1, dtype=dtype, crs="EPSG:4326",
                           transform=tr, nodata=nod) as dst:
            dst.write(np.full((ny, nx), val, dtype=dtype), 1)
    time = pd.date_range("2016-12-31 00:00", "2017-01-03 00:00", freq="1h")
    lat = np.arange(n + 0.5, s - 0.5, -0.25); lon = np.arange(w - 0.5, e + 0.5, 0.25)
    pr = np.zeros((time.size, lat.size, lon.size), "float32")
    # ERA5 convention (accumulation over the hour ENDING at the stamp): stamps 02:00..04:00 -> rain on [01:00, 04:00)
    for h in range(2, 2 + RAIN_HOURS):
        pr[time == pd.Timestamp(f"2017-01-01 {h:02d}:00")] = RAIN_MM_H
    xr.Dataset({"precip": (("time", "latitude", "longitude"), pr, {"units": "mm/h"})},
               coords={"time": time, "latitude": lat, "longitude": lon}).to_netcdf(data / "era5_synth.nc")
    (data / "data_catalog.yml").write_text(f"""meta:
  version: 1
  hydromt_version: ">=0.10"
  root: {data.as_posix()}

copdem30:
  data_type: RasterDataset
  driver: raster
  path: dep.tif
  crs: 4326
  rename:
    Band1: elevtn
    band_1: elevtn

esa_worldcover_2021:
  data_type: RasterDataset
  driver: raster
  path: landuse.tif
  crs: 4326
  rename:
    Band1: landuse
    band_1: landuse

cn_raster:
  data_type: RasterDataset
  driver: raster
  path: cn.tif
  crs: 4326
  rename:
    Band1: cn
    band_1: cn

era5_hourly:
  data_type: RasterDataset
  driver: netcdf
  path: era5_synth.nc
  crs: 4326
""", encoding="utf-8")
    raw = {"event": {"id": "EMSR999", "name": "Synth", "slug": "synth", "date": "2017-01-01"},
           "window": {"spinup_days": 0, "pre_event_days": 0, "post_event_days": 1},         # tref = tstart = 01-01, tstop = 01-02
           "bbox": {"west": w, "south": s, "east": e, "north": n}, "crs": {"epsg": 32634}, "grid": {"res": 100, "zmin": -2, "zmax": 250},
           "paths": {"work_dir": str(work), "deliverable_dir": str(work / "d"), "manning_lookup": str(a.repo / "skill" / "manning_lookup.csv")},
           "rain_source": "era5_hourly", "infiltration": {"enabled": True}, "harness_version": "v1.3"}
    cfg = EventCfg(raw=raw, config_path=Path("synth.yaml"))
    built = work / "built"; built.mkdir()
    yml = work / "sfincs_build.yml"; yml.write_text(build_model.render_build_yml(cfg), encoding="utf-8")
    res_b = subprocess.run([env["hydromt"], "build", "sfincs", str(built), "-i", str(yml), "-d", str(data / "data_catalog.yml"), "--fo"],
                           capture_output=True, text=True)
    (work / "hydromt.log").write_text(res_b.stdout + res_b.stderr, encoding="utf-8")
    if res_b.returncode != 0:
        sys.exit("hydromt build failed:\n" + res_b.stdout[-3000:] + res_b.stderr[-3000:])
    inp = (built / "sfincs.inp").read_text()
    if "scsfile" not in inp:
        sys.exit("build did not write scsfile")
    # point source in the middle of the plain, 20 m3/s between 06:00 and 18:00
    x0 = float([ln.split("=")[1] for ln in inp.splitlines() if ln.split("=")[0].strip() == "x0"][0])
    y0 = float([ln.split("=")[1] for ln in inp.splitlines() if ln.split("=")[0].strip() == "y0"][0])
    mmax = int([ln.split("=")[1] for ln in inp.splitlines() if ln.split("=")[0].strip() == "mmax"][0])
    nmax = int([ln.split("=")[1] for ln in inp.splitlines() if ln.split("=")[0].strip() == "nmax"][0])
    sx, sy = x0 + 100.0 * (mmax // 2 + 0.5), y0 + 100.0 * (nmax // 2 + 0.5)
    (built / "sfincs.src").write_text(f"{sx:.2f} {sy:.2f}\n")
    t = [0.0, Q_START_H * 3600 - 1, Q_START_H * 3600, Q_END_H * 3600, Q_END_H * 3600 + 1, 86400.0]
    q = [0.0, 0.0, Q_M3S, Q_M3S, 0.0, 0.0]
    (built / "sfincs.dis").write_text("".join(f"{ti:.0f} {qi:.3f}\n" for ti, qi in zip(t, q)))
    (built / "sfincs.inp").write_text(inp.rstrip() + "\nsrcfile = sfincs.src\ndisfile = sfincs.dis\n")
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "work": str(work), "cn": CN,
           "S_mm": round((1000 / CN - 10) * 25.4, 2), "Ia_mm": round(0.2 * (1000 / CN - 10) * 25.4, 2),
           "rain_mm": RAIN_MM_H * RAIN_HOURS, "source": {"q_m3s": Q_M3S, "hours": [Q_START_H, Q_END_H]}, "runs": {}}
    for flag in (0, 1):
        m = work / f"storecumprcp_{flag}"
        shutil.copytree(built, m)
        txt = (m / "sfincs.inp").read_text()
        (m / "sfincs.inp").write_text(txt.rstrip() + f"\nstorecumprcp = {flag}\ndtout = 3600\n")
        run = subprocess.run([env["sfincs_exe"]], cwd=str(m), capture_output=True, text=True)
        (m / "sfincs_run.log").write_text(run.stdout + run.stderr, encoding="utf-8")
        ds = xr.open_dataset(m / "sfincs_map.nc")
        zb = ds["zb"].values; msk = ds["msk"].values; zs = ds["zs"].values
        h = np.where(np.isfinite(zs), np.maximum(zs - zb[None], 0.0), 0.0); h[:, msk == 0] = 0.0
        area_m2 = float((msk > 0).sum()) * 100.0 * 100.0
        V = (h * 1e4).reshape(h.shape[0], -1).sum(axis=1)
        expected = scs_runoff_mm(RAIN_MM_H * RAIN_HOURS, CN) / 1000.0 * area_m2 + Q_M3S * (Q_END_H - Q_START_H) * 3600
        tt = pd.to_datetime(ds["time"].values)
        out["runs"][f"storecumprcp_{flag}"] = {
            "active_cells": int((msk > 0).sum()), "msk2_cells": int((msk == 2).sum()), "area_km2": area_m2 / 1e6,
            "volume_m3_hourly": {str(tt[i])[5:16]: round(float(V[i]), 1) for i in range(len(V))}, "simulated_runoff_mm_from_rain": round(float(V[np.searchsorted(tt, pd.Timestamp("2017-01-01 06:00"))]) / area_m2 * 1000, 3), "expected_runoff_mm_scs": round(scs_runoff_mm(RAIN_MM_H * RAIN_HOURS, CN), 3),
            "volume_end_m3": round(float(V[-1]), 1), "expected_end_m3_correct_scs": round(expected, 1),
            "ratio_end_to_expected": round(float(V[-1]) / expected, 4),
            "log_infiltration_line": [ln.strip() for ln in run.stdout.splitlines() if "nfiltration" in ln][:3]}
        ds.close()
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "runs"}, indent=1))
    for k, r in out["runs"].items():
        print(k, "end volume", r["volume_end_m3"], "expected", r["expected_end_m3_correct_scs"], "ratio", r["ratio_end_to_expected"], r["log_infiltration_line"])
    if not a.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
