"""Evaluation-mask exclusion for harness v1.4 scoring (GO-C decision 3, Papaioannou 2026-10-19).

Identical rule for every event: the evaluation universe (msk > 0 within the AOI union) loses
    EXCLUDED = WorldCover-2021 class 80 (permanent water bodies, sampled at the model cell centre)
              UNION the v1.4 open-sea mask (build_model.open_sea_split on the v1.3-style active mask + dep:
                    active dep <= 0 cells 4-connected to the grid edge — the cells prepare_coastal_exclusion
                    deactivates plus the one-cell coastal ring it keeps as msk = 2).
The exclusion is applied to BOTH sides (model wet field and EMS truth); validate_event_v2 reports the observed-flood
area it removes. One GeoTIFF per event (north-up, uint8, 1 = excluded) is produced once and used both for the
v1.4 runs and for re-scoring the published v1.3 outputs on the same grid (the mask-only effect).

CLI:
  python eval_exclusion.py --gis <model>/gis --worldcover <esa_worldcover_2021.vrt> --out <event>_exclusion.tif
                           [--open-sea-tif <open_sea_mask.tif from a v1.4 build>] [--out-json stats.json]
`--gis` derives the open sea from a v1.3-style model (msk.tif >= 1, dep.tif); `--open-sea-tif` takes the raster a
v1.4 build wrote (prepare_coastal_exclusion). When both are given they must agree (the symmetric difference is
reported and must be empty unless --allow-diff).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import numpy as np

_SKILL = Path(os.environ.get("SFINCS_SKILL_DIR", str(Path(__file__).resolve().parents[1] / "skill")))
sys.path.insert(0, str(_SKILL / "scripts"))

WC_PERMANENT_WATER = 80


def _read_tif(path: Path):
    import rasterio
    with rasterio.open(path) as src:
        return src.read(1), src.transform, src.crs, src.nodata


def open_sea_from_gis(gis_dir):
    """Open sea (incl. the coastal ring) from a model's hydromt gis/msk.tif + gis/dep.tif (north-up).
    Returns (bool array, transform, crs)."""
    from build_model import open_sea_split
    gis_dir = Path(gis_dir)
    msk, tr, crs, _ = _read_tif(gis_dir / "msk.tif")
    dep, tr2, _, nod = _read_tif(gis_dir / "dep.tif")
    if msk.shape != dep.shape or tr != tr2:
        raise ValueError(f"msk.tif and dep.tif differ in grid under {gis_dir}")
    dep = dep.astype(float)
    if nod is not None:
        dep = np.where(dep == nod, np.nan, dep)
    _, open_sea, _ = open_sea_split(msk >= 1, dep)
    return open_sea.astype(bool), tr, crs


def read_open_sea_tif(path):
    arr, tr, crs, _ = _read_tif(Path(path))
    return arr == 1, tr, crs


def worldcover80_at_centres(wc_path, transform, shape, epsg) -> np.ndarray:
    """WorldCover class 80 at the centre of every model cell (nearest 10-m pixel), as a north-up bool array
    of `shape` on the grid given by `transform` (model CRS `epsg`)."""
    import rasterio
    from pyproj import Transformer
    ny, nx = shape
    rows, cols = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij")
    xs, ys = rasterio.transform.xy(transform, rows.ravel(), cols.ravel(), offset="center")
    lon, lat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(np.asarray(xs), np.asarray(ys))
    out = np.zeros(ny * nx, dtype=bool)
    with rasterio.open(wc_path) as src:
        step = 200_000
        for i in range(0, lon.size, step):
            vals = np.array([v[0] for v in src.sample(zip(lon[i:i + step], lat[i:i + step]))])
            out[i:i + step] = vals == WC_PERMANENT_WATER
    return out.reshape(ny, nx)


def union_exclusion(open_sea, wc80, cell_km2: float):
    open_sea = np.asarray(open_sea, bool); wc80 = np.asarray(wc80, bool)
    ex = open_sea | wc80
    st = {"open_sea_cells": int(open_sea.sum()), "wc80_cells": int(wc80.sum()),
          "wc80_land_cells": int((wc80 & ~open_sea).sum()), "union_cells": int(ex.sum()),
          "open_sea_km2": round(float(open_sea.sum() * cell_km2), 4), "wc80_km2": round(float(wc80.sum() * cell_km2), 4),
          "union_km2": round(float(ex.sum() * cell_km2), 4)}
    return ex, st


def write_mask_tif(path, arr, transform, crs):
    import rasterio
    arr = np.asarray(arr, bool).astype("uint8")
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1, dtype="uint8",
                       crs=crs, transform=transform, nodata=255, compress="deflate") as dst:
        dst.write(arr, 1)


def read_mask_for_grid(path, s) -> np.ndarray:
    """Read a north-up mask GeoTIFF onto the sfincs_map.nc grid described by `s` (open_sfincs dict with 2-D x, y,
    dx, dy). Checks shape and cell centres (0.01 m) and flips to the map's row order (y ascending in the outputs)."""
    arr, tr, _, _ = _read_tif(Path(path))
    x2, y2 = np.asarray(s["x"]), np.asarray(s["y"])
    ny, nx = x2.shape
    if arr.shape != (ny, nx):
        raise ValueError(f"exclusion raster {arr.shape} does not match the model grid {(ny, nx)}")
    # north-up raster cell centres
    xr0 = tr.c + tr.a * 0.5; yr_top = tr.f + tr.e * 0.5
    x_cols = xr0 + tr.a * np.arange(nx)
    y_rows = yr_top + tr.e * np.arange(ny)                      # descending
    ascending = y2[1, 0] > y2[0, 0] if ny > 1 else False
    y_map = y2[:, 0]; x_map = x2[0, :]
    y_cmp = y_rows[::-1] if ascending else y_rows
    if not (np.allclose(x_cols, x_map, atol=0.01) and np.allclose(y_cmp, y_map, atol=0.01)):
        raise ValueError("exclusion raster cell centres do not match the model grid")
    m = arr == 1
    return m[::-1, :].copy() if ascending else m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gis", type=Path, help="<model>/gis of a v1.3-style model (msk.tif, dep.tif)")
    ap.add_argument("--open-sea-tif", type=Path, help="open_sea_mask.tif written by a v1.4 build")
    ap.add_argument("--worldcover", required=True, type=Path)
    ap.add_argument("--epsg", type=int, default=None, help="model EPSG (default: from the rasters)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--allow-diff", action="store_true")
    a = ap.parse_args()
    if not a.gis and not a.open_sea_tif:
        sys.exit("give --gis and/or --open-sea-tif")
    sea_gis = sea_tif = None
    if a.gis:
        sea_gis, tr, crs = open_sea_from_gis(a.gis)
    if a.open_sea_tif:
        sea_tif, tr2, crs2 = read_open_sea_tif(a.open_sea_tif)
        if sea_gis is not None and (sea_tif.shape != sea_gis.shape or tr2 != tr):
            sys.exit("--gis and --open-sea-tif are on different grids")
        if sea_gis is None:
            tr, crs = tr2, crs2
    open_sea = sea_tif if sea_tif is not None else sea_gis
    epsg = a.epsg or crs.to_epsg()
    cell_km2 = abs(tr.a * tr.e) / 1e6
    wc80 = worldcover80_at_centres(a.worldcover, tr, open_sea.shape, epsg)
    ex, st = union_exclusion(open_sea, wc80, cell_km2)
    st.update({"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "out": str(a.out),
               "open_sea_source": str(a.open_sea_tif or a.gis), "worldcover": str(a.worldcover), "epsg": epsg,
               "wc80_sampling": "class 80 at the model cell centre (nearest 10-m pixel)",
               "open_sea_definition": "build_model.open_sea_split: active dep<=0 cells 4-connected to the grid edge (incl. the coastal ring)",
               "grid": {"shape": list(open_sea.shape), "cell_m": [abs(tr.a), abs(tr.e)], "transform": list(tr)[:6]}})
    if sea_gis is not None and sea_tif is not None:
        diff = int((sea_gis ^ sea_tif).sum())
        st["open_sea_gis_vs_tif_symmetric_difference_cells"] = diff
        st["open_sea_gis_cells"] = int(sea_gis.sum()); st["open_sea_tif_cells"] = int(sea_tif.sum())
        if diff and not a.allow_diff:
            sys.exit(f"open sea from --gis and --open-sea-tif differ in {diff} cells (use --allow-diff to proceed)")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    write_mask_tif(a.out, ex, tr, crs)
    if a.out_json:
        a.out_json.write_text(json.dumps(st, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in st.items() if k != "grid"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
