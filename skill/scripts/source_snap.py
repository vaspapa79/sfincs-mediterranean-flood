"""R3 source snap (harness v1.4.2, CODE-15 B (3), 2026-10-20).

Rule R3 reads "GloFAS-v4 at named inflow points, snapped to the lowest-z_b channel cell"; until v1.4.1 the pipeline wrote the
YAML coordinate itself to sfincs.src (no snap, two sources on inactive cells). Under harness v1.4 a source is injected at
the lowest-z_b ACTIVE (msk = 1) CHANNEL cell within SNAP_RADIUS_M of the YAML injection point, where "channel" means a D8
upstream area of at least CHANNEL_FRACTION of the largest upstream area inside the radius — the local thalweg, so a pit or
a floodplain depression beside the river does not win. No active cell inside the radius is a hard error (NoActiveCellError):
the point is misplaced and must be resolved in the configuration, never silently moved further.

The upstream area comes from a D8 network of the Copernicus DEM tiles of the run mosaicked onto the model grid with a pad
(rivers entering the domain keep their accumulation), pyflwdir; when no DEM tiles are present the model's own dep is used
(reported as such).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

SNAP_RADIUS_M = 1000.0
CHANNEL_FRACTION = 0.5
DEM_PAD_M = 10000.0


class NoActiveCellError(RuntimeError):
    """No active model cell within the snap radius of a source point (v1.4.2: hard error, the configuration must be fixed)."""


def cell_centres(transform, shape):
    rows, cols = np.indices(shape)
    return transform.c + (cols + 0.5) * transform.a, transform.f + (rows + 0.5) * transform.e


def snap_source(dep: np.ndarray, msk: np.ndarray, uparea: np.ndarray, transform, x: float, y: float,
                radius_m: float = SNAP_RADIUS_M, channel_fraction: float = CHANNEL_FRACTION) -> dict:
    """Lowest-z_b active channel cell within radius_m of (x, y); returns row/col, the cell centre, z_b, distance and the
    upstream-area context. Raises NoActiveCellError when no active cell lies inside the radius."""
    xs, ys = cell_centres(transform, dep.shape)
    dist = np.hypot(xs - x, ys - y)
    active = (msk == 1) & np.isfinite(dep)
    cand = active & (dist <= radius_m)
    if not cand.any():
        raise NoActiveCellError(f"no active model cell within {radius_m:.0f} m of ({x:.1f}, {y:.1f})")
    up = np.where(np.isfinite(uparea), uparea, 0.0)
    up_max = float(up[cand].max())
    chan = cand & (up >= channel_fraction * up_max) if up_max > 0 else cand
    k = int(np.argmin(np.where(chan, dep, np.inf)))
    r, c = np.unravel_index(k, dep.shape)
    return {"row": int(r), "col": int(c), "x": float(xs[r, c]), "y": float(ys[r, c]), "zb": float(dep[r, c]), "distance_m": float(dist[r, c]),
            "uparea_km2": float(up[r, c]), "max_uparea_within_radius_km2": up_max, "n_active_within_radius": int(cand.sum()),
            "n_channel_cells": int(chan.sum()), "radius_m": float(radius_m), "channel_fraction": float(channel_fraction)}


def dem_uparea_on_grid(dem_dir: Path | None, epsg: int, transform, shape, pad_m: float = DEM_PAD_M, fallback_dep: np.ndarray | None = None):
    """D8 upstream area [km2] on the model grid from the Copernicus DEM tiles in dem_dir (mosaicked with a pad, average
    resampling), or from fallback_dep (the model's own elevation) when no tiles exist."""
    import pyflwdir
    res = float(abs(transform.a))
    tiles = sorted(Path(dem_dir).glob("*.tif")) if dem_dir else []
    if tiles:
        import rasterio
        from rasterio.transform import from_origin
        from rasterio.warp import Resampling, reproject
        x0 = transform.c - pad_m; y1 = transform.f + pad_m
        w = int(math.ceil((shape[1] * res + 2 * pad_m) / res)); h = int(math.ceil((shape[0] * res + 2 * pad_m) / res))
        Td = from_origin(x0, y1, res, res)
        dem = np.full((h, w), np.nan, dtype=np.float32)
        for t in tiles:
            with rasterio.open(t) as s:
                tmp = np.full((h, w), np.nan, dtype=np.float32)
                reproject(rasterio.band(s, 1), tmp, dst_transform=Td, dst_crs=f"EPSG:{epsg}", dst_nodata=np.nan, src_nodata=s.nodata, resampling=Resampling.average)
                m = np.isfinite(tmp); dem[m] = tmp[m]
        flw = pyflwdir.from_dem(data=dem, nodata=np.nan, transform=Td, latlon=False)
        up = flw.upstream_area(unit="km2")
        r0 = int(round((Td.f - transform.f) / res)); c0 = int(round((transform.c - Td.c) / res))
        return np.asarray(up[r0:r0 + shape[0], c0:c0 + shape[1]], dtype=float)
    if fallback_dep is None:
        raise FileNotFoundError(f"no DEM tiles in {dem_dir} and no fallback elevation given")
    flw = pyflwdir.from_dem(data=np.asarray(fallback_dep, dtype=np.float32), nodata=np.nan, transform=transform, latlon=False)
    return np.asarray(flw.upstream_area(unit="km2"), dtype=float)
