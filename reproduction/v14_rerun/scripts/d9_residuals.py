"""CODE-16 A1 (2026-10-21) — the D9 residual items of the harness v1.4.2 source-point ledger, measured (post-processing only,
no SFINCS run). The author's decision (21 Oct 2026): D9 is documented, not fixed; the number freeze stands.

The CODE-15 ledger (code15/source_points_v142.json) left seven configuration items as found. Each is measured on the v1.4.2
build it belongs to:
  * injection items (Trikala, Titarisios, Ronco, Montone, Júcar): offset_km = distance from the build's snapped injection cell
    (model/sfincs_src_snap.json) to the nearest model cell on the named river's channel. Channel cells = model cells inside the
    0.05° footprints of the named river's GloFAS v4 network cells (glofas_network.river_cells from the d8_scope reference cells)
    whose centre lies within SEARCH_KM of the snapped cell, with a DEM-D8 upstream area (source_snap.dem_uparea_on_grid — the
    grid the build-time snap used) >= CHANNEL_FRACTION x the largest D8 upstream area inside the same footprint; a footprint
    whose D8 maximum exceeds LARGER_RIVER_RATIO x its GloFAS upstream area is crossed by a larger river and is skipped.
  * Kalambaka (inject: false): the same distance from its YAML injection coordinate; the point is sampled only.
  * the lattice item: the +0.05° longitude offset of the frozen Pineios Open-Meteo lattice (d8_scope lattice_shift_test) in km
    at the lattice's mean latitude (pyproj Geod, WGS84).
Usage: python -I d9_residuals.py --repo <worktree> [--static-dir D:/ELKAK/implementation/v14/_static/glofas_v4] [--out-dir ...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

SEARCH_KM = 15.0
CHANNEL_FRACTION = 0.5
HALF_CELL_DEG = 0.025
LARGER_RIVER_RATIO = 2.0   # a footprint whose D8 maximum exceeds this x the GloFAS cell's upstream area is crossed by a larger river: skipped
ITEMS = [  # (id, event, run, point, named river, kind)
    ("D9-1", "pineios", "pineios_enhanced_v142", "pineios_trikala", "Pineios", "injection"),
    ("D9-2", "pineios", "pineios_enhanced_v142", "titarisios", "Titarisios", "injection"),
    ("D9-3", "emilia", "emilia_enhanced_8aoi_v142", "ronco", "Ronco", "injection"),
    ("D9-4", "emilia", "emilia_enhanced_8aoi_v142", "montone", "Montone", "injection"),
    ("D9-5", "valencia", "valencia_enhanced_164_v142", "jucar", "Jucar", "sampling at the mouth reach (Magro nested)"),
    ("D9-6", "pineios", "pineios_enhanced_v142", "pineios_kalambaka", "Pineios", "sampled only (inject: false)"),
    ("D9-7", "pineios", None, None, None, "lattice offset of the frozen Open-Meteo file"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--static-dir", type=Path, default=Path("D:/ELKAK/implementation/v14/_static/glofas_v4"))
    ap.add_argument("--out-dir", type=Path, default=None)
    a = ap.parse_args()
    repo = a.repo.resolve()
    R = repo / "reproduction" / "v14_rerun"
    out_dir = a.out_dir or (R / "code16")
    sys.path.insert(0, str(repo / "skill" / "scripts")); sys.path.insert(0, str(Path(__file__).resolve().parent))
    os.environ.setdefault("GDAL_DATA", os.path.join(sys.prefix, "Library", "share", "gdal"))
    import pyproj
    import rasterio
    from _common import load_config
    from d8_scope import RIVER_REFS
    from glofas_network import GlofasNetwork, river_cells
    import source_snap as ss

    ledger = json.loads((R / "code15" / "source_points_v142.json").read_text(encoding="utf-8"))
    scope = json.loads((R / "code15" / "d8_scope.json").read_text(encoding="utf-8"))
    net = GlofasNetwork(a.static_dir)
    geod = pyproj.Geod(ellps="WGS84")
    grids = {}

    def grid(run):
        if run in grids:
            return grids[run]
        cfg = load_config(["--config", str(R / "configs" / f"{run}.yaml")])
        model = cfg.paths["model_dir"]
        with rasterio.open(model / "gis" / "dep.tif") as s:
            dep = s.read(1).astype(float); T = s.transform
        with rasterio.open(model / "gis" / "msk.tif") as s:
            msk = s.read(1).astype(float)
        dem_dir = cfg.paths["data_dir"] / "copdem30"
        up = ss.dem_uparea_on_grid(dem_dir if any(dem_dir.glob("*.tif")) else None, cfg.epsg, T, dep.shape, fallback_dep=dep)
        X, Y = ss.cell_centres(T, dep.shape)
        to_ll = pyproj.Transformer.from_crs(f"EPSG:{cfg.epsg}", "EPSG:4326", always_xy=True)
        LON, LAT = to_ll.transform(X, Y)
        snap = json.loads((model / "sfincs_src_snap.json").read_text(encoding="utf-8"))
        grids[run] = {"cfg": cfg, "model": model, "dep": dep, "msk": msk, "up": up, "X": X, "Y": Y, "LON": np.asarray(LON), "LAT": np.asarray(LAT),
                      "T": T, "epsg": cfg.epsg, "snap": {p["name"]: p for p in snap["points"]}, "to_utm": pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{cfg.epsg}", always_xy=True)}
        return grids[run]

    def channel_cells(g, river, x0, y0):
        refs = RIVER_REFS[river]
        refs = refs if isinstance(refs, list) else [refs]
        cells = []
        for rlon, rlat in refs:
            cells += river_cells(net, net.cell(rlon, rlat))
        cells = list(dict.fromkeys(cells))
        lon0, lat0 = pyproj.Transformer.from_crs(f"EPSG:{g['epsg']}", "EPSG:4326", always_xy=True).transform(x0, y0)
        chan = np.zeros(g["dep"].shape, dtype=bool); owner = {}
        used = []
        for ij in cells:
            clon, clat = net.centre(ij)
            _, _, d = geod.inv(lon0, lat0, clon, clat)
            if d / 1000.0 > SEARCH_KM:
                continue
            fp = (np.abs(g["LON"] - clon) <= HALF_CELL_DEG) & (np.abs(g["LAT"] - clat) <= HALF_CELL_DEG)
            if not fp.any():
                continue
            upmax = float(np.nanmax(np.where(fp, g["up"], np.nan)))
            if upmax > LARGER_RIVER_RATIO * net.uparea(ij):
                used.append({"glofas_cell": [clon, clat], "glofas_uparea_km2": round(net.uparea(ij), 1), "footprint_cells": int(fp.sum()), "max_d8_uparea_km2": round(upmax, 2),
                             "skipped": f"D8 maximum > {LARGER_RIVER_RATIO} x the GloFAS upstream area: a larger river crosses the footprint"})
                continue
            c = fp & (g["up"] >= CHANNEL_FRACTION * upmax)
            chan |= c
            used.append({"glofas_cell": [clon, clat], "glofas_uparea_km2": round(net.uparea(ij), 1), "footprint_cells": int(fp.sum()), "max_d8_uparea_km2": round(upmax, 2), "channel_cells": int(c.sum())})
            for r, cc in zip(*np.nonzero(c)):
                owner[(int(r), int(cc))] = (clon, clat)
        if not chan.any():
            return None, used
        rr, cc = np.nonzero(chan)
        d = np.hypot(g["X"][rr, cc] - x0, g["Y"][rr, cc] - y0)
        k = int(np.argmin(d)); r, c = int(rr[k]), int(cc[k])
        return {"offset_km": round(float(d[k]) / 1000.0, 2), "row_col": [r, c], "lonlat": [round(float(g["LON"][r, c]), 5), round(float(g["LAT"][r, c]), 5)],
                "zb_m": round(float(g["dep"][r, c]), 2), "msk": int(g["msk"][r, c]), "d8_uparea_km2": round(float(g["up"][r, c]), 2),
                "footprint_of_glofas_cell": list(owner[(r, c)]), "n_channel_cells": int(chan.sum())}, used

    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/d9_residuals.py",
           "ledger": "code15/source_points_v142.json", "ledger_utc": ledger["utc"], "scope": "code15/d8_scope.json",
           "method": {"search_km": SEARCH_KM, "channel_fraction_of_footprint_max_d8": CHANNEL_FRACTION, "footprint_half_width_deg": HALF_CELL_DEG, "larger_river_ratio": LARGER_RIVER_RATIO,
                      "d8": "source_snap.dem_uparea_on_grid (Copernicus DEM tiles of the run on the model grid, 10 km pad) — the build-time snap's grid",
                      "river_cells": "glofas_network.river_cells of the d8_scope RIVER_REFS reference cell(s)"},
           "items": []}
    for iid, event, run, point, river, kind in ITEMS:
        it = {"id": iid, "event": event, "run": run, "point": point, "named_river": river, "kind": kind}
        if kind.startswith("lattice"):
            ev = next(e for e in scope["events"] if e["event"] == event)
            off = float(ev["lattice_lon_offset_deg"])
            ext = ev.get("glofas_extent") or {}
            lats = ext.get("lat") or ext.get("latitude") or [ext.get("south"), ext.get("north")]
            lat_mid = float(np.mean([float(v) for v in lats if v is not None])) if any(v is not None for v in lats) else 39.6
            lon_mid = float(np.mean([float(v) for v in (ext.get("lon") or ext.get("longitude") or [22.0, 22.0]) if v is not None]))
            _, _, d = geod.inv(lon_mid, lat_mid, lon_mid + off, lat_mid)
            it.update({"lattice_lon_offset_deg": off, "at_lat": round(lat_mid, 3), "offset_km": round(d / 1000.0, 2),
                       "lattice_shift_test": ev.get("lattice_shift_test"), "glofas_file": ev.get("glofas_file"), "glofas_extent": ext})
            out["items"].append(it); print(iid, kind, it["offset_km"], "km"); continue
        g = grid(run)
        lp = next(p for p in ledger["events"][event]["src_points"] if p["name"] == point)
        it["ledger_point"] = lp
        sp = g["snap"].get(point)
        if sp and sp.get("injected"):
            x0, y0 = sp["xy"]
            it["snapped_injection_cell"] = {"row_col": sp["row_col"], "xy": sp["xy"], "zb_m": sp["zb_m"], "d8_uparea_km2": sp["uparea_km2"],
                                            "snap_distance_m": sp["distance_m"], "source": f"{g['model']}/sfincs_src_snap.json"}
        else:
            x0, y0 = g["to_utm"].transform(lp.get("src_lon", lp["lon"]), lp.get("src_lat", lp["lat"]))
            r = int((g["T"].f - y0) // abs(g["T"].e)); c = int((x0 - g["T"].c) // g["T"].a)
            inside = 0 <= r < g["dep"].shape[0] and 0 <= c < g["dep"].shape[1]
            fin = lambda v, f: (f(v) if (inside and np.isfinite(v)) else None)  # noqa: E731 — NaN outside the active grid -> None
            it["unsnapped_injection_point"] = {"lonlat": [lp.get("src_lon", lp["lon"]), lp.get("src_lat", lp["lat"])], "xy": [round(x0, 2), round(y0, 2)],
                                               "zb_m": fin(g["dep"][r, c] if inside else np.nan, lambda v: round(float(v), 2)),
                                               "msk": fin(g["msk"][r, c] if inside else np.nan, int),
                                               "d8_uparea_km2": fin(g["up"][r, c] if inside else np.nan, lambda v: round(float(v), 2)),
                                               "note": "inject: false — not written to sfincs.src; zb/msk None = outside the model's active grid (gis rasters are NaN there)"}
        ch, used = channel_cells(g, river, x0, y0)
        xy_yaml = g["to_utm"].transform(lp.get("src_lon", lp["lon"]), lp.get("src_lat", lp["lat"]))
        ch_y, _ = channel_cells(g, river, *xy_yaml)
        it["offset_from_yaml_point_km"] = ch_y["offset_km"] if ch_y else None
        it["nearest_named_river_channel_cell"] = ch
        it["offset_km"] = ch["offset_km"] if ch else None
        it["footprints_used"] = used
        it["sampled_cell"] = next(({"file_coord": q["glofas_rule_cell"]["file_coord"], "network_cell": q["glofas_rule_cell"]["network_cell"], "uparea_km2": q["glofas_rule_cell"]["uparea_km2"],
                                    "peak_file_m3s": q["glofas_rule_cell"]["peak_file_m3s"]} for e in scope["events"] if e["event"] == event for q in e["points"] if q["name"] == point), None)
        out["items"].append(it)
        print(iid, point, river, "offset", it["offset_km"], "km;", "snapped" if "snapped_injection_cell" in it else "unsnapped", (it.get("snapped_injection_cell") or it.get("unsnapped_injection_point")))
    nest = {ev: v.get("nested_injected_cells") for ev, v in ledger["events"].items()}
    out["nested_injected_cells_from_ledger"] = nest
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "d9_residuals.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    md = [f"# D9 residual items, measured — generated {out['utc']} by `reproduction/v14_rerun/scripts/d9_residuals.py`", "",
          f"Ledger `{out['ledger']}` (resolved {out['ledger_utc']}). Offset = distance from the snapped injection cell (or, for a point that is not injected, from its YAML injection coordinate) "
          f"to the nearest model cell on the named river's channel: cells inside the 0.05° footprints of the river's GloFAS v4 cells within {SEARCH_KM:.0f} km whose D8 upstream area is ≥ {CHANNEL_FRACTION} × the footprint maximum (footprints whose D8 maximum exceeds {LARGER_RIVER_RATIO} × the GloFAS upstream area — a larger river crossing — are skipped).", "",
          "| id | point | kind | offset km | injection cell: z_b m, D8 km² | nearest channel cell: z_b m, D8 km², GloFAS footprint |", "|---|---|---|---|---|---|"]
    for it in out["items"]:
        if it["kind"].startswith("lattice"):
            md.append(f"| {it['id']} | Pineios lattice | {it['kind']} | {it['offset_km']} | — | +{it['lattice_lon_offset_deg']}° longitude at {it['at_lat']}° N |"); continue
        ic = it.get("snapped_injection_cell") or it.get("unsnapped_injection_point") or {}
        ch = it.get("nearest_named_river_channel_cell") or {}
        md.append(f"| {it['id']} | {it['point']} ({it['named_river']}) | {it['kind']} | {it['offset_km']} | {ic.get('zb_m')}, {ic.get('d8_uparea_km2')} | {ch.get('zb_m')}, {ch.get('d8_uparea_km2')}, {ch.get('footprint_of_glofas_cell')} |")
    (out_dir / "d9_residuals.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("wrote", out_dir / "d9_residuals.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
