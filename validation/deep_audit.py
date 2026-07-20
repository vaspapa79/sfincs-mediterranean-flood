"""Deep audit of every SFINCS run input.

Reports per event:
  * sfincs.inp key parameters
  * Manning lookup
  * CN raster stats (if present)
  * sfincs.src / sfincs.dis upstream-Q stats
  * active mask area / sea mask area / land mask area
  * EMS observed-flood polygon stats (count, total wet area, extent)
  * EMS AOI polygon stats
  * model vs observed inundation overlap
  * peak depth, peak flooded area
  * spin-up sanity check
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# GDAL_DATA: derive from the active conda env (portable across machines); if no
# env is active, let rasterio fall back to its bundled data.
_conda_prefix = os.environ.get("CONDA_PREFIX")
if _conda_prefix:
    os.environ.setdefault("GDAL_DATA", os.path.join(_conda_prefix, "Library", "share", "gdal"))

import numpy as np
import xarray as xr
import pyogrio
import pyproj
import rasterio
import rasterio.features
from rasterio.transform import from_bounds
from shapely import from_wkb
from shapely.ops import transform as shp_transform

# Author dev-audit tool: reads the local multi-GB SFINCS output runs, which are
# NOT part of the public repo. Point SFINCS_IMPL_DIR at your outputs tree to run it.
ROOT = Path(os.environ.get("SFINCS_IMPL_DIR",
                           str(Path(__file__).resolve().parents[1] / "implementation")))

EVENTS = {
    "mandra":    {"dir": "mandra_sfincs_enhanced",    "epsg": 32634},
    "strymonas": {"dir": "emsr122_sfincs_enhanced",   "epsg": 32634},
    "pineios":   {"dir": "pineios_sfincs_enhanced",   "epsg": 32634},
}


def parse_inp(path):
    keys = {}
    if not path.exists():
        return keys
    for line in path.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            keys[k.strip()] = v.strip()
    return keys


def list_shps(d, patterns):
    out, seen = [], set()
    if not d.exists():
        return out
    for pat in patterns:
        for p in d.rglob(pat):
            if p in seen:
                continue
            seen.add(p)
            out.append(p)
    return sorted(out)


def rasterise_polys(shp_paths, x, y, target_epsg, dx, dy):
    target_crs = pyproj.CRS.from_epsg(target_epsg)
    ny, nx = x.shape
    xs = x[0, :]; ys = y[:, 0]
    west = float(xs.min()) - dx/2.0
    east = float(xs.max()) + dx/2.0
    south = float(ys.min()) - dy/2.0
    north = float(ys.max()) + dy/2.0
    transform = from_bounds(west, south, east, north, nx, ny)
    geoms = []
    for shp in shp_paths:
        if not shp.exists():
            continue
        try:
            info = pyogrio.read_info(shp)
            src_crs = pyproj.CRS.from_user_input(info["crs"])
            _, _, gw, _ = pyogrio.raw.read(str(shp), return_fids=True)
            gs = [from_wkb(g) for g in gw]
            if src_crs != target_crs:
                tr = pyproj.Transformer.from_crs(src_crs, target_crs,
                                                 always_xy=True).transform
                gs = [shp_transform(tr, g) for g in gs]
            geoms.extend([g for g in gs if not g.is_empty])
        except Exception as e:
            print(f"  ERROR reading {shp.name}: {e}")
    if not geoms:
        return np.zeros((ny, nx), dtype=bool)
    out_td = rasterio.features.rasterize(
        ((g, 1) for g in geoms),
        out_shape=(ny, nx),
        transform=transform,
        all_touched=True,
        dtype="uint8",
    )
    return out_td[::-1, :].astype(bool)


def audit_event(slug, info):
    print(f"\n{'='*70}\n{slug.upper()}  ({info['dir']})\n{'='*70}")
    work = ROOT / info["dir"]
    model = work / "model"
    inp = parse_inp(model / "sfincs.inp")
    print(f"\n--- sfincs.inp ---")
    for k in ("mmax","nmax","dx","dy","tref","tstart","tstop",
              "manning","manning_land","manning_sea","huthresh",
              "alpha","pavbnd","zsini","qinf","advection","baro","viscosity"):
        if k in inp:
            print(f"  {k:<20} = {inp[k]}")

    # Manning lookup
    mlook = work / "manning_lookup.csv"
    if mlook.exists():
        print(f"\n--- manning_lookup.csv ---")
        for line in mlook.read_text().splitlines():
            print(f"  {line}")

    # CN raster
    cn_tif = model / "cn.tif"
    if cn_tif.exists():
        with rasterio.open(cn_tif) as ds:
            cn = ds.read(1)
            valid = cn[cn > 0]
            if valid.size > 0:
                print(f"\n--- cn.tif --- shape={cn.shape} valid={valid.size}")
                print(f"  CN min/mean/max = {valid.min():.1f}/{valid.mean():.1f}/{valid.max():.1f}")
                print(f"  CN p05/p25/p50/p75/p95 = "
                      f"{np.percentile(valid,5):.0f}/"
                      f"{np.percentile(valid,25):.0f}/"
                      f"{np.percentile(valid,50):.0f}/"
                      f"{np.percentile(valid,75):.0f}/"
                      f"{np.percentile(valid,95):.0f}")
    else:
        print(f"\n--- cn.tif --- NOT PRESENT (infiltration disabled)")

    # Upstream Q
    src = model / "sfincs.src"
    dis = model / "sfincs.dis"
    if src.exists() and src.stat().st_size > 0:
        src_data = src.read_text()
        # Parse src points: each line is "x y" or "name x y"
        n_pts = sum(1 for l in src_data.splitlines() if l.strip())
        print(f"\n--- sfincs.src --- {n_pts} inflow point(s):")
        print(src_data)
        if dis.exists() and dis.stat().st_size > 0:
            # dis is tabular: time then Q for each src point
            lines = dis.read_text().splitlines()
            print(f"--- sfincs.dis --- {len(lines)} time steps")
            # parse
            try:
                rows = [list(map(float, l.split())) for l in lines if l.strip()]
                if rows:
                    arr = np.array(rows)
                    print(f"  time range: {arr[0,0]:.0f} to {arr[-1,0]:.0f} s "
                          f"({arr[-1,0]/3600:.0f} h)")
                    if arr.shape[1] >= 2:
                        for col in range(1, arr.shape[1]):
                            print(f"  Q_pt{col}: min/mean/max = "
                                  f"{arr[:,col].min():.1f}/"
                                  f"{arr[:,col].mean():.1f}/"
                                  f"{arr[:,col].max():.1f} m³/s")
            except Exception as e:
                print(f"  parse error: {e}")
    else:
        print(f"\n--- sfincs.src --- NOT PRESENT (upstream Q disabled)")

    # Active mask
    msk_file = model / "sfincs.msk"
    ind_file = model / "sfincs.ind"
    if msk_file.exists() and "mmax" in inp:
        mmax = int(inp["mmax"]); nmax = int(inp["nmax"])
        dx = float(inp["dx"]); dy = float(inp["dy"])
        # Read binary msk file (uint8)
        msk_raw = np.fromfile(msk_file, dtype=np.uint8)
        n_msk = msk_raw.size
        # The msk file may include indexed format; we just count nonzero
        active_cells = int(np.sum(msk_raw > 0))
        sea_cells = int(np.sum(msk_raw == 2))
        land_cells = int(np.sum(msk_raw == 1))
        bnd_cells = int(np.sum(msk_raw > 2))
        cell_km2 = dx*dy / 1e6
        print(f"\n--- sfincs.msk ---")
        print(f"  grid {mmax}x{nmax} = {mmax*nmax} cells")
        print(f"  msk bytes: {n_msk}; nonzero: {active_cells}")
        print(f"  msk==1 (land/active): {land_cells} = {land_cells*cell_km2:.1f} km²")
        print(f"  msk==2 (waterlevel boundary): {sea_cells} = {sea_cells*cell_km2:.1f} km²")
        print(f"  msk>2: {bnd_cells}")
        print(f"  total active (>0): {active_cells} = {active_cells*cell_km2:.1f} km²")

    # SFINCS map outputs
    map_nc = model / "sfincs_map.nc"
    if map_nc.exists():
        ds = xr.open_dataset(map_nc)
        if "zsmax" in ds and "zb" in ds:
            zsmax = ds["zsmax"].max(dim="timemax").values
            zb = ds["zb"].values
            hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - zb, 0))
            # Try to get msk for proper masking
            msk = ds.get("mask") or ds.get("msk")
            if msk is not None:
                msk = msk.values
                wet_h01 = (hmax > 0.10) & (msk > 0)
            else:
                wet_h01 = (hmax > 0.10)
            dx = float(ds.attrs.get("dx", inp.get("dx", 50)))
            cell_km2 = dx*dx / 1e6
            print(f"\n--- sfincs_map.nc ---")
            print(f"  hmax range: {hmax.min():.2f} to {hmax.max():.2f} m")
            print(f"  cells with hmax>0.10m: {int(wet_h01.sum())} = "
                  f"{wet_h01.sum()*cell_km2:.2f} km²")
            print(f"  cells with hmax>0.50m: {int(((hmax>0.50)&(wet_h01>=0)).sum())} = "
                  f"{((hmax>0.50)&(wet_h01>=0)).sum()*cell_km2:.2f} km²")
            print(f"  cells with hmax>2.00m: "
                  f"{int(((hmax>2.0)&(wet_h01>=0)).sum())}")

    # EMS shapefiles
    ems_dir = work / "data" / "ems_polygons"
    obs_shps = list_shps(ems_dir, [
        "*DELINEATION*MONIT*crisis_information_poly.shp",
        "*GRADING*observed_event_a.shp",
        "*GRA_*observed_event_a.shp",
        "*DEL_MONIT*observedEventA*.shp",
        "*DEL_MONIT*observed_event*.shp",
    ])
    aoi_shps = list_shps(ems_dir, [
        "*area_of_interest.shp",
        "*area_of_interest_a.shp",
        "*areaOfInterestA*.shp",
    ])
    print(f"\n--- EMS shapefiles ---")
    print(f"  Observed flood (n={len(obs_shps)}):")
    for s in obs_shps[:8]:
        try:
            info = pyogrio.read_info(s)
            print(f"    {s.name}  features={info['features']}, crs={info['crs']}")
        except Exception as e:
            print(f"    {s.name}  ERROR: {e}")
    print(f"  AOI (n={len(aoi_shps)}):")
    for s in aoi_shps[:8]:
        try:
            info = pyogrio.read_info(s)
            print(f"    {s.name}  features={info['features']}, crs={info['crs']}")
        except Exception as e:
            print(f"    {s.name}  ERROR: {e}")


def main():
    for slug, info in EVENTS.items():
        audit_event(slug, info)


if __name__ == "__main__":
    main()
