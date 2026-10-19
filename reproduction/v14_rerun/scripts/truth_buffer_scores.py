"""Phase 4a (GO Phases 3-5, 2026-10-19) — truth-polygon positional uncertainty on the v1.4 outputs.

Re-scores the strict h > 0.10 m contingency against the EMS observed extent buffered by -20 / 0 / +20 m (the Sentinel-1
positional spec the manuscript quotes in §3.6/§7; validation/truth_uncertainty.py did this for the three published
canonical runs with the published mask). Same rasterisation rule as the validator (all_touched, rows in map order,
y ascending), the v1.4 evaluation mask (AOI ∩ active minus the exclusion GeoTIFF) on both sides. Post-processing only.

Usage: python -I truth_buffer_scores.py --repo <worktree> --config <run yaml> --exclusion-tif <tif> --out-json <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import numpy as np


def rasterise_geoms(geoms, s, buffer_m: float = 0.0) -> np.ndarray:
    """Boolean grid (rows = map order, y ascending) of the geometries buffered by buffer_m (negative = eroded)."""
    import rasterio.features
    from rasterio.transform import from_bounds
    x, y = np.asarray(s["x"]), np.asarray(s["y"])
    ny, nx = x.shape
    dx, dy = float(s["dx"]), float(s["dy"])
    xs, ys = x[0, :], y[:, 0]
    tr = from_bounds(float(xs.min()) - dx / 2, float(ys.min()) - dy / 2, float(xs.max()) + dx / 2, float(ys.max()) + dy / 2, nx, ny)
    gs = []
    for g in geoms:
        gb = g.buffer(buffer_m) if buffer_m else g
        if not gb.is_empty:
            gs.append(gb)
    if not gs:
        return np.zeros((ny, nx), dtype=bool)
    out = rasterio.features.rasterize(((g, 1) for g in gs), out_shape=(ny, nx), transform=tr, all_touched=True, dtype="uint8")
    out = out[::-1, :] if (ny > 1 and ys[1] > ys[0]) else out      # rasterio rows run north->south; the map stores y ascending
    return out.astype(bool)


def load_geoms(shp_paths, target_epsg):
    import pyogrio
    import pyproj
    from shapely import from_wkb
    from shapely.ops import transform as shp_transform
    target = pyproj.CRS.from_epsg(target_epsg)
    geoms = []
    for shp in shp_paths:
        info = pyogrio.read_info(shp)
        src = pyproj.CRS.from_user_input(info["crs"])
        _, _, gw, _ = pyogrio.raw.read(str(shp), return_fids=True)
        gs = [from_wkb(g) for g in gw]
        if src != target:
            tr = pyproj.Transformer.from_crs(src, target, always_xy=True).transform
            gs = [shp_transform(tr, g) for g in gs]
        geoms.extend([g for g in gs if not g.is_empty])
    return geoms


def buffer_sweep(model_wet, truth_geoms, universe, s, buffers_m=(-20.0, 0.0, 20.0)) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "validation"))
    from validate_event_v2 import _contingency_full
    out = {}
    for b in buffers_m:
        truth = rasterise_geoms(truth_geoms, s, buffer_m=b)
        c = _contingency_full(model_wet, truth, universe)
        c["truth_km2"] = float((truth & universe).sum() * s["cell_area_km2"])
        out[f"{b:g}"] = c
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--exclusion-tif", type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--buffers", default="-20,0,20")
    ap.add_argument("--threshold", type=float, default=0.10)
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts")); sys.path.insert(0, str(a.repo / "validation"))
    os.environ.setdefault("GDAL_DATA", os.path.join(os.environ.get("CONDA_PREFIX", ""), "Library", "share", "gdal"))
    from _common import load_config
    from validate_event_v2 import _rasterise_polys_to_grid, _select_obs_shps, _list_shps, open_sfincs_light
    cfg = load_config(["--config", str(a.config)])
    s = open_sfincs_light(cfg.paths["model_dir"])
    excl = None
    if a.exclusion_tif:
        from eval_exclusion import read_mask_for_grid
        excl = read_mask_for_grid(a.exclusion_tif, s)
    ems_dir = cfg.paths["data_dir"] / "ems_polygons"
    obs = _select_obs_shps(ems_dir, include_del_product=bool(cfg.ems.get("include_del_product", False)))
    aois = _list_shps(ems_dir, ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"])
    universe = s["msk"] > 0
    if aois:
        universe &= _rasterise_polys_to_grid(aois, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"])
    if excl is not None:
        universe &= ~excl
    zsmax = s["ds"]["zsmax"].max(dim="timemax").values
    hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
    model_wet = hmax > a.threshold
    geoms = load_geoms(obs, cfg.epsg)
    buffers = tuple(float(x) for x in a.buffers.split(","))
    sweep = buffer_sweep(model_wet, geoms, universe, s, buffers)
    # consistency: buffer 0 must equal the validator's strict rasterisation of the same shapefiles
    plain = _rasterise_polys_to_grid(obs, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"])
    same = bool(np.array_equal(plain, rasterise_geoms(geoms, s, 0.0)))
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "config": str(a.config), "event": cfg.event_slug, "threshold_m": a.threshold,
           "exclusion_tif": (str(a.exclusion_tif) if a.exclusion_tif else None), "buffers_m": list(buffers), "n_obs_shps": len(obs), "n_polygons": len(geoms),
           "zero_buffer_equals_validator_rasterisation": same, "universe_km2": float(universe.sum() * s["cell_area_km2"]), "sweep": sweep,
           "csi_range": [min(v["csi"] for v in sweep.values()), max(v["csi"] for v in sweep.values())]}
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    for k, v in sweep.items():
        print(f"buffer {k:>4s} m: CSI {v['csi']:.3f} HR {v['hr']:.3f} FAR {v['far']:.3f} B {v['bias']:.2f} truth {v['truth_km2']:.1f} km²")
    print("zero buffer equals validator rasterisation:", same)
    return 0


if __name__ == "__main__":
    sys.exit(main())
