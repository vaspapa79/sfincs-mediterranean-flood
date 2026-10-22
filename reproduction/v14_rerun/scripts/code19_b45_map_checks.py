"""CODE-19 B4 / B5 — geometry checks behind the maps, no scoring, no model run.

B4 (Valencia, F7): the Albufera lagoon cells — WorldCover class at the cell centre (ESA WorldCover 2021, the same sampling as the
evaluation mask), whether they lie inside the evaluation universe, count and km², modelled h_max there; the lagoon = the connected
component of WorldCover-80 cells that holds the lagoon centre. If the cells are excluded by the universe, F7 is re-exported with the
exclusion mask above the depth layer (r6_figures.EXCL_ON_TOP); if inside, the share of the Valencia false alarms they carry.
Also, for every map (F3, F5-F9): the number of modelled-wet cells that lie in excluded cells (where the depth layer currently shows
over the grey mask).

B5 (Emilia-Romagna, F8): h_max > 0.10 m cells in the five southernmost rows of the domain (y ascending: rows 0-4), whether any lie
inside an AOI, whether the water touches the closed southern boundary (wet cells on row 0 with msk = 1), their position, bed level,
distance to the nearest inflow source and whether they belong to a flood component that extends north.

Uses r6_figures.load_run (the same fields the maps draw: active, excl, aoi_m, ems_wet, hmax, wet).
Usage (sfincs-viz env): python -I code19_b45_map_checks.py --repo <worktree>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ALBUFERA_LONLAT = (-0.335, 39.335)     # centre of the Albufera lagoon (WGS84), used only to pick the WorldCover-80 component
THR = 0.10


def _json_default(o):
    """numpy scalars -> JSON (float32 from the map grid otherwise fails to serialise)."""
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(f"not serialisable: {type(o).__name__}")


def southern_rows_summary(wet, msk, aoi, hmax, n_rows: int = 5) -> dict:
    """Counts over the n southernmost rows (row 0 = south, y ascending): wet cells, wet cells inside an AOI, wet cells on row 0
    that sit on a closed boundary (msk = 1), the boundary composition of row 0 and the largest depth."""
    rows = slice(0, n_rows)
    w = np.asarray(wet)[rows]
    msk = np.asarray(msk); aoi = np.asarray(aoi); hmax = np.asarray(hmax)
    return {"n_rows": int(n_rows), "wet_cells": int(w.sum()), "wet_in_aoi": int((w & aoi[rows]).sum()), "wet_per_row": [int(np.asarray(wet)[i].sum()) for i in range(n_rows)],
            "row0_msk0": int((msk[0] == 0).sum()), "row0_msk1": int((msk[0] == 1).sum()), "row0_msk2": int((msk[0] == 2).sum()),
            "row0_wet_closed": int((np.asarray(wet)[0] & (msk[0] == 1)).sum()), "hmax_max_m": float(np.nanmax(np.where(w, hmax[rows], np.nan))) if w.any() else 0.0}


def worldcover_at_cells(vrt_path: Path, x, y, epsg: int):
    """WorldCover class at every cell centre (nearest 10-m pixel), as eval_exclusion samples it."""
    import pyproj
    import rasterio
    from rasterio.windows import Window
    tr = pyproj.Transformer.from_crs(epsg, 4326, always_xy=True)
    lon, lat = tr.transform(x.ravel(), y.ravel())
    with rasterio.open(vrt_path) as src:
        rows, cols = rasterio.transform.rowcol(src.transform, lon, lat)
        rows, cols = np.asarray(rows), np.asarray(cols)
        r0, r1, c0, c1 = int(rows.min()), int(rows.max()), int(cols.min()), int(cols.max())
        arr = src.read(1, window=Window(c0, r0, c1 - c0 + 1, r1 - r0 + 1))
    return arr[rows - r0, cols - c0].reshape(x.shape)


def component_stats(comp, R, open_sea, cell_km2, fp_total):
    msk = R.s["msk"]; zb = R.s["zb"]
    act = comp & R.active
    universe = R.active & R.aoi_m & ~R.excl
    wet_in = comp & R.wet
    would_fp = wet_in & R.active & R.aoi_m & ~R.ems_wet
    ii, jj = np.nonzero(comp)
    return {"cells": int(comp.sum()), "km2": round(float(comp.sum() * cell_km2), 2),
            "bbox_cells_rows_cols": [int(ii.min()), int(ii.max()), int(jj.min()), int(jj.max())],
            "bbox_utm": [float(R.s["x"][comp].min()), float(R.s["y"][comp].min()), float(R.s["x"][comp].max()), float(R.s["y"][comp].max())],
            "msk_counts": {str(k): int((msk[comp] == k).sum()) for k in (0, 1, 2)}, "active_cells": int(act.sum()), "open_sea_cells": int((comp & open_sea).sum()),
            "excluded_cells": int((comp & R.excl).sum()), "in_aoi_cells": int((comp & R.aoi_m).sum()), "in_universe_cells": int((comp & universe).sum()),
            "ems_observed_cells": int((comp & R.ems_wet).sum()), "zb_m": {"min": float(zb[comp].min()), "median": float(np.median(zb[comp])), "max": float(zb[comp].max())},
            "hmax_active": None if not act.any() else {"max_m": float(R.hmax[act].max()), "mean_m": float(R.hmax[act].mean()), "median_m": float(np.median(R.hmax[act])),
                                                       "cells_gt_0p10": int((R.hmax[act] > THR).sum()), "cells_gt_0p50": int((R.hmax[act] > 0.5).sum())},
            "wet_cells_h_gt_0p10": int(wet_in.sum()), "would_be_false_alarm_cells": int(would_fp.sum()),
            "would_be_share_of_record_FP_pct": round(100.0 * would_fp.sum() / fp_total, 3) if fp_total else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    a = ap.parse_args()
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "reproduction" / "r6" / "scripts"))
    import r6_figures as F
    F.setup_env()
    import pyproj
    from scipy import ndimage
    from eval_exclusion import read_mask_for_grid
    out_dir = repo / "reproduction" / "v14_rerun" / "code19"; out_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- every map: modelled-wet cells inside excluded cells (depth drawn over the grey mask)
    maps = {}
    for fig, event in list(F.MAP_FIGS.items()) + [("F9", "crete")]:
        R = F.load_run(event)
        cell_km2 = R.s["cell_area_km2"]
        n = int((R.wet & R.excl).sum())
        maps[fig] = {"event": event, "run": R.run, "wet_cells_in_excluded": n, "km2": round(n * cell_km2, 2), "wet_cells_total": int(R.wet.sum()),
                     "share_of_wet_pct": round(100.0 * n / max(int(R.wet.sum()), 1), 2)}
        print(f"{fig} {event}: wet cells in excluded cells {n} ({maps[fig]['km2']} km², {maps[fig]['share_of_wet_pct']} % of the wet cells)", flush=True)

    # ---- B4 Valencia / Albufera
    R = F.load_run("valencia")
    cfg = R.cfg; cell_km2 = R.s["cell_area_km2"]
    excl_rec = json.loads((F.MASKS / "valencia_exclusion.json").read_text(encoding="utf-8"))
    vrt = Path(excl_rec["worldcover"])
    cls = worldcover_at_cells(vrt, R.s["x"], R.s["y"], cfg.epsg)
    open_sea_tif = cfg.paths["work_dir"] / "open_sea_mask.tif"
    open_sea = read_mask_for_grid(open_sea_tif, R.s) if open_sea_tif.exists() else read_mask_for_grid(Path(excl_rec["open_sea_source"]), R.s)
    wc80 = cls == 80
    tr = pyproj.Transformer.from_crs(4326, cfg.epsg, always_xy=True)
    cx, cy = tr.transform(*ALBUFERA_LONLAT)
    i0 = np.unravel_index(int(np.argmin((R.s["x"] - cx) ** 2 + (R.s["y"] - cy) ** 2)), R.s["x"].shape)
    centre = {"lonlat": ALBUFERA_LONLAT, "cell_row_col": [int(i0[0]), int(i0[1])], "worldcover_class": int(cls[i0]), "msk": int(R.s["msk"][i0]), "zb_m": float(R.s["zb"][i0]),
              "open_sea": bool(open_sea[i0]), "excluded": bool(R.excl[i0]), "in_aoi": bool(R.aoi_m[i0])}
    rec = F.jload(F.RES / f"{R.run}_v14_newmask.json")["validation"]["strict_threshold_sweep"][F.thr_key()]
    fp_total = int(rec["fp"])
    lab4, _ = ndimage.label(wc80)                                   # 4-connected class-80 component holding the centre
    comp_all = lab4 == lab4[i0] if lab4[i0] else np.zeros_like(wc80)
    lab4b, _ = ndimage.label(wc80 & ~open_sea)                      # the same without the open-sea cells (the lagoon proper if the golas connect it to the sea)
    comp_land = lab4b == lab4b[i0] if lab4b[i0] else np.zeros_like(wc80)
    ring = ndimage.binary_dilation(comp_land, structure=np.ones((3, 3)), iterations=3) & ~comp_land
    ring_cls = {int(k): int(v) for k, v in zip(*np.unique(cls[ring], return_counts=True))}
    ring_universe = ring & R.active & R.aoi_m & ~R.excl
    b4 = {"utc": now, "run": R.run, "worldcover_vrt": str(vrt), "wc80_cells_total": int(wc80.sum()), "wc80_cells_record": excl_rec["wc80_cells"], "open_sea_cells": int(open_sea.sum()),
          "open_sea_cells_record": excl_rec["open_sea_cells"], "centre": centre, "record_fp_cells": fp_total,
          "lagoon_wc80_component_incl_open_sea": component_stats(comp_all, R, open_sea, cell_km2, fp_total) if comp_all.any() else None,
          "lagoon_wc80_component_excl_open_sea": component_stats(comp_land, R, open_sea, cell_km2, fp_total) if comp_land.any() else None,
          "margin_ring_3_cells": {"cells": int(ring.sum()), "worldcover_classes": ring_cls, "in_universe_cells": int(ring_universe.sum()),
                                  "wet_in_universe_cells": int((ring_universe & R.wet).sum()), "false_alarm_cells": int((ring_universe & R.wet & ~R.ems_wet).sum()),
                                  "share_of_record_FP_pct": round(100.0 * (ring_universe & R.wet & ~R.ems_wet).sum() / fp_total, 3)}}
    lag = b4["lagoon_wc80_component_excl_open_sea"] or b4["lagoon_wc80_component_incl_open_sea"]
    b4["verdict"] = ("excluded from the evaluation universe (no lagoon cell inside it)" if lag and lag["in_universe_cells"] == 0 else
                     f"{lag['in_universe_cells']} lagoon cells inside the universe" if lag else "no WorldCover-80 component at the centre")
    (out_dir / "b4_albufera.json").write_text(json.dumps(b4, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    print("B4 centre:", centre)
    for k in ("lagoon_wc80_component_incl_open_sea", "lagoon_wc80_component_excl_open_sea"):
        v = b4[k]
        if v:
            print(f"B4 {k}: {v['cells']} cells {v['km2']} km²; msk {v['msk_counts']}; open sea {v['open_sea_cells']}; excluded {v['excluded_cells']}; in AOI {v['in_aoi_cells']}; "
                  f"in universe {v['in_universe_cells']}; wet {v['wet_cells_h_gt_0p10']}; hmax {v['hmax_active']}; would-be FP {v['would_be_false_alarm_cells']} = {v['would_be_share_of_record_FP_pct']} %")
    print("B4 margin ring:", b4["margin_ring_3_cells"]); print("B4 verdict:", b4["verdict"])

    # ---- B5 Emilia-Romagna southern edge
    R = F.load_run("emilia")
    msk = R.s["msk"]; cell = R.s["dx"]
    summ = southern_rows_summary(R.wet, msk, R.aoi_m, R.hmax, 5)
    src_pts = []
    srcf = R.cfg.paths["model_dir"] / "sfincs.src"
    if srcf.exists():
        src_pts = [tuple(float(v) for v in ln.split()[:2]) for ln in srcf.read_text(encoding="utf-8").splitlines() if ln.strip()]
    lab, _ = ndimage.label(R.wet, structure=np.ones((3, 3)))
    cells = []
    for i, j in zip(*np.nonzero(R.wet[:5])):
        comp = lab == lab[i, j]
        rows_of_comp = np.nonzero(comp.any(axis=1))[0]
        d = min(((R.s["x"][i, j] - sx) ** 2 + (R.s["y"][i, j] - sy) ** 2) ** 0.5 for sx, sy in src_pts) if src_pts else None
        cells.append({"row": int(i), "col": int(j), "x_m": float(R.s["x"][i, j]), "y_m": float(R.s["y"][i, j]), "msk": int(msk[i, j]), "zb_m": round(float(R.s["zb"][i, j]), 2),
                      "hmax_m": round(float(R.hmax[i, j]), 3), "in_aoi": bool(R.aoi_m[i, j]), "ems_observed": bool(R.ems_wet[i, j]), "excluded": bool(R.excl[i, j]),
                      "component_cells": int(comp.sum()), "component_rows": [int(rows_of_comp.min()), int(rows_of_comp.max())], "nearest_source_m": None if d is None else round(d, 1)})
    src_in_south = [p for p in src_pts if any(abs(p[0] - c["x_m"]) < cell and abs(p[1] - c["y_m"]) < cell for c in cells)]
    b5 = {"utc": now, "run": R.run, "grid_rows_cols": list(R.s["msk"].shape), "cell_m": cell, "y_ascending": bool(R.s["y"][1, 0] > R.s["y"][0, 0]), "summary": summ,
          "row0_southern_extent_y_m": float(R.s["y"][0, 0]), "sources": [{"x_m": p[0], "y_m": p[1]} for p in src_pts], "sources_within_one_cell_of_a_southern_wet_cell": len(src_in_south),
          "southern_wet_cells": cells, "plotting_artefact": False,
          "reading": "the wet cells in rows 0-4 are h_max > 0.10 m in sfincs_map.nc, drawn by imshow with origin='lower' at their cell extent; they are model output, not a drawing artefact"}
    (out_dir / "b5_emilia_south.json").write_text(json.dumps(b5, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    print("B5 summary:", summ, "| sources within a cell of a southern wet cell:", len(src_in_south))
    for c in cells[:40]:
        print("   ", c)
    (out_dir / "b_maps_wet_in_excluded.json").write_text(json.dumps({"utc": now, "maps": maps}, indent=2, default=_json_default), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
