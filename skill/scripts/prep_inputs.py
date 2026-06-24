"""Clean the ERA5 + GloFAS netCDFs, copy the Manning lookup, and write
data_catalog.yml from the bundled template.
"""
from __future__ import annotations

import shutil
import string
import subprocess
import sys
import zipfile
from pathlib import Path

from _common import SKILL_DIR, load_config, ensure_dir


def main():
    cfg = load_config()
    import xarray as xr  # imported after GDAL_DATA is set

    data = ensure_dir(cfg.paths["data_dir"])
    era_zip = data / f"era5_{cfg.event_slug}_raw.zip"
    era_dir = ensure_dir(cfg.paths["era5_extracted_dir"])
    era_accum = era_dir / "data_stream-oper_stepType-accum.nc"
    era_inst = era_dir / "data_stream-oper_stepType-instant.nc"

    # 1) ERA5
    if era_zip.exists():
        with zipfile.ZipFile(era_zip) as zf:
            zf.extractall(era_dir)
        print(f"  ERA5 unzipped: {[p.name for p in era_dir.glob('*.nc')]}")
    if era_accum.exists() and era_inst.exists():
        ds = xr.merge([xr.open_dataset(era_accum), xr.open_dataset(era_inst)],
                      compat="override")
    else:
        # Fallback: a single NetCDF without the accum/instant split
        nc_files = list(era_dir.glob("*.nc"))
        if len(nc_files) == 1:
            ds = xr.open_dataset(nc_files[0])
        elif nc_files:
            ds = xr.merge([xr.open_dataset(f) for f in nc_files], compat="override")
        else:
            sys.exit(f"no ERA5 NetCDF in {era_dir} — run download_era5.py first")
    if "valid_time" in ds.coords:
        ds = ds.rename({"valid_time": "time"})
    if "tp" in ds:
        ds["tp"] = ds["tp"] * 1000.0
        ds["tp"].attrs.update({"units": "mm/h", "long_name": "Total precipitation"})
    rename = {k: v for k, v in {
        "tp": "precip", "msl": "press_msl", "u10": "wind10_u", "v10": "wind10_v"
    }.items() if k in ds}
    ds = ds.rename(rename)
    for v in ["number", "expver"]:
        if v in ds.coords:
            ds = ds.drop_vars(v)
        if v in ds.variables:
            ds = ds.drop_vars(v)
    era_clean = data / f"era5_{cfg.event_slug}.nc"
    ds.to_netcdf(era_clean, engine="scipy", format="NETCDF3_64BIT")
    print(f"ERA5 cleaned: {era_clean.name} ({era_clean.stat().st_size/1e6:.2f} MB)  "
          f"vars: {list(ds.data_vars)}")

    # 2) GloFAS
    gf_raw = data / f"glofas_{cfg.event_slug}.nc"
    if gf_raw.exists():
        gl = xr.open_dataset(gf_raw)
        if "valid_time" in gl.coords:
            gl = gl.rename({"valid_time": "time"})
        for v in ["surface"]:
            if v in gl.coords:
                gl = gl.drop_vars(v)
        if "dis24" in gl:
            gl["dis24"].attrs.update({"units": "m3/s",
                                      "long_name": "River discharge (24h mean)"})
            gl = gl.rename({"dis24": "discharge"})
        gf_clean = data / f"glofas_{cfg.event_slug}_clean.nc"
        gl.to_netcdf(gf_clean, engine="scipy", format="NETCDF3_64BIT")
        print(f"GloFAS cleaned: {gf_clean.name} ({gf_clean.stat().st_size/1e6:.2f} MB)")
    else:
        print(f"WARN: GloFAS source {gf_raw} not present — run download_glofas.py first")

    # 3) Copy/locate the Manning lookup table
    mln_dst = cfg.paths["work_dir"] / "manning_lookup.csv"
    src = cfg.paths["manning_lookup"]
    if src.resolve() != mln_dst.resolve():
        shutil.copy2(src, mln_dst)
    print(f"manning lookup: {mln_dst}")

    # 4) Write data_catalog.yml from template
    tmpl = (SKILL_DIR / "templates" / "data_catalog.yml.tmpl").read_text()
    rendered = string.Template(tmpl).substitute({
        "data_root": str(data).replace("\\", "/"),
        "event": cfg.event_slug,
        "tstart_str": cfg.tstart.strftime("%B %d %Y"),
        "tstop_str": cfg.tstop.strftime("%B %d %Y"),
    })
    out_cat = cfg.paths["work_dir"] / "data_catalog.yml"
    out_cat.write_text(rendered, encoding="utf-8")
    print(f"catalog: {out_cat}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
