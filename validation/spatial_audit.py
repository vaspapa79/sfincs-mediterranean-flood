"""Spatial audit: where is the model wetting vs EMS observed vs AOI?

Per event, dump:
  * Model wet (h>0.10m) area inside vs outside the EMS AOI union
  * EMS observed wet area inside the AOI union
  * EMS AOI bbox (UTM)
  * Q injection point coords (UTM and lat/lon)
  * Per-AOI: model wet vs obs wet
"""
from __future__ import annotations

import os
# GDAL_DATA: derive from the active conda env (portable across machines); if no
# env is active, let rasterio fall back to its bundled data.
_conda_prefix = os.environ.get("CONDA_PREFIX")
if _conda_prefix:
    os.environ.setdefault("GDAL_DATA", os.path.join(_conda_prefix, "Library", "share", "gdal"))

import sys
from pathlib import Path

import numpy as np
import xarray as xr
import pyogrio
import pyproj
import rasterio.features
from rasterio.transform import from_bounds
from shapely import from_wkb
from shapely.ops import transform as shp_transform

# _anim_common lives in the repo's own skill/scripts. Override with
# SFINCS_SKILL_DIR if you keep the pipeline skill elsewhere.
SKILL = Path(os.environ.get("SFINCS_SKILL_DIR",
                            str(Path(__file__).resolve().parents[1] / "skill")))
sys.path.insert(0, str(SKILL / "scripts"))
from _anim_common import open_sfincs

# Author dev-audit tool: reads the local multi-GB SFINCS output runs, which are
# NOT part of the public repo. Point SFINCS_IMPL_DIR at your outputs tree to run it.
ROOT = Path(os.environ.get("SFINCS_IMPL_DIR",
                           str(Path(__file__).resolve().parents[1] / "implementation")))

EVENTS = {
    "mandra":    {"dir": "mandra_sfincs_enhanced",    "epsg": 32634},
    "strymonas": {"dir": "emsr122_sfincs_enhanced",   "epsg": 32634},
    "pineios":   {"dir": "pineios_sfincs_enhanced",   "epsg": 32634},
}


def list_shps(d, patterns):
    out, seen = [], set()
    if not d.exists():
        return out
    for pat in patterns:
        for p in d.rglob(pat):
            if p in seen:
                continue
            seen.add(p); out.append(p)
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
            print(f"  ERROR {shp.name}: {e}")
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


def audit(slug, info):
    print(f"\n{'='*70}\n{slug.upper()} SPATIAL AUDIT\n{'='*70}")
    model = ROOT / info["dir"] / "model"
    ems_dir = ROOT / info["dir"] / "data" / "ems_polygons"

    s = open_sfincs(model)
    msk = (s["msk"] > 0)
    cell_km2 = s["cell_area_km2"]
    print(f"Grid: {s['nx']}x{s['ny']}, dx={s['dx']}m, active={msk.sum()*cell_km2:.1f} km²")

    # Observed flood + AOIs
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
    ems_wet = rasterise_polys(obs_shps, s["x"], s["y"], info["epsg"],
                              s["dx"], s["dy"])
    aoi_union = rasterise_polys(aoi_shps, s["x"], s["y"], info["epsg"],
                                s["dx"], s["dy"]) if aoi_shps else msk

    # Hmax
    zsmax = s["ds"]["zsmax"].max(dim="timemax").values
    hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
    model_wet = (hmax > 0.10) & msk

    # Categories
    eval_mask = msk & aoi_union
    print(f"\nEMS AOI union cap active: {eval_mask.sum()*cell_km2:.1f} km²")
    print(f"EMS observed wet:        {ems_wet.sum()*cell_km2:.1f} km² (total)")
    print(f"EMS observed in AOI:     {(ems_wet & aoi_union).sum()*cell_km2:.1f} km²")
    print(f"EMS observed in eval:    {(ems_wet & eval_mask).sum()*cell_km2:.1f} km²")
    print(f"\nModel wet (h>0.10m, full active): {model_wet.sum()*cell_km2:.1f} km²")
    print(f"Model wet inside AOI union:        {(model_wet & aoi_union).sum()*cell_km2:.1f} km²")
    print(f"Model wet outside AOI union:       {(model_wet & ~aoi_union & msk).sum()*cell_km2:.1f} km²")

    # Contingency on eval mask
    tp = int((model_wet & ems_wet & eval_mask).sum())
    fp = int((model_wet & ~ems_wet & eval_mask).sum())
    fn = int((~model_wet & ems_wet & eval_mask).sum())
    print(f"\nContingency on eval mask (h>0.10m strict):")
    print(f"  TP={tp}  FP={fp}  FN={fn}")
    print(f"  CSI={tp/(tp+fp+fn) if tp+fp+fn else float('nan'):.3f}")
    print(f"  HR ={tp/(tp+fn) if tp+fn else float('nan'):.3f}")
    print(f"  FAR={fp/(tp+fp) if tp+fp else float('nan'):.3f}")
    print(f"  Bias={(tp+fp)/(tp+fn) if tp+fn else float('nan'):.2f}")

    # Per AOI
    print(f"\nPer-AOI breakdown (deduplicate by AOI base name):")
    seen_aoi_names = set()
    for aoi_shp in aoi_shps:
        base = aoi_shp.name.split("_area")[0]  # keep just the AOI key
        if base in seen_aoi_names:
            continue
        seen_aoi_names.add(base)
        a_mask = rasterise_polys([aoi_shp], s["x"], s["y"], info["epsg"],
                                 s["dx"], s["dy"])
        local = msk & a_mask
        if not local.any():
            continue
        m_tp = int((model_wet & ems_wet & local).sum())
        m_fp = int((model_wet & ~ems_wet & local).sum())
        m_fn = int((~model_wet & ems_wet & local).sum())
        m_obs = int((ems_wet & local).sum())
        m_mod = int((model_wet & local).sum())
        area = local.sum() * cell_km2
        if not area or not (m_tp + m_fn):
            continue
        print(f"  {aoi_shp.name[:55]:55s}  area={area:6.0f}km² obs={m_obs*cell_km2:6.1f}km²"
              f" mod={m_mod*cell_km2:6.1f}km² CSI={m_tp/(m_tp+m_fp+m_fn) if m_tp+m_fp+m_fn else 0:.3f}"
              f" HR={m_tp/(m_tp+m_fn):.3f}")


def main():
    for slug, info in EVENTS.items():
        audit(slug, info)


if __name__ == "__main__":
    main()
