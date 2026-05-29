"""Shared helpers for the animation + MP4 + QC scripts.

Computes the SFINCS canvas extents, h(t), flooded km², max depth, ERA5
cum rain series, GloFAS peak Q on a reach, and loads EMS / AOI /
hydrography polygons.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import xarray as xr


def open_sfincs(model_dir: Path):
    dm = xr.open_dataset(model_dir / "sfincs_map.nc")
    zs = dm["zs"].values
    zb = dm["zb"].values
    msk = dm["msk"].values
    x = dm["x"].values
    y = dm["y"].values
    times = dm["time"].values
    nt, ny, nx = zs.shape
    dx = float(x[0, 1] - x[0, 0])
    dy = abs(float(y[1, 0] - y[0, 0]))
    xmin = float(x.min()) - dx / 2
    xmax = float(x.max()) + dx / 2
    ymin = float(y.min()) - dy / 2
    ymax = float(y.max()) + dy / 2
    zs_f = np.where(np.isfinite(zs), zs, zb[None, :, :])
    h = np.maximum(zs_f - zb[None, :, :], 0)
    h[:, msk == 0] = 0
    return {
        "ds": dm, "zs": zs, "zb": zb, "msk": msk,
        "x": x, "y": y, "times": times, "h": h,
        "nt": nt, "ny": ny, "nx": nx, "dx": dx, "dy": dy,
        "xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax,
        "cell_area_km2": (dx * dy) / 1e6,
    }


def stats_per_frame(s: dict):
    h = s["h"]; msk = s["msk"]
    nt = s["nt"]
    flooded_km2 = np.array([float(((h[t] > 0.1) & (msk > 0)).sum()) * s["cell_area_km2"]
                            for t in range(nt)])
    maxdepth_m = np.array([float(h[t][msk > 0].max()) if (msk > 0).any() else 0.0
                           for t in range(nt)])
    return flooded_km2, maxdepth_m


def cum_rain_series(model_dir: Path, nt: int):
    precip = xr.open_dataset(model_dir / "precip_2d.nc")
    pvar = list(precip.data_vars)[0]
    p_native = np.nan_to_num(precip[pvar].values, nan=0.0)
    p_series = p_native.reshape(p_native.shape[0], -1).mean(axis=1)
    if len(p_series) < nt:
        p_series = np.pad(p_series, (0, nt - len(p_series)), constant_values=0.0)
    else:
        p_series = p_series[:nt]
    return np.cumsum(p_series)


def glofas_peak_q(glofas_nc: Path, reach: dict, times: np.ndarray):
    """Interpolate the daily GloFAS Q at the peak cell within `reach` to the
    SFINCS hourly times. `reach` is {lat_min, lat_max, lon_min, lon_max}."""
    if not glofas_nc.exists():
        return np.zeros(len(times)), None, 0.0
    gf = xr.open_dataset(glofas_nc)
    qvar = list(gf.data_vars)[0]
    sel = gf.sel(longitude=slice(reach["lon_min"], reach["lon_max"]),
                 latitude=slice(reach["lat_max"], reach["lat_min"]))
    qmat = sel[qvar].max("time").values
    qmat = np.where(np.isfinite(qmat), qmat, 0.0)
    if not qmat.size or qmat.max() <= 0:
        return np.zeros(len(times)), None, 0.0
    i_up, j_up = np.unravel_index(int(np.argmax(qmat)), qmat.shape)
    q_daily = np.where(np.isfinite(sel[qvar].isel(latitude=i_up, longitude=j_up).values),
                       sel[qvar].isel(latitude=i_up, longitude=j_up).values, 0.0)
    q_times = sel["time"].values
    q_hourly = np.interp(times.astype("datetime64[s]").astype(float),
                         q_times.astype("datetime64[s]").astype(float), q_daily)
    return q_hourly, (float(sel.latitude[i_up]), float(sel.longitude[j_up])), float(qmat[i_up, j_up])


def load_polys_paths(ems_dir: Path, target_epsg: int, glob_patterns: list):
    """Return dict {label: [(xs_array, ys_array), ...]} for each label.
    Each glob_patterns entry is (label, pat_or_pats, simplify_tol_m). The
    second field may be a single glob string or a list of globs (any match
    contributes to the label). Both Polygon and LineString geometries are
    accepted — newer Copernicus EMS GRADING products ship hydrography as
    lines instead of polygons.
    """
    import numpy as np
    import pyogrio
    import pyproj
    from shapely import from_wkb
    from shapely.ops import transform as shp_transform
    from shapely.geometry import (Polygon, MultiPolygon,
                                  LineString, MultiLineString)
    out = {}
    target_crs = pyproj.CRS.from_epsg(target_epsg)
    for label, pat_or_pats, simp in glob_patterns:
        items = []
        if not ems_dir.exists():
            out[label] = items
            continue
        pats = [pat_or_pats] if isinstance(pat_or_pats, str) else list(pat_or_pats)
        shps = []
        for p in pats:
            shps.extend(ems_dir.rglob(p))
        seen = set()
        shps = sorted([sp for sp in shps if not (sp in seen or seen.add(sp))])
        for shp in shps:
            info = pyogrio.read_info(shp)
            src_crs = pyproj.CRS.from_user_input(info["crs"])
            _, _, gw, _ = pyogrio.raw.read(str(shp), return_fids=True)
            geoms = [from_wkb(g) for g in gw]
            if src_crs != target_crs:
                tr = pyproj.Transformer.from_crs(src_crs, target_crs,
                                                 always_xy=True).transform
                geoms = [shp_transform(tr, g) for g in geoms]
            for g in geoms:
                if g.is_empty:
                    continue
                if isinstance(g, (Polygon, MultiPolygon)):
                    parts = g.geoms if isinstance(g, MultiPolygon) else [g]
                    for p in parts:
                        if p.is_empty:
                            continue
                        sp = p.simplify(simp, preserve_topology=False)
                        if sp.is_empty or not isinstance(sp, Polygon):
                            continue
                        xs, ys = sp.exterior.coords.xy
                        items.append((np.array(xs), np.array(ys)))
                elif isinstance(g, (LineString, MultiLineString)):
                    parts = g.geoms if isinstance(g, MultiLineString) else [g]
                    for ln in parts:
                        if ln.is_empty:
                            continue
                        sp = ln.simplify(simp, preserve_topology=False)
                        if sp.is_empty:
                            continue
                        ls_list = sp.geoms if isinstance(sp, MultiLineString) else [sp]
                        for li in ls_list:
                            if li.is_empty or not isinstance(li, LineString):
                                continue
                            xs, ys = li.coords.xy
                            items.append((np.array(xs), np.array(ys)))
        out[label] = items
    return out
