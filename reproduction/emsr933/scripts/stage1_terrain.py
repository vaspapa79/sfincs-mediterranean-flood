"""CODE-10 Stage 1a — catchment and terrain facts for EMSR933 from Copernicus DEM GLO-30.

Per AOI (8 EMS areas of interest, extents from the Stage-0 API snapshot) and per candidate domain:
  * contributing catchment: cells draining through the AOI (outlet-based), external inflow streams
    (upstream area at the cells entering the AOI), largest stream inside the AOI       -> R3 input
  * sea cells (GLO-30 <= 0 m) inside the AOI box / candidate domain                      -> R5 input
  * closed depressions (Tzermiado and Omalos poljes): filled-depth statistics, spill level -> ponding note
  * observed-wet area at the Stage-0 cut-off (union of released observedEventA layers, EPSG:32634)
    and its equivalent cell count at dx = 50 / 100 / 150 m
  * candidate domains = bbox of (AOI boxes U complete basins intersecting them) + margin, for the
    three clusters and the whole island; cell counts at 50/100/150 m; inflow streams >= 120 km2
    crossing the domain edge (R3); UTM 34N scale factor at AOI centroids and domain corners.

Hydrology is computed with pyflwdir on the GLO-30 mosaic decimated 3x (90 m, block average) over
23.4-26.4 E / 34.8-35.7 N; sea (<= 0 m) is masked so the coast acts as outlet. All depressions are
filled for the flow network (conventional delineation); depression depths are reported separately.
Facts only; the rule ledger interprets them.

Usage: python -I stage1_terrain.py --event-root D:/ELKAK/implementation/emsr933_crete --out-dir <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np

ISLAND = (23.4, 34.8, 26.4, 35.7)
DECIM = 3
UPAREA_STREAM_KM2 = 10.0      # cells drawn as "stream" in the summaries
R3_THRESHOLD_KM2 = 120.0      # Box 1: 4 x GloFAS-v4 cell
CLUSTERS = {"east": [3, 4, 6, 8], "central": [1, 2, 5], "west": [7]}
MARGIN_DEG = 0.02
DXS = (50, 100, 150)
UTM = 32634


def latest(d: Path, pat: str) -> Path:
    c = sorted(d.glob(pat))
    if not c:
        sys.exit(f"missing {pat} in {d}")
    return c[-1]


def read_dem(vrt: Path):
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import from_bounds
    from rasterio.windows import from_bounds as win_from_bounds
    with rasterio.open(vrt) as src:
        win = win_from_bounds(*ISLAND, transform=src.transform)
        h = int(round(win.height / DECIM)); w = int(round(win.width / DECIM))
        dem = src.read(1, window=win, out_shape=(h, w), resampling=Resampling.average).astype("float32")
        nod = src.nodata
    transform = from_bounds(*ISLAND, w, h)
    if nod is not None:
        dem[dem == nod] = np.nan
    return dem, transform, (h, w)


def cell_area_km2(transform, shape):
    """Geodetic cell area per row (lat/lon grid)."""
    h, _ = shape
    dlon = transform.a; dlat = -transform.e
    lats = transform.f + (np.arange(h) + 0.5) * transform.e
    R = 6371.0088
    return (R ** 2) * math.radians(dlon) * (np.sin(np.radians(lats + dlat / 2)) - np.sin(np.radians(lats - dlat / 2)))


def rasterize(geom, transform, shape):
    import rasterio.features
    return rasterio.features.rasterize([(geom, 1)], out_shape=shape, transform=transform,
                                       all_touched=True, dtype="uint8").astype(bool)


def rc_to_lonlat(transform, r, c):
    x, y = transform * (c + 0.5, r + 0.5)
    return round(float(x), 4), round(float(y), 4)


def bbox_of_mask(mask, transform):
    rows, cols = np.where(mask)
    x0, y1 = transform * (cols.min(), rows.min())
    x1, y0 = transform * (cols.max() + 1, rows.max() + 1)
    return float(x0), float(y0), float(x1), float(y1)


def pad_round(b, margin, step=0.01):
    w, s, e, n = b
    f = lambda v, up: (math.ceil(v / step) if up else math.floor(v / step)) * step
    return [round(f(w - margin, False), 2), round(f(s - margin, False), 2),
            round(f(e + margin, True), 2), round(f(n + margin, True), 2)]


def utm_scale(lon, lat):
    from pyproj import Proj
    f = Proj(f"EPSG:{UTM}").get_factors(lon, lat)
    return round(float(f.meridional_scale), 5), round(float(f.areal_scale), 5)


def follow_to_aoi(idx, idxs_ds, aoi_id_flat, max_steps=2_000_000):
    """Walk downstream from idx; return the AOI number first touched, or None."""
    seen = 0
    while seen < max_steps:
        a = aoi_id_flat[idx]
        if a:
            return int(a)
        nxt = idxs_ds[idx]
        if nxt == idx or nxt < 0:
            return None
        idx = nxt; seen += 1
    return None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--event-root", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args()
    import pyflwdir
    import geopandas as gpd
    from shapely import wkt as swkt
    from shapely.geometry import box as sbox

    t0 = dt.datetime.now(dt.timezone.utc)
    vrt = a.event_root / "data/copdem30/copdem30.vrt"
    manifest = json.loads(latest(a.out_dir, "ems_snapshot_*_manifest.json").read_text(encoding="utf-8"))
    dem, transform, shape = read_dem(vrt)
    carea = cell_area_km2(transform, shape)                      # per row
    carea2d = np.repeat(carea[:, None], shape[1], axis=1)
    land = np.isfinite(dem) & (dem > 0)
    sea = np.isfinite(dem) & (dem <= 0)
    dem_h = np.where(land, dem, -9999.0).astype("float32")

    # flow network on the filled DEM; depression depths kept separately
    filled, _ = pyflwdir.dem.fill_depressions(dem_h, nodata=-9999.0, max_depth=-1.0, outlets="edge")
    depth = np.where(land, filled - dem_h, 0.0)
    flw = pyflwdir.from_dem(data=dem_h, nodata=-9999.0, max_depth=-1.0, transform=transform,
                            latlon=True, outlets="edge")
    uparea = flw.upstream_area(unit="km2")
    uparea = np.where(uparea < 0, np.nan, uparea)
    basins = flw.basins()
    idxs_ds = flw.idxs_ds.astype(np.int64)
    n = dem.size

    # AOI geometry
    aois = sorted(manifest["aois"], key=lambda x: x["number"])
    aoi_id = np.zeros(shape, dtype=np.int16)
    aoi_geoms = {}
    for ao in aois:
        g = swkt.loads(ao["extent_wkt"])
        aoi_geoms[ao["number"]] = g
        m = rasterize(g, transform, shape)
        aoi_id[m & (aoi_id == 0)] = ao["number"]
    aoi_id_flat = aoi_id.ravel()

    # observed-wet union per AOI from the released packages (EPSG:32634)
    xroot = Path(manifest["extracted_dir"])
    obs_by_aoi = {}
    for ao in aois:
        parts = []
        for p in ao["products"]:
            if not p.get("released"):
                continue
            pkg = xroot / p["download"]["stem"]
            for shp in pkg.rglob("*observedEventA*.shp"):
                parts.append(gpd.read_file(shp).to_crs(epsg=UTM))
        if parts:
            u = gpd.GeoDataFrame(__import__("pandas").concat(parts, ignore_index=True), crs=f"EPSG:{UTM}")
            km2 = float(u.union_all().area) / 1e6
            obs_by_aoi[ao["number"]] = {"km2_union": round(km2, 4), "n_products": len(parts),
                                        "cells_at_dx": {str(dx): round(km2 * 1e6 / dx ** 2, 1) for dx in DXS}}
        else:
            obs_by_aoi[ao["number"]] = None

    rep = {"utc": t0.strftime("%Y-%m-%dT%H:%M:%SZ"), "dem_vrt": str(vrt), "grid": {
               "bbox": ISLAND, "decimation": DECIM, "shape": shape,
               "cell_deg": [round(transform.a, 6), round(-transform.e, 6)],
               "cell_m_approx": [round(transform.a * 111320 * math.cos(math.radians(35.25))), round(-transform.e * 111320)]},
           "land_km2": round(float(carea2d[land].sum()), 1), "aois": [], "domains": {}}

    for ao in aois:
        k = ao["number"]
        m = aoi_id == k
        mf = m.ravel()
        ds_in = np.zeros(n, dtype=bool); ds_in[idxs_ds[mf]] = True  # not used directly
        idx_in = np.where(mf)[0]
        ds = idxs_ds[idx_in]
        pits_inside = idx_in[ds == idx_in]
        outlets = idx_in[(ds != idx_in) & ~mf[ds]]
        # inlets: cells outside whose downstream cell is inside
        idx_out = np.where(~mf & land.ravel())[0]
        ds_out = idxs_ds[idx_out]
        inlets = idx_out[(ds_out != idx_out) & mf[ds_out]]
        up = uparea.ravel()
        inlet_tab = sorted([(float(up[i]), int(i)) for i in inlets if np.isfinite(up[i])], reverse=True)[:6]
        inlet_rows = []
        for ua, i in inlet_tab:
            r, c = divmod(i, shape[1])
            lon, lat = rc_to_lonlat(transform, r, c)
            inlet_rows.append({"uparea_km2": round(ua, 1), "lon": lon, "lat": lat, "z_m": round(float(dem[r, c]), 1),
                               "ge_R3_threshold": bool(ua >= R3_THRESHOLD_KM2)})
        bas_ids = np.unique(basins[m & land]); bas_ids = bas_ids[bas_ids > 0]
        bas_mask = np.isin(basins, bas_ids) & land
        dep_in = depth[m & land]
        i_max = int(np.argmax(np.where(m & land, uparea, -1)))
        rmx, cmx = divmod(i_max, shape[1])
        rec = {"number": k, "name": ao["name"], "aoi_km2_utm34": ao["area_km2_utm34"],
               "centroid_lonlat": ao["centroid_lonlat"],
               "utm34_scale_at_centroid": dict(zip(("k_linear", "k_areal"), utm_scale(*ao["centroid_lonlat"]))),
               "dem_min_max_mean_m": [round(float(np.nanmin(dem[m])), 1), round(float(np.nanmax(dem[m])), 1), round(float(np.nanmean(dem[m])), 1)],
               "sea_cells_in_box": int((sea & m).sum()), "land_km2_in_box": round(float(carea2d[m & land].sum()), 1),
               "n_outlet_cells": int(outlets.size), "n_pits_inside": int(pits_inside.size),
               "uparea_sum_at_outlets_km2": round(float(np.nansum(up[outlets])), 1),
               "largest_stream_inside": {"uparea_km2": round(float(uparea[rmx, cmx]), 1), **dict(zip(("lon", "lat"), rc_to_lonlat(transform, rmx, cmx)))},
               "external_inflow_streams_top": inlet_rows,
               "n_inlets_ge_R3": int(sum(1 for ua, _ in [(float(up[i]), i) for i in inlets] if ua >= R3_THRESHOLD_KM2)),
               "basins_intersecting": {"n": int(bas_ids.size), "km2": round(float(carea2d[bas_mask].sum()), 1),
                                       "bbox": [round(v, 3) for v in bbox_of_mask(bas_mask | m, transform)],
                                       "reach_sea": bool((sea & _dilate(bas_mask)).any())},
               "depressions": {"km2_depth_gt_0p5m": round(float(carea2d[m & land & (depth > 0.5)].sum()), 2),
                               "max_depth_m": round(float(dep_in.max()), 1) if dep_in.size else 0.0,
                               "spill_level_m_at_deepest": round(float(filled[m & land][np.argmax(dep_in)]), 1) if dep_in.size else None,
                               "floor_min_m": round(float(np.nanmin(dem[m & land])), 1)},
               "observed_wet_cutoff": obs_by_aoi[k]}
        rep["aois"].append(rec)

    # candidate domains
    def domain_record(name, numbers):
        m_aoi = np.isin(aoi_id, numbers)
        ids = np.unique(basins[m_aoi & land]); ids = ids[ids > 0]
        hyd = (np.isin(basins, ids) & land) | m_aoi
        bb = pad_round(bbox_of_mask(hyd, transform), MARGIN_DEG)
        dom = rasterize(sbox(*bb), transform, shape)
        domf = dom.ravel()
        idx_out = np.where(~domf & land.ravel())[0]
        ds_out = idxs_ds[idx_out]
        inl = idx_out[(ds_out != idx_out) & domf[ds_out]]
        up = uparea.ravel()
        big = [(float(up[i]), int(i)) for i in inl if np.isfinite(up[i]) and up[i] >= R3_THRESHOLD_KM2]
        big.sort(reverse=True)
        rows = []
        for ua, i in big[:10]:
            r, c = divmod(i, shape[1])
            lon, lat = rc_to_lonlat(transform, r, c)
            rows.append({"uparea_km2": round(ua, 1), "lon": lon, "lat": lat, "z_m": round(float(dem[r, c]), 1),
                         "reaches_aoi": follow_to_aoi(int(idxs_ds[i]), idxs_ds, aoi_id_flat)})
        from pyproj import Transformer
        tr = Transformer.from_crs(4326, UTM, always_xy=True)
        xs, ys = zip(*[tr.transform(x, y) for x, y in ((bb[0], bb[1]), (bb[2], bb[1]), (bb[2], bb[3]), (bb[0], bb[3]))])
        wx, hy = max(xs) - min(xs), max(ys) - min(ys)
        land_km2 = float(carea2d[dom & land].sum()); sea_cells = int((dom & sea).sum())
        return {"aois": numbers, "bbox_WSEN": bb, "size_km_utm34": [round(wx / 1000, 1), round(hy / 1000, 1)],
                "land_km2": round(land_km2, 1), "sea_cells_90m": sea_cells, "contains_sea": sea_cells > 0,
                "cells_total_at_dx": {str(dx): int(round(wx / dx) * round(hy / dx)) for dx in DXS},
                "cells_land_at_dx": {str(dx): int(land_km2 * 1e6 / dx ** 2) for dx in DXS},
                "inflow_streams_ge_120km2_crossing_edge": rows, "n_inflow_ge_120km2": len(big),
                "utm34_scale_corners": {f"{x:.2f}E/{y:.2f}N": utm_scale(x, y) for x, y in ((bb[0], bb[1]), (bb[2], bb[3]))}}

    for cname, nums in CLUSTERS.items():
        rep["domains"][cname] = domain_record(cname, nums)
    rep["domains"]["island"] = domain_record("island", [a_["number"] for a_ in aois])
    rep["domains"]["island"]["bbox_WSEN"] = list(ISLAND)
    rep["elapsed_s"] = round((dt.datetime.now(dt.timezone.utc) - t0).total_seconds(), 1)

    out = a.out_dir / "stage1_terrain.json"
    out.write_text(json.dumps(rep, indent=2, default=float), encoding="utf-8")

    L = [f"# EMSR933 Stage 1a — terrain/catchment facts (GLO-30 @ 90 m, pyflwdir), {rep['utc']}", "",
         "| AOI | name | AOI km² | DEM min/max m | sea cells in box | outlets | pits | Σ uparea at outlets km² | largest stream inside km² | top inflow km² (≥120?) | basins km² (reach sea) | depression km² >0.5 m / max m / spill m | obs km² (cells @50/100/150) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rep["aois"]:
        top = r["external_inflow_streams_top"][0] if r["external_inflow_streams_top"] else None
        ow = r["observed_wet_cutoff"]
        L.append(f"| {r['number']:02d} | {r['name']} | {r['aoi_km2_utm34']} | {r['dem_min_max_mean_m'][0]}/{r['dem_min_max_mean_m'][1]} | "
                 f"{r['sea_cells_in_box']} | {r['n_outlet_cells']} | {r['n_pits_inside']} | {r['uparea_sum_at_outlets_km2']} | "
                 f"{r['largest_stream_inside']['uparea_km2']} | {(str(top['uparea_km2']) + (' yes' if top['ge_R3_threshold'] else ' no')) if top else '—'} | "
                 f"{r['basins_intersecting']['km2']} ({'yes' if r['basins_intersecting']['reach_sea'] else 'no'}) | "
                 f"{r['depressions']['km2_depth_gt_0p5m']} / {r['depressions']['max_depth_m']} / {r['depressions']['spill_level_m_at_deepest']} | "
                 f"{(str(ow['km2_union']) + ' (' + '/'.join(str(int(v)) for v in ow['cells_at_dx'].values()) + ')') if ow else '— (no release)'} |")
    L += ["", "| domain | AOIs | bbox W,S,E,N | size km | land km² | sea? | cells total @50/100/150 | land cells @50/100/150 | inflow ≥120 km² crossing edge | UTM34 k (corners) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for name, d in rep["domains"].items():
        L.append(f"| {name} | {d['aois']} | {d['bbox_WSEN']} | {d['size_km_utm34'][0]}×{d['size_km_utm34'][1]} | {d['land_km2']} | "
                 f"{'yes' if d['contains_sea'] else 'no'} | {'/'.join(f'{v/1e6:.2f}M' for v in d['cells_total_at_dx'].values())} | "
                 f"{'/'.join(f'{v/1e6:.2f}M' for v in d['cells_land_at_dx'].values())} | {d['n_inflow_ge_120km2']} | "
                 f"{'; '.join(f'{k}: {v[0]}' for k, v in d['utm34_scale_corners'].items())} |")
    (a.out_dir / "stage1_terrain.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L)); print(f"\nelapsed {rep['elapsed_s']} s -> {out}")
    return 0


def _dilate(mask):
    from scipy import ndimage
    return ndimage.binary_dilation(mask, structure=np.ones((3, 3), bool))


if __name__ == "__main__":
    sys.exit(main())
