"""CODE-12 Part C — EMSR933 Crete build QC (grid, subgrid, mask, boundary only; no forcing, no run).

Reads the hydromt build made from the Stage-1 rendered baseline yml with the forcing step removed
(D:/ELKAK/implementation/emsr933_crete/buildqc/), reports mask counts, water-level boundary points
(harness v1.4 geometry, written into the QC model as sfincs.bnd/bzs), subgrid statistics, and
characterises the GLO-30 pit in the Samaria gorge on the 100-m dep grid (do not fix).

Usage: python -I crete_build_qc.py --repo <worktree> --model D:/ELKAK/implementation/emsr933_crete/buildqc/model
       --stage1-json <reproduction/emsr933/stage1_depressions.json> --out-json <...> --out-md <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--stage1-json", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--out-md", required=True, type=Path)
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts"))
    import build_model
    import pyflwdir
    import rasterio
    import xarray as xr
    from hydromt_sfincs import SfincsModel
    from pyproj import Transformer
    from scipy import ndimage

    t0 = dt.datetime.now(dt.timezone.utc)
    rep = {"utc": t0.strftime("%Y-%m-%dT%H:%M:%SZ"), "model_dir": str(a.model)}
    mod = SfincsModel(root=str(a.model), mode="r")
    mod.read_config()
    mod.read_grid()
    inp = {k: mod.config[k] for k in ("mmax", "nmax", "dx", "dy", "x0", "y0", "epsg", "tref", "tstart", "tstop", "pavbnd")}
    rep["inp"] = inp
    msk = mod.mask.values
    rep["grid"] = {"mmax": int(inp["mmax"]), "nmax": int(inp["nmax"]), "n_cells_total": int(msk.size),
                   "dx_m": float(inp["dx"]), "cell_km2": float(inp["dx"]) * float(inp["dy"]) / 1e6}
    rep["mask"] = {"msk0_inactive": int((msk == 0).sum()), "msk1_active_interior": int((msk == 1).sum()),
                   "msk2_waterlevel_boundary": int((msk == 2).sum()), "msk3_outflow_boundary": int((msk == 3).sum()),
                   "active_total_msk_ge_1": int((msk >= 1).sum())}
    rep["mask"]["active_km2"] = round(rep["mask"]["active_total_msk_ge_1"] * rep["grid"]["cell_km2"], 1)
    # dep (gis/dep.tif written by hydromt at model resolution) — land/sea split of the active cells
    with rasterio.open(a.model / "gis" / "dep.tif") as src:
        dep = src.read(1).astype("float64"); tr = src.transform; nod = src.nodata
    dep = np.where(dep == nod, np.nan, dep) if nod is not None else dep
    act = msk >= 1
    rep["dep"] = {"active_cells_dep_le_0": int((act & (dep <= 0)).sum()), "active_cells_dep_gt_0": int((act & (dep > 0)).sum()),
                  "active_dep_min_m": float(np.nanmin(dep[act])), "active_dep_max_m": float(np.nanmax(dep[act])),
                  "msk2_dep_min_m": float(np.nanmin(dep[msk == 2])), "msk2_dep_max_m": float(np.nanmax(dep[msk == 2])),
                  "msk2_dep_eq_0_count": int(((msk == 2) & (dep == 0)).sum())}
    # water-level boundary points (v1.4 geometry) -> written into the QC model (sfincs.bnd / sfincs.bzs)
    gdf = build_model.waterlevel_bnd_points(mod.mask, build_model.BND_SPACING_M)
    n_bnd = build_model.write_waterlevel_bnd(a.model, gdf, tref=str(mod.config["tref"]), tstop=str(mod.config["tstop"]))
    rep["boundary"] = {"bnd_points": int(n_bnd), "spacing_m": build_model.BND_SPACING_M,
                       "msk2_boundary_length_km_approx": round(rep["mask"]["msk2_waterlevel_boundary"] * float(inp["dx"]) / 1000, 1),
                       "pavbnd_pa_in_inp": float(inp["pavbnd"]), "bzs_m": 0.0,
                       "bnd_x_range": [float(gdf.geometry.x.min()), float(gdf.geometry.x.max())] if n_bnd else None,
                       "bnd_y_range": [float(gdf.geometry.y.min()), float(gdf.geometry.y.max())] if n_bnd else None}
    # subgrid statistics (active cells)
    sg = xr.open_dataset(a.model / "sfincs_subgrid.nc")
    rep["subgrid"] = {"file_MB": round((a.model / "sfincs_subgrid.nc").stat().st_size / 1e6, 1),
                      "np": int(sg.sizes["np"]), "npuv": int(sg.sizes["npuv"]), "levels": int(sg.sizes["levels"])}
    for v in ("z_zmin", "z_zmax", "z_volmax"):
        arr = sg[v].values.astype("float64")
        arr = arr[np.isfinite(arr)]
        rep["subgrid"][v] = {"min": float(arr.min()), "p50": float(np.percentile(arr, 50)), "mean": float(arr.mean()),
                             "max": float(arr.max()), "n_finite": int(arr.size)}
    for v in ("uv_zmin", "uv_zmax", "uv_navg"):
        arr = sg[v].values.astype("float64"); arr = arr[np.isfinite(arr)]
        rep["subgrid"][v] = {"min": float(arr.min()), "p50": float(np.percentile(arr, 50)), "max": float(arr.max()), "n_finite": int(arr.size)}
    # Samaria-gorge pit (Stage-1: AOI07 component 2, deepest GLO-30 cell 23.9604E 35.2837N)
    s1 = json.loads(a.stage1_json.read_text(encoding="utf-8"))
    aoi7 = next(x for x in s1["aois"] if x["number"] == 7)
    pit1 = aoi7["largest_components"][1]
    lon, lat = pit1["deepest_cell_lonlat"]
    to_utm = Transformer.from_crs(4326, int(inp["epsg"]), always_xy=True)
    px, py = to_utm.transform(lon, lat)
    col, row = ~tr * (px, py); row, col = int(row), int(col)
    W = 150  # 15 km window around the pit
    r0, r1, c0, c1 = max(row - W, 0), min(row + W, dep.shape[0]), max(col - W, 0), min(col + W, dep.shape[1])
    win = dep[r0:r1, c0:c1].astype("float32")
    land = np.isfinite(win) & (act[r0:r1, c0:c1])
    win_f = np.where(land, win, -9999.0).astype("float32")
    filled, _ = pyflwdir.dem.fill_depressions(win_f, nodata=-9999.0, max_depth=-1.0, outlets="edge")
    depth = np.where(land, filled - win_f, 0.0)
    lab, nlab = ndimage.label(depth > 0.5, structure=np.ones((3, 3)))
    lr, lc = row - r0, col - c0
    lab_pit = lab[lr, lc]
    if lab_pit == 0:  # deepest GLO-30 cell may sit one cell off at 100 m: take the deepest labelled cell nearby
        sub = depth[max(lr - 3, 0):lr + 4, max(lc - 3, 0):lc + 4]
        j = np.unravel_index(np.argmax(sub), sub.shape)
        lab_pit = lab[max(lr - 3, 0) + j[0], max(lc - 3, 0) + j[1]]
    cm = lab == lab_pit
    d = depth[cm]; k = int(np.argmax(d)); rr, cc = np.where(cm)
    cell_km2 = rep["grid"]["cell_km2"]
    floor = float(win[rr[k], cc[k]]); spill = float(filled[rr[k], cc[k]])
    rep["samaria_pit_100m"] = {
        "stage1_90m_component": pit1,
        "window_cells": [int(r1 - r0), int(c1 - c0)], "n_cells": int(cm.sum()), "area_km2": round(float(cm.sum() * cell_km2), 2),
        "floor_m": round(floor, 1), "spill_level_m": round(spill, 1), "max_depth_m": round(float(d.max()), 1),
        "volume_below_spill_Mm3": round(float((d * cell_km2 * 1e6).sum()) / 1e6, 1),
        "deepest_cell_lonlat_100m": list(Transformer.from_crs(int(inp["epsg"]), 4326, always_xy=True).transform(
            *(tr * (c0 + cc[k] + 0.5, r0 + rr[k] + 0.5)))),
        "cells_in_mask_active": int(act[r0:r1, c0:c1][cm].sum()),
        "subgrid_z_zmin_at_deepest_m": None, "closed_in_dep_grid": bool(spill > floor + 0.5),
        "note": "closed depression in the model dep (filled surface > floor): rain-on-grid runoff reaching these cells ponds up to the spill level — SFINCS has no karst/sinkhole drainage; not modified (Part C: characterise only)."}
    # subgrid z_zmin/z_zmax at the deepest 100-m cell. SFINCS index order = column-major (Fortran) over the
    # south-up grid; verified here by the correlation between dep[ind] and z_zmin (must exceed 0.99).
    try:
        from hydromt_sfincs import utils as sfu
        ind = sfu.read_binary_map_index(a.model / "sfincs.ind")
        dep_su = dep[::-1, :]                                   # south-up (SFINCS n = 1 at y0)
        corr = float(np.corrcoef(dep_su.ravel(order="F")[ind], sg["z_zmin"].values)[0, 1])
        flat = int(np.ravel_multi_index((dep.shape[0] - 1 - (r0 + rr[k]), c0 + cc[k]), dep.shape, order="F"))
        pos = int(np.searchsorted(ind, flat))
        ok = pos < ind.size and ind[pos] == flat and corr > 0.99
        rep["samaria_pit_100m"]["subgrid_index_check_corr"] = round(corr, 5)
        rep["samaria_pit_100m"]["subgrid_z_zmin_at_deepest_m"] = round(float(sg["z_zmin"].values[pos]), 1) if ok else "n/a (index check failed)"
        rep["samaria_pit_100m"]["subgrid_z_zmax_at_deepest_m"] = round(float(sg["z_zmax"].values[pos]), 1) if ok else "n/a"
    except Exception as e:  # pragma: no cover
        rep["samaria_pit_100m"]["subgrid_z_zmin_at_deepest_m"] = f"n/a ({e})"
    # hydromt build wall-clock from the log
    log = (a.model / "hydromt.log").read_text(encoding="utf-8", errors="replace").splitlines()
    stamps = [ln[:19] for ln in log if ln[:4].isdigit() and " - build - " in ln]   # the CLI build only (reads log too)
    rep["hydromt_build"] = {"first_log_stamp_local": stamps[0] if stamps else None, "last_log_stamp_local": stamps[-1] if stamps else None}
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    m, b, g, s, p = rep["mask"], rep["boundary"], rep["grid"], rep["subgrid"], rep["samaria_pit_100m"]
    L = [f"# EMSR933 Crete — build QC (CODE-12 Part C, no forcing, no run), {rep['utc']}", "",
         f"Model: `{a.model}` — grid {g['mmax']} x {g['nmax']} = {g['n_cells_total']:,} cells @ {g['dx_m']:.0f} m (EPSG:{inp['epsg']}); "
         f"GAP-1 = A (100 m island-wide), GAP-2 z_max = 2500 m; tref/tstart/tstop {inp['tref']} / {inp['tstart']} / {inp['tstop']}.", "",
         "| quantity | value |", "|---|---|",
         f"| active cells (msk >= 1) | {m['active_total_msk_ge_1']:,} ({m['active_km2']:,} km²) |",
         f"| msk = 1 interior / msk = 2 water-level boundary / msk = 3 | {m['msk1_active_interior']:,} / {m['msk2_waterlevel_boundary']:,} / {m['msk3_outflow_boundary']:,} |",
         f"| active cells with dep <= 0 m (GLO-30 sea plane) / > 0 m | {rep['dep']['active_cells_dep_le_0']:,} / {rep['dep']['active_cells_dep_gt_0']:,} |",
         f"| dep range of active cells | {rep['dep']['active_dep_min_m']:.1f} .. {rep['dep']['active_dep_max_m']:.1f} m |",
         f"| msk = 2 cells: dep range / cells at exactly 0 m | {rep['dep']['msk2_dep_min_m']:.2f} .. {rep['dep']['msk2_dep_max_m']:.2f} m / {rep['dep']['msk2_dep_eq_0_count']:,} |",
         f"| water-level bnd points (v1.4, every {b['spacing_m']:.0f} m) | {b['bnd_points']} along ~{b['msk2_boundary_length_km_approx']} km of msk = 2 cells; bzs = 0 m; pavbnd = {b['pavbnd_pa_in_inp']:.0f} Pa |",
         f"| subgrid file | {s['file_MB']} MB, np {s['np']:,}, npuv {s['npuv']:,}, {s['levels']} levels |",
         f"| subgrid z_zmin min / p50 / max | {s['z_zmin']['min']:.1f} / {s['z_zmin']['p50']:.1f} / {s['z_zmin']['max']:.1f} m |",
         f"| subgrid z_zmax min / p50 / max | {s['z_zmax']['min']:.1f} / {s['z_zmax']['p50']:.1f} / {s['z_zmax']['max']:.1f} m |",
         f"| subgrid z_volmax p50 / max | {s['z_volmax']['p50']:.0f} / {s['z_volmax']['max']:.0f} m³ |",
         f"| subgrid uv_navg (Manning) min / p50 / max | {s['uv_navg']['min']:.3f} / {s['uv_navg']['p50']:.3f} / {s['uv_navg']['max']:.3f} |",
         f"| hydromt build log span (local time) | {rep['hydromt_build']['first_log_stamp_local']} -> {rep['hydromt_build']['last_log_stamp_local']} |",
         "", "## Samaria-gorge GLO-30 pit at model resolution (characterised, NOT fixed)", "",
         "| grid | area km² | cells | floor m | spill m | max depth m | volume below spill Mm³ | closed in dep? |", "|---|---|---|---|---|---|---|---|",
         f"| GLO-30 @ 90 m (Stage 1) | {p['stage1_90m_component']['area_km2']} | {p['stage1_90m_component']['n_cells_90m']} | {p['stage1_90m_component']['floor_m']} | {p['stage1_90m_component']['spill_level_m']} | {p['stage1_90m_component']['max_depth_m']} | {p['stage1_90m_component']['volume_below_spill_Mm3']} | yes |",
         f"| model dep @ 100 m | {p['area_km2']} | {p['n_cells']} | {p['floor_m']} | {p['spill_level_m']} | {p['max_depth_m']} | {p['volume_below_spill_Mm3']} | {p['closed_in_dep_grid']} |",
         "", f"Deepest 100-m cell {p['deepest_cell_lonlat_100m'][0]:.4f} E / {p['deepest_cell_lonlat_100m'][1]:.4f} N; subgrid z_zmin there: {p['subgrid_z_zmin_at_deepest_m']} m; "
         f"{p['cells_in_mask_active']} of {p['n_cells']} pit cells are active. {p['note']}"]
    a.out_md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L)); print(f"-> {a.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
