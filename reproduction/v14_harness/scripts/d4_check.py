"""CODE-13 Part A — D4 check: sea, initial water and evaluation mask (geometry only; NO runs, NO scores).

For every model listed in EVENTS: the as-run grid (sfincs_map.nc: msk, zb, x, y; or gis/*.tif for a build
without a run) and the hydromt dep raster (gis/dep.tif) give
  A1  active cells; active cells with dep <= 0 split into (i) connected to the grid edge through dep <= 0
      cells ("open sea", 4-connectivity) and (ii) inland; msk = 2 count and location (grid perimeter vs
      interior);
  A2  (ii) cells with zb < 0 (they start wet under zsini = 0; zb = SFINCS bed level of sfincs_map.nc, i.e.
      the sub-grid minimum) — count and km2;
  A3  the validator's evaluation mask (validate_event_v2.py:229-242: active cells AND the union of the
      EMS areaOfInterest polygons; no sea / hydrography / elevation exclusion) and how many of its cells are
      (i), (ii)-with-zb<0, inside EMS hydrography polygons (where the package ships them), or ESA WorldCover
      class 80 (permanent water) at the cell centre; plus the list of reference layers of each package set.
No FP/FN/score is computed. Usage: python -I d4_check.py --repo <worktree> --out-json <...> --out-md <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np

EVENTS = [
    # label, kind, model dir, gis dir, ems dir, yaml, worldcover vrt
    ("Pineios enhanced (2a)", "map", "D:/ELKAK/implementation/pineios_sfincs_enhanced/model_author_ref", None,
     "D:/ELKAK/implementation/pineios_sfincs_enhanced/data/ems_polygons", "emsr692_pineios_enhanced.yaml",
     "D:/ELKAK/implementation/pineios_sfincs_enhanced/data/esa_worldcover/esa_worldcover_2021.vrt"),
    ("Pineios grid-matched baseline (1c)", "map", "D:/ELKAK/reproduction/grid_matched_baseline/model", None,
     "D:/ELKAK/implementation/pineios_sfincs_enhanced/data/ems_polygons", "emsr692_pineios_enhanced.yaml",
     "D:/ELKAK/implementation/pineios_sfincs_enhanced/data/esa_worldcover/esa_worldcover_2021.vrt"),
    ("Mandra enhanced (2b)", "map", "D:/ELKAK/implementation/mandra_sfincs_enhanced/model_author_ref", None,
     "D:/ELKAK/implementation/mandra_sfincs_enhanced/data/ems_polygons", "emsr257_mandra_enhanced.yaml",
     "D:/ELKAK/implementation/mandra_sfincs_enhanced/data/esa_worldcover/esa_worldcover_2021.vrt"),
    ("Mandra baseline (1d)", "map", "D:/ELKAK/implementation/mandra_sfincs/model", None,
     "D:/ELKAK/implementation/mandra_sfincs/data/ems_polygons", "emsr257_mandra.yaml",
     "D:/ELKAK/implementation/mandra_sfincs/data/esa_worldcover/esa_worldcover_2021.vrt"),
    ("Strymonas v3 enhanced (2c)", "map", "D:/ELKAK/implementation/emsr122_sfincs_v3/model_author_ref", None,
     "D:/ELKAK/implementation/emsr122_sfincs_v3/data/ems_polygons", "emsr122_strymonas_enhanced.yaml",
     "D:/ELKAK/implementation/emsr122_sfincs_v3/data/esa_worldcover/esa_worldcover_2021.vrt"),
    ("Strymonas baseline (1e)", "map", "D:/ELKAK/implementation/emsr122_sfincs/model", None,
     "D:/ELKAK/implementation/emsr122_sfincs/data/ems_polygons", "emsr122_strymonas.yaml",
     "D:/ELKAK/implementation/emsr122_sfincs/data/esa_worldcover/esa_worldcover_2021.vrt"),
    ("Valencia 164 mm (2e)", "map", "D:/ELKAK/ELKAK2/NHESS/R1_verification/task_valencia_anchor/rerun_v164/model",
     "D:/ELKAK/ELKAK2/NHESS/runs/valencia_emsr773/model/gis",
     "D:/ELKAK/ELKAK2/NHESS/runs/valencia_emsr773/data/ems_polygons", "emsr773_valencia_enhanced.yaml",
     "D:/ELKAK/ELKAK2/NHESS/runs/valencia_emsr773/data/esa_worldcover/esa_worldcover_2021.vrt"),
    ("Emilia-Romagna 8-AOI (2f)", "map", "D:/ELKAK/ELKAK2/NHESS/runs/emilia_emsr664/model", None,
     "D:/ELKAK/ELKAK2/NHESS/R1_verification/task_emilia_aoi/data/ems_polygons", "emsr664_emilia_romagna_enhanced.yaml",
     "D:/ELKAK/ELKAK2/NHESS/runs/emilia_emsr664/data/esa_worldcover/esa_worldcover_2021.vrt"),
    ("Crete build-only QC (CODE-12)", "gis", "D:/ELKAK/implementation/emsr933_crete/buildqc/model", None,
     "D:/ELKAK/implementation/emsr933_crete/ems_snapshots/20261009T124720Z/extracted", "emsr933_crete_enhanced.yaml",
     "D:/ELKAK/implementation/emsr933_crete/data/esa_worldcover/esa_worldcover_2021.vrt"),
]
HYDRO_PATTERNS = ["*hydrography_a.shp", "*hydrography_poly.shp", "*hydrographyA*.shp"]


def load_validator(repo: Path):
    os.environ.setdefault("SFINCS_SKILL_DIR", str(repo / "skill"))
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    spec = importlib.util.spec_from_file_location("validate_event_v2", repo / "validation" / "validate_event_v2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_grid(kind: str, model: Path, gis: Path):
    """Return msk, zb, dep, x2d, y2d (all y-ascending, shape (n, m)), dx, dy, epsg."""
    import rasterio
    import xarray as xr
    with rasterio.open(gis / "dep.tif") as r:
        dep = r.read(1).astype("float64")[::-1, :]            # north-up -> y ascending
        dep = np.where(dep == r.nodata, np.nan, dep) if r.nodata is not None else dep
        tr, crs = r.transform, r.crs
    if kind == "map":
        ds = xr.open_dataset(model / "sfincs_map.nc")
        msk = ds["msk"].values.astype(int); zb = ds["zb"].values.astype("float64")
        x2d, y2d = ds["x"].values, ds["y"].values
        inp = ds["inp"].attrs; dx, dy = float(inp["dx"]), float(inp["dy"]); epsg = int(inp["epsg"])
        assert msk.shape == dep.shape, (msk.shape, dep.shape)
        assert y2d[1, 0] > y2d[0, 0]
    else:
        with rasterio.open(gis / "msk.tif") as r:
            msk = r.read(1)[::-1, :]
            msk = np.where(np.isnan(msk), 0, msk).astype(int)
        dx, dy = tr.a, -tr.e; epsg = crs.to_epsg()
        n, m = dep.shape
        xs = tr.c + dx * (np.arange(m) + 0.5); ys = (tr.f - dy * n) + dy * (np.arange(n) + 0.5)
        x2d, y2d = np.meshgrid(xs, ys)
        # bed level = sub-grid minimum (np index = column-major over the south-up grid; see crete_build_qc.py)
        from hydromt_sfincs import utils as sfu
        ind = sfu.read_binary_map_index(model / "sfincs.ind")
        zmin = xr.open_dataset(model / "sfincs_subgrid.nc")["z_zmin"].values.astype("float64")
        zb = np.full(dep.shape, np.nan); flat = zb.ravel(order="F"); flat[ind] = zmin; zb = flat.reshape(dep.shape, order="F")
    return msk, zb, dep, x2d, y2d, dx, dy, epsg


def open_sea_split(active, dep):
    """(i) open sea / (ii) inland split — the production function of harness v1.4 (build_model.open_sea_split),
    plus the component counts reported in the table."""
    from scipy import ndimage
    import build_model
    sea0, open_sea, inland = build_model.open_sea_split(active, dep)
    lab, n = ndimage.label(sea0, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    edge = np.zeros_like(sea0); edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
    nedge = int(np.unique(lab[edge & sea0]).size - (1 if (lab[edge & sea0] == 0).any() else 0))
    return sea0, open_sea, inland, int(n), nedge


def worldcover_class(vrt: str, x2d, y2d, epsg: int, sel):
    import rasterio
    from pyproj import Transformer
    rows, cols = np.where(sel)
    if rows.size == 0:
        return np.zeros(0, dtype=int), rows, cols
    tr = Transformer.from_crs(epsg, 4326, always_xy=True)
    lon, lat = tr.transform(x2d[rows, cols], y2d[rows, cols])
    with rasterio.open(vrt) as src:
        vals = np.array([v[0] for v in src.sample(zip(lon, lat))], dtype=int)
    return vals, rows, cols


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--out-md", required=True, type=Path)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    V = load_validator(a.repo)
    from _common import load_config
    rep = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "evaluation_mask_definition": "validate_event_v2.py:235-242: evaluation_mask = (msk > 0) & rasterised union of *areaOfInterest* shapefiles "
                                         "(all_touched=True, :62-102); no exclusion of sea, hydrography/permanent water or zb <= 0 cells.",
           "events": []}
    for label, kind, model, gis, ems, yml, wc in EVENTS:
        if a.only and a.only not in label:
            continue
        model, ems = Path(model), Path(ems); gis = Path(gis) if gis else model / "gis"
        cfg = load_config(["--config", str(a.repo / "skill" / "examples" / yml)])
        msk, zb, dep, x2d, y2d, dx, dy, epsg = read_grid(kind, model, gis)
        cell_km2 = dx * dy / 1e6
        active = msk >= 1
        sea0, open_sea, inland0, ncomp, nedge = open_sea_split(active, dep)
        perim = np.zeros_like(active); perim[0, :] = perim[-1, :] = perim[:, 0] = perim[:, -1] = True
        m2 = msk == 2
        land = active & ~open_sea
        zb_neg_inland0 = inland0 & (zb < 0)
        zb_neg_land = land & (zb < 0)
        # evaluation mask exactly as the validator builds it
        aoi_shps = V._list_shps(ems, ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"])
        aoi = V._rasterise_polys_to_grid(aoi_shps, x2d, y2d, epsg, dx, dy) if aoi_shps else np.ones_like(active)
        ev = active & aoi
        hydro_shps = V._list_shps(ems, HYDRO_PATTERNS)
        hydro = V._rasterise_polys_to_grid(hydro_shps, x2d, y2d, epsg, dx, dy) if hydro_shps else np.zeros_like(active)
        wcv, wr, wcc = worldcover_class(wc, x2d, y2d, epsg, ev)
        wc80 = np.zeros_like(active); wc80[wr[wcv == 80], wcc[wcv == 80]] = True
        layers = sorted({p.name.split("_")[-2] + "_" + p.name.split("_")[-1] if p.name.count("_") > 2 else p.name
                         for p in ems.rglob("*.shp")})
        # compact layer names (strip product prefixes)
        import re
        lay = sorted({re.sub(r"^(EMSR\d+_)?(\w+?_)*?(v\d+_)?", "", p.stem) for p in ems.rglob("*.shp")})
        e = {"label": label, "model_dir": str(model), "gis_dir": str(gis), "ems_dir": str(ems), "yaml": yml, "epsg": epsg,
             "grid": {"n": int(msk.shape[0]), "m": int(msk.shape[1]), "dx_m": dx, "cell_km2": cell_km2, "cells_total": int(msk.size)},
             "A1": {"active": int(active.sum()), "active_km2": round(float(active.sum() * cell_km2), 1),
                    "active_dep_le_0": int(sea0.sum()), "open_sea_i": int(open_sea.sum()), "open_sea_i_km2": round(float(open_sea.sum() * cell_km2), 1),
                    "inland_dep_le_0_ii": int(inland0.sum()), "inland_ii_km2": round(float(inland0.sum() * cell_km2), 2),
                    "dep_le_0_components": ncomp, "components_touching_edge": nedge,
                    "msk2": int(m2.sum()), "msk2_on_grid_perimeter": int((m2 & perim).sum()), "msk2_interior": int((m2 & ~perim).sum()),
                    "msk2_in_open_sea": int((m2 & open_sea).sum()), "msk2_in_inland_or_land": int((m2 & ~open_sea).sum()),
                    "msk2_dep_max_m": float(np.nanmax(dep[m2])) if m2.any() else None, "msk2_zb_max_m": float(np.nanmax(zb[m2])) if m2.any() else None,
                    "open_sea_zb_min_m": float(np.nanmin(zb[open_sea])) if open_sea.any() else None,
                    "open_sea_dep_min_m": float(np.nanmin(dep[open_sea])) if open_sea.any() else None,
                    "land_cells": int(land.sum()), "land_km2": round(float(land.sum() * cell_km2), 1)},
             "A2": {"inland_ii_zb_lt_0": int(zb_neg_inland0.sum()), "inland_ii_zb_lt_0_km2": round(float(zb_neg_inland0.sum() * cell_km2), 3),
                    "inland_ii_zb_lt_0_zb_min_m": float(np.nanmin(zb[zb_neg_inland0])) if zb_neg_inland0.any() else None,
                    "all_land_zb_lt_0": int(zb_neg_land.sum()), "all_land_zb_lt_0_km2": round(float(zb_neg_land.sum() * cell_km2), 3),
                    "initial_water_volume_if_zsini_0_Mm3": round(float((-zb[zb_neg_land]).sum() * dx * dy / 1e6), 3) if zb_neg_land.any() else 0.0},
             "A3": {"n_aoi_shps": len(aoi_shps), "eval_cells": int(ev.sum()), "eval_km2": round(float(ev.sum() * cell_km2), 1),
                    "eval_open_sea_i": int((ev & open_sea).sum()), "eval_open_sea_km2": round(float((ev & open_sea).sum() * cell_km2), 2),
                    "eval_inland_ii_zb_lt_0": int((ev & zb_neg_inland0).sum()), "eval_land_zb_lt_0": int((ev & zb_neg_land).sum()),
                    "eval_dep_le_0_any": int((ev & sea0).sum()),
                    "hydrography_layers_found": [p.name for p in hydro_shps][:6], "n_hydro_shps": len(hydro_shps),
                    "eval_in_hydrography": int((ev & hydro).sum()) if hydro_shps else None,
                    "eval_wc80_permanent_water": int((ev & wc80).sum()), "eval_wc80_open_sea": int((ev & wc80 & open_sea).sum()),
                    "eval_wc80_land": int((ev & wc80 & land).sum()), "eval_wc80_km2": round(float((ev & wc80).sum() * cell_km2), 2),
                    "eval_wc_class_counts": {int(k): int(v) for k, v in zip(*np.unique(wcv, return_counts=True))},
                    "package_layers": lay}}
        rep["events"].append(e)
        print(label, json.dumps({"A1": e["A1"], "A2": e["A2"], "A3": {k: v for k, v in e["A3"].items() if k not in ("package_layers", "eval_wc_class_counts")}}))
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    L = [f"# D4 check — sea, initial water, evaluation mask (CODE-13 Part A; geometry only, no scores), {rep['utc']}", "",
         rep["evaluation_mask_definition"], "",
         "(i) open sea = active cells with dep <= 0 connected to the grid edge through dep <= 0 cells (4-connectivity); (ii) inland = the other active dep <= 0 cells; "
         "zb = SFINCS bed level of the run (sub-grid minimum); WC80 = ESA WorldCover class 80 (permanent water) at the cell centre.", "",
         "| model | active cells (km²) | active dep<=0: (i) open sea (km²) | (ii) inland (km²) | msk=2 total / on grid perimeter / interior | msk=2 inside (i) | A2 (ii) zb<0 cells (km²) | all land zb<0 cells (km², initial volume Mm³) | eval cells (km²) | eval ∩ (i) (km²) | eval ∩ (ii) zb<0 | eval ∩ EMS hydrography | eval ∩ WC80 (sea / land) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in rep["events"]:
        A, B, C = e["A1"], e["A2"], e["A3"]
        hyd = "—" if C["eval_in_hydrography"] is None else f"{C['eval_in_hydrography']:,} ({C['n_hydro_shps']} shp)"
        L.append(f"| {e['label']} | {A['active']:,} ({A['active_km2']:,}) | {A['open_sea_i']:,} ({A['open_sea_i_km2']:,}) | {A['inland_dep_le_0_ii']:,} ({A['inland_ii_km2']}) | "
                 f"{A['msk2']:,} / {A['msk2_on_grid_perimeter']:,} / {A['msk2_interior']:,} | {A['msk2_in_open_sea']:,} | {B['inland_ii_zb_lt_0']:,} ({B['inland_ii_zb_lt_0_km2']}) | "
                 f"{B['all_land_zb_lt_0']:,} ({B['all_land_zb_lt_0_km2']}, {B['initial_water_volume_if_zsini_0_Mm3']}) | {C['eval_cells']:,} ({C['eval_km2']:,}) | "
                 f"{C['eval_open_sea_i']:,} ({C['eval_open_sea_km2']}) | {C['eval_inland_ii_zb_lt_0']:,} | {hyd} | "
                 f"{C['eval_wc80_permanent_water']:,} ({C['eval_wc80_open_sea']:,} / {C['eval_wc80_land']:,}) |")
    L += ["", "## Reference layers shipped in each EMS package set (shapefile names, product prefixes stripped)", ""]
    for e in rep["events"]:
        L.append(f"- {e['label']}: {', '.join(e['A3']['package_layers'])}")
    a.out_md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:12])); print(f"-> {a.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
